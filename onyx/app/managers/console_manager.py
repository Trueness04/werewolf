"""Console output templates from data/console."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config.paths import GK_CONSOLE
from app.managers.logger_manager import setup_loguru


class ConsoleManager:
    """Formats console messages using JSON templates."""

    def __init__(
        self,
        template_path: Path | None = None,
    ) -> None:
        self._path = template_path or GK_CONSOLE
        self._templates: dict[str, str] = {}
        self.reload()

    def reload(self) -> None:
        """Reload console templates from disk."""
        with self._path.open(encoding="utf-8") as handle:
            raw: Any = json.load(handle)
        if not isinstance(raw, dict):
            self._templates = {}
            return
        self._templates = {
            str(key): str(value)
            for key, value in raw.items()
        }

    def format(self, key: str, **kwargs: object) -> str:
        """Return a formatted console string by key."""
        template = self._templates.get(key, key)
        if kwargs:
            return template.format(**kwargs)
        return template

    @staticmethod
    def setup_logging() -> None:
        """Configure loguru (compat shim)."""
        setup_loguru(debug_mode=False)
