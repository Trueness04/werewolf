"""Gatekeeper hardcoding scan helpers."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Callable

from app.config.paths import ROOT
from app.managers.error_manager import ErrorManager
from app.managers.gk_structure import load_json


IssueFactory = Callable[..., Any]


def _docstring_nodes(tree: ast.AST) -> set[ast.AST]:
    """Collect AST nodes that are docstrings."""
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


def _iter_py_files(
    root: Path,
    skip: set[str],
) -> list[Path]:
    """List Python sources under app, AI + launcher."""
    files: list[Path] = []
    roots = (root / "app", root / "AI")
    for base in roots:
        if not base.is_dir():
            continue
        for path in base.rglob("*.py"):
            rel = path.relative_to(root).as_posix()
            if rel in skip:
                continue
            files.append(path)
    launcher = root / "launcher.py"
    if launcher.is_file():
        rel = launcher.relative_to(root).as_posix()
        if rel not in skip:
            files.append(launcher)
    return files


def collect_scan_targets(
    patterns_path: Path,
) -> list[Path]:
    """Return Python files subject to hardcoding scan."""
    data = load_json(patterns_path)
    skip = {str(item) for item in data.get("skip_files", [])}
    return _iter_py_files(ROOT, skip)


def collect_all_py_files() -> list[Path]:
    """Return project Python files (app, AI, launcher)."""
    return _iter_py_files(ROOT, set())


def check_hardcoding(
    patterns_path: Path,
    errors: ErrorManager,
    issue_cls: IssueFactory,
) -> list[Any]:
    """Scan Python sources for hardcoding patterns."""
    data = load_json(patterns_path)
    max_lit = int(data.get("max_literal_length", 40))
    skip_docs = bool(data.get("skip_docstrings", True))
    skip = {str(item) for item in data.get("skip_files", [])}
    compiled: list[tuple[str, re.Pattern[str]]] = []
    for rule in data.get("rules", []):
        flags = 0
        if "i" in str(rule.get("flags", "")):
            flags |= re.IGNORECASE
        compiled.append(
            (
                str(rule["id"]),
                re.compile(str(rule["pattern"]), flags),
            )
        )
    issues: list[Any] = []
    for path in _iter_py_files(ROOT, skip):
        rel = path.relative_to(ROOT).as_posix()
        source = path.read_text(encoding="utf-8")
        issues.extend(
            _scan_file(
                path=path,
                rel=rel,
                source=source,
                max_lit=max_lit,
                skip_docs=skip_docs,
                compiled=compiled,
                errors=errors,
                issue_cls=issue_cls,
            )
        )
    return issues


def _scan_file(
    path: Path,
    rel: str,
    source: str,
    max_lit: int,
    skip_docs: bool,
    compiled: list[tuple[str, re.Pattern[str]]],
    errors: ErrorManager,
    issue_cls: IssueFactory,
) -> list[Any]:
    """Scan one file for literal and pattern issues."""
    issues: list[Any] = []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return issues
    docs = _docstring_nodes(tree) if skip_docs else set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue
        if not isinstance(node.value, str):
            continue
        if node in docs:
            continue
        if len(node.value) <= max_lit:
            continue
        line = getattr(node, "lineno", 1)
        msg = errors.get(
            "gatekeeper.hardcoding.literal",
            file=rel,
            line=line,
            rule="long_literal",
        )
        issues.append(
            issue_cls(
                rule="hardcoding",
                message=msg,
                file=rel,
                line=line,
            )
        )
    for idx, line in enumerate(source.splitlines(), start=1):
        for rule_id, pattern in compiled:
            if pattern.search(line):
                msg = errors.get(
                    "gatekeeper.hardcoding.pattern",
                    file=rel,
                    line=idx,
                    rule=rule_id,
                )
                issues.append(
                    issue_cls(
                        rule="hardcoding",
                        message=msg,
                        file=rel,
                        line=idx,
                    )
                )
    return issues
