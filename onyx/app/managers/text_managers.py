"""Text loading and caching from data/text."""

from __future__ import annotations

import json
import re
from pathlib import Path
from random import SystemRandom
from typing import Any

from app.config.paths import TEXT_DIR
from app.config.settings import get_settings

_Entry = str | list[str]


class TextManager:
    """Loads localized strings from data/text."""

    def __init__(self) -> None:
        self._cache: dict[str, dict[str, _Entry]] = {}
        self._rng = SystemRandom()

    def _bundle_path(self, lang: str, name: str) -> Path:
        """Return path to a language JSON bundle."""
        return TEXT_DIR / lang / f"{name}.json"

    def _load_bundle(
        self,
        lang: str,
        name: str,
    ) -> dict[str, _Entry]:
        """Load one language bundle into cache."""
        cache_key = f"{lang}:{name}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        path = self._bundle_path(lang, name)
        settings = get_settings()
        if not path.is_file():
            path = self._bundle_path(
                settings.fallback_lang,
                name,
            )
        with path.open(encoding="utf-8-sig") as handle:
            raw: Any = json.load(handle)
        data: dict[str, _Entry] = {}
        for key, value in raw.items():
            if isinstance(value, list):
                data[str(key)] = [str(item) for item in value]
            else:
                data[str(key)] = str(value)
        self._cache[cache_key] = data
        return data

    def _pick(self, entry: _Entry | None, key: str) -> str:
        """Pick one string; lists choose at random."""
        if entry is None:
            return key
        if isinstance(entry, list):
            if not entry:
                return key
            return self._rng.choice(entry)
        return entry

    def get(
        self,
        key: str,
        lang: str,
        *args: object,
        bundle: str = "lobby",
    ) -> str:
        """Return text for key; random if multi-value."""
        data = self._load_bundle(lang, bundle)
        if key not in data:
            settings = get_settings()
            data = self._load_bundle(
                settings.fallback_lang,
                bundle,
            )
        raw = data.get(key)
        if isinstance(raw, list):
            text = self._pick(raw, key)
        elif isinstance(raw, str):
            text = raw
        else:
            text = key
        if not isinstance(text, str):
            text = key
        if args:
            try:
                return text.format(*args)
            except (IndexError, KeyError, ValueError):
                return text
        if "{" in text:
            return re.sub(r"\{\d+\}", "", text).rstrip()
        return text
