"""Project rule enforcement before application start."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from app.config.paths import (
    GK_LIMITS,
    GK_PATTERNS,
    GK_STRUCTURE,
)
from app.managers.console_manager import ConsoleManager
from app.managers.error_manager import ErrorManager
from app.managers.gk_hardcoding import (
    check_hardcoding,
    collect_all_py_files,
)
from app.managers.gk_integrity import verify as verify_integrity
from app.managers.gk_structure import (
    check_app_py_only,
    check_data_no_python,
    check_file_length,
    check_line_length,
    check_pep8,
    check_structure,
    load_json,
)
from app.managers.logger_manager import get_logger


@dataclass(frozen=True)
class Issue:
    """A single gatekeeper violation."""

    rule: str
    message: str
    file: str | None = None
    line: int | None = None


class Gatekeeper:
    """Runs project rule checks and aborts on failure."""

    def __init__(
        self,
        errors: ErrorManager | None = None,
        console: ConsoleManager | None = None,
    ) -> None:
        self._errors = errors or ErrorManager()
        self._console = console or ConsoleManager()

    def check_integrity(self) -> list[Issue]:
        """Detect tampering with protected gatekeeper files."""
        return [
            Issue(
                rule="integrity",
                message=self._errors.get(key, **kwargs),
            )
            for key, kwargs in verify_integrity()
        ]

    @staticmethod
    def _ignore_dirs(data: dict) -> set[str]:
        """Directory names excluded from structure walks."""
        return {
            str(item)
            for item in data.get("ignore_dirs", [])
        }

    def check_structure(self) -> list[Issue]:
        """Validate required project structure."""
        return check_structure(
            GK_STRUCTURE,
            self._errors,
            Issue,
        )

    def check_app_py_only(self) -> list[Issue]:
        """app/ may contain Python sources only."""
        data = load_json(GK_STRUCTURE)
        return check_app_py_only(
            [str(x) for x in data.get("app_py_only", [])],
            self._ignore_dirs(data),
            self._errors,
            Issue,
        )

    def check_data_no_python(self) -> list[Issue]:
        """data/ may contain no Python sources at all."""
        data = load_json(GK_STRUCTURE)
        return check_data_no_python(
            [str(x) for x in data.get("data_no_python", [])],
            self._ignore_dirs(data),
            self._errors,
            Issue,
        )

    def check_hardcoding(self) -> list[Issue]:
        """Scan sources for hardcoding signals."""
        return check_hardcoding(
            GK_PATTERNS,
            self._errors,
            Issue,
        )

    def check_file_length(self) -> list[Issue]:
        """Validate Python file line-count limits."""
        limits = load_json(GK_LIMITS)
        max_lines = int(limits["max_file_lines"])
        files = collect_all_py_files(GK_PATTERNS)
        return check_file_length(
            files,
            max_lines,
            self._errors,
            Issue,
        )

    def check_line_length(self) -> list[Issue]:
        """Validate Python per-line character limits."""
        limits = load_json(GK_LIMITS)
        max_len = int(limits["max_line_length"])
        files = collect_all_py_files(GK_PATTERNS)
        return check_line_length(
            files,
            max_len,
            self._errors,
            Issue,
        )

    def check_pep8(self) -> list[Issue]:
        """Validate the configured PEP8 rule subset."""
        limits = load_json(GK_LIMITS)
        rules = {
            str(item)
            for item in limits.get("pep8_rules", [])
        }
        files = collect_all_py_files(GK_PATTERNS)
        return check_pep8(
            files,
            rules,
            self._errors,
            Issue,
        )

    def enforce(self) -> None:
        """Run all checks; exit process on any issue."""
        log = get_logger()
        try:
            issues = self._collect()
        except (OSError, ValueError) as exc:
            path = Path(str(exc))
            msg = self._errors.get(
                "gatekeeper.data_load_failed",
                path=str(path),
            )
            log.error(msg)
            sys.exit(1)
        if not issues:
            ok = self._errors.get("gatekeeper.ok")
            summary = self._console.format("summary_ok")
            log.info(ok)
            log.info(summary)
            return
        for item in issues:
            text = self._console.format(
                "violation",
                rule=item.rule,
                message=item.message,
            )
            log.error(text)
        fail = self._errors.get("gatekeeper.failed")
        summary = self._console.format(
            "summary_fail",
            count=len(issues),
        )
        log.error(fail)
        log.error(summary)
        sys.exit(1)

    def _collect(self) -> list[Issue]:
        """Aggregate issues from every check."""
        issues: list[Issue] = []
        issues.extend(self.check_integrity())
        issues.extend(self.check_structure())
        issues.extend(self.check_app_py_only())
        issues.extend(self.check_data_no_python())
        issues.extend(self.check_hardcoding())
        issues.extend(self.check_file_length())
        issues.extend(self.check_line_length())
        issues.extend(self.check_pep8())
        return issues
