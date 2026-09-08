"""Gatekeeper hardcoding scan: AST rules + regex rules.

Policy: runtime text may not live inside *.py.  Every string
literal is a violation unless it is a key-like token (ASCII,
no whitespace, within the length cap) - the single sanctioned
channel used to address texts inside data/*.json via the text,
log, error and keyboard managers.  Word sets (strings inside a
set/frozenset literal), non-ASCII text, multi-word text, URLs
and overlong tokens always violate.  Docstrings stay exempt
while skip_docstrings is true.  Regex rules additionally ban
print(), raw SQL, secrets, windows paths and inline regex.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Callable

from app.config.paths import ROOT
from app.managers.error_manager import ErrorManager
from app.managers.gk_structure import load_json


IssueFactory = Callable[..., Any]

_CACHE_DIR = "__pycache__"


def _docstring_nodes(tree: ast.AST) -> set[ast.AST]:
    """Collect AST string constant nodes used as docstrings."""
    found: set[ast.AST] = set()

    def take(body: list[ast.stmt]) -> None:
        if not body:
            return
        first = body[0]
        if not isinstance(first, ast.Expr):
            return
        val = first.value
        if isinstance(val, ast.Constant) and isinstance(
            val.value, str
        ):
            found.add(val)

    def_types = (
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.ClassDef,
    )
    if isinstance(tree, ast.Module):
        take(tree.body)
    for node in ast.walk(tree):
        if isinstance(node, def_types):
            take(node.body)
    return found


def _parents(tree: ast.AST) -> dict[int, ast.AST]:
    """Map each child node id to its parent node."""
    out: dict[int, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            out[id(child)] = node
    return out


def _scan_roots(cfg: dict[str, Any]) -> list[Path]:
    """Resolve scan roots and single files from config."""
    roots: list[Path] = []
    for name in cfg.get("scan_roots", []):
        base = ROOT / str(name)
        if base.is_dir():
            roots.append(base)
    for rel in cfg.get("scan_files", []):
        single = ROOT / str(rel)
        if single.is_file():
            roots.append(single)
    return roots


def _skip_set(cfg: dict[str, Any]) -> set[str]:
    """Relative paths excluded from every scan."""
    return {
        str(item) for item in cfg.get("skip_files", [])
    }


def _iter_py_files(
    roots: list[Path],
    skip: set[str],
) -> list[Path]:
    """List Python files under the scan roots."""
    files: list[Path] = []
    for base in roots:
        if base.is_file():
            rel = base.relative_to(ROOT).as_posix()
            if rel not in skip:
                files.append(base)
            continue
        for path in sorted(base.rglob("*.py")):
            parts = path.relative_to(ROOT).parts
            if any(
                part.startswith(".")
                or part == _CACHE_DIR
                for part in parts
            ):
                continue
            rel = path.relative_to(ROOT).as_posix()
            if rel not in skip:
                files.append(path)
    return files


def collect_all_py_files(
    patterns_path: Path,
) -> list[Path]:
    """All project Python files subject to the gatekeeper."""
    cfg = load_json(patterns_path)
    return _iter_py_files(
        _scan_roots(cfg),
        _skip_set(cfg),
    )


def _classify(value: str, max_len: int) -> str | None:
    """Return the AST rule a string literal violates.

    Key-like tokens (ASCII, no whitespace, within the length
    cap) are allowed: they are lookup keys into data JSON.
    """
    if "://" in value:
        return "inline_url"
    if any(ord(ch) > 127 for ch in value):
        return "non_ascii"
    if re.search(r"\s", value):
        return "text_literal"
    if len(value) > max_len:
        return "long_literal"
    return None


def _compiled_rules(
    cfg: dict[str, Any],
) -> list[tuple[str, re.Pattern[str]]]:
    """Compile the regex rules from the patterns config."""
    out: list[tuple[str, re.Pattern[str]]] = []
    for rule in cfg.get("rules", []):
        flags = 0
        if "i" in str(rule.get("flags", "")):
            flags |= re.IGNORECASE
        out.append((
            str(rule["id"]),
            re.compile(str(rule["pattern"]), flags),
        ))
    return out


def _scan_file(
    path: Path,
    cfg: dict[str, Any],
    compiled: list[tuple[str, re.Pattern[str]]],
) -> list[tuple[str, int]]:
    """Scan one file; return (rule_id, line) hits."""
    hits: list[tuple[str, int]] = []
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return hits
    ast_rules = {
        str(item) for item in cfg.get("ast_rules", [])
    }
    max_len = int(cfg.get("max_key_token_length", 48))
    docs = (
        _docstring_nodes(tree)
        if bool(cfg.get("skip_docstrings", True))
        else set()
    )
    parents = _parents(tree)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue
        if not isinstance(node.value, str):
            continue
        if node in docs:
            continue
        if (
            "word_set" in ast_rules
            and isinstance(
                parents.get(id(node)), ast.Set
            )
        ):
            hits.append(("word_set", node.lineno))
            continue
        rule = _classify(node.value, max_len)
        if rule is not None and rule in ast_rules:
            hits.append((rule, node.lineno))
    for idx, line in enumerate(source.splitlines(), 1):
        for rule_id, pattern in compiled:
            if pattern.search(line):
                hits.append((rule_id, idx))
    return hits


def check_hardcoding(
    patterns_path: Path,
    errors: ErrorManager,
    issue_cls: IssueFactory,
) -> list[Any]:
    """Scan every file; one Issue per file per rule type."""
    cfg = load_json(patterns_path)
    skip = _skip_set(cfg)
    compiled = _compiled_rules(cfg)
    ast_rules = {
        str(item) for item in cfg.get("ast_rules", [])
    }
    issues: list[Any] = []
    for path in _iter_py_files(_scan_roots(cfg), skip):
        rel = path.relative_to(ROOT).as_posix()
        buckets: dict[str, list[int]] = {}
        for rule, line in _scan_file(path, cfg, compiled):
            buckets.setdefault(rule, []).append(line)
        for rule, lines in sorted(buckets.items()):
            key = "gatekeeper.hardcoding.literal"
            if rule not in ast_rules:
                key = "gatekeeper.hardcoding.pattern"
            msg = errors.get(
                key,
                file=rel,
                line=lines[0],
                rule=rule,
                count=len(lines),
            )
            issues.append(issue_cls(
                rule="hardcoding",
                message=msg,
                file=rel,
                line=lines[0],
            ))
    return issues
