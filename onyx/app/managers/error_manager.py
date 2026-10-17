"""Load and format error messages from data/text."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config.paths import ERRORS_JSON


class ErrorManager:
    """Reads error templates from errors.json."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or ERRORS_JSON
        self._data: dict[str, str] = {}
        self.reload()

    def reload(self) -> None:
        """Reload error templates from disk."""
        with self._path.open(encoding="utf-8") as handle:
            raw: Any = json.load(handle)
        if not isinstance(raw, dict):
            self._data = {}
            return
        self._data = {
            str(key): str(value) for key, value in raw.items()
        }

    def get(self, key: str, **kwargs: object) -> str:
        """Return a formatted error string by key."""
        template = self._data.get(key, key)
        if kwargs:
            return template.format(**kwargs)
        return template
