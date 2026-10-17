"""Gatekeeper check helpers (structure and length)."""

from __future__ import annotations

import json
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
