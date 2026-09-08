"""Gatekeeper check helpers (structure and length)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from app.config.paths import ROOT
from app.managers.error_manager import ErrorManager


IssueFactory = Callable[..., Any]


def load_json(path: Path) -> Any:
    """Load a JSON document from disk."""
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def check_structure(
    structure_path: Path,
    errors: ErrorManager,
    issue_cls: IssueFactory,
) -> list[Any]:
    """Verify required paths exist; reject unknown roots."""
    data = load_json(structure_path)
    issues: list[Any] = []
    for rel in data.get("directories", []):
        target = ROOT / str(rel)
        if not target.is_dir():
            msg = errors.get(
                "gatekeeper.structure.missing_dir",
                path=str(rel),
            )
            issues.append(
                issue_cls(rule="structure", message=msg)
            )
    for rel in data.get("files", []):
        target = ROOT / str(rel)
        if not target.is_file():
            msg = errors.get(
                "gatekeeper.structure.missing_file",
                path=str(rel),
            )
            issues.append(
                issue_cls(rule="structure", message=msg)
            )
    allowed = {
        str(item)
        for item in data.get("allowed_top_level", [])
    }
    if allowed:
        for child in ROOT.iterdir():
            name = child.name
            if name.startswith("."):
                continue
            if name in allowed:
                continue
            msg = errors.get(
                "gatekeeper.structure.extra_root",
                path=name,
            )
            issues.append(
                issue_cls(rule="structure", message=msg)
            )
    return issues


def check_file_length(
    files: list[Path],
    max_lines: int,
    errors: ErrorManager,
    issue_cls: IssueFactory,
) -> list[Any]:
    """Ensure each Python file is within line limit."""
    issues: list[Any] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        count = len(lines)
        if count > max_lines:
            rel = path.relative_to(ROOT).as_posix()
            msg = errors.get(
                "gatekeeper.file_too_long",
                file=rel,
                lines=count,
                max=max_lines,
            )
            issues.append(
                issue_cls(
                    rule="file_length",
                    message=msg,
                    file=rel,
                )
            )
    return issues


def check_line_length(
    files: list[Path],
    max_len: int,
    errors: ErrorManager,
    issue_cls: IssueFactory,
) -> list[Any]:
    """Ensure no Python line exceeds max length."""
    issues: list[Any] = []
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        lines = path.read_text(encoding="utf-8").splitlines()
        for idx, line in enumerate(lines, start=1):
            length = len(line)
            if length > max_len:
                msg = errors.get(
                    "gatekeeper.line_too_long",
                    file=rel,
                    line=idx,
                    length=length,
                    max=max_len,
                )
                issues.append(
                    issue_cls(
                        rule="line_length",
                        message=msg,
                        file=rel,
                        line=idx,
                    )
                )
    return issues


def _walk_files(
    rel: str,
    ignore: set[str],
) -> list[Path]:
    """List files under ROOT/rel, skipping hidden/ignored."""
    base = ROOT / rel
    if not base.is_dir():
        return []
    out: list[Path] = []
    for path in base.rglob("*"):
        parts = path.relative_to(ROOT).parts
        if any(
            part.startswith(".") or part in ignore
            for part in parts
        ):
            continue
        if path.is_file():
            out.append(path)
    return out


def check_app_py_only(
    dirs: list[str],
    ignore: set[str],
    errors: ErrorManager,
    issue_cls: IssueFactory,
) -> list[Any]:
    """Enforce: every file under app/ is a .py file."""
    issues: list[Any] = []
    for rel in dirs:
        for path in _walk_files(rel, ignore):
            if path.suffix == ".py":
                continue
            r = path.relative_to(ROOT).as_posix()
            msg = errors.get(
                "gatekeeper.structure.non_py_in_app",
                file=r,
            )
            issues.append(
                issue_cls(rule="structure", message=msg)
            )
    return issues


def check_data_no_python(
    dirs: list[str],
    ignore: set[str],
    errors: ErrorManager,
    issue_cls: IssueFactory,
) -> list[Any]:
    """Enforce: no .py file anywhere under data/."""
    issues: list[Any] = []
    for rel in dirs:
        for path in _walk_files(rel, ignore):
            if path.suffix != ".py":
                continue
            r = path.relative_to(ROOT).as_posix()
            msg = errors.get(
                "gatekeeper.structure.py_in_data",
                file=r,
            )
            issues.append(
                issue_cls(rule="structure", message=msg)
            )
    return issues


_BARE_EXCEPT = re.compile(r"^\s*except\s*:")


def check_pep8(
    files: list[Path],
    rules: set[str],
    errors: ErrorManager,
    issue_cls: IssueFactory,
) -> list[Any]:
    """PEP8 subset: tabs, trailing ws, final nl, except."""
    issues: list[Any] = []
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        hits: dict[str, tuple[int, int]] = {}

        def bump(rule: str, line: int) -> None:
            first, count = hits.get(rule, (line, 0))
            hits[rule] = (min(first, line), count + 1)

        for idx, line in enumerate(lines, start=1):
            pad = line[: len(line) - len(line.lstrip())]
            if "tabs_indent" in rules and "\t" in pad:
                bump("tabs_indent", idx)
            if (
                "trailing_whitespace" in rules
                and line != line.rstrip()
            ):
                bump("trailing_whitespace", idx)
            if (
                "bare_except" in rules
                and _BARE_EXCEPT.match(line)
            ):
                bump("bare_except", idx)
        if (
            "final_newline" in rules
            and text
            and not text.endswith("\n")
        ):
            bump("final_newline", len(lines))
        for rule, (first, count) in sorted(hits.items()):
            msg = errors.get(
                "gatekeeper.pep8." + rule,
                file=rel,
                line=first,
                count=count,
            )
            issues.append(issue_cls(
                rule="pep8",
                message=msg,
                file=rel,
                line=first,
            ))
    return issues
