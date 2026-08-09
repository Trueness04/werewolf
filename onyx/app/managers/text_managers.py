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
# Sprint 6: phase bundle → optional mode catalog → general → main.
_CATALOG_FALLBACK = ("general", "main")


class TextManager:
    """Loads localized strings from data/text."""

    def __init__(
        self,
        default_mode: str | None = None,
    ) -> None:
        self._cache: dict[str, dict[str, _Entry]] = {}
        self._rng = SystemRandom()
        self._default_mode = default_mode

    def _bundle_path(self, lang: str, name: str) -> Path:
        """Return path to a language JSON bundle."""
        return TEXT_DIR / lang / f"{name}.json"

    def _load_bundle(
        self,
        lang: str,
        name: str,
        *,
        required: bool = True,
    ) -> dict[str, _Entry]:
        """Load one language bundle into cache."""
        cache_key = f"{lang}:{name}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        path = self._bundle_path(lang, name)
        if not path.is_file():
            if not required:
                self._cache[cache_key] = {}
                return {}
            settings = get_settings()
            path = self._bundle_path(
                settings.fallback_lang,
                name,
            )
            if not path.is_file():
                self._cache[cache_key] = {}
                return {}
        with path.open(encoding="utf-8-sig") as handle:
            raw: Any = json.load(handle)
        data: dict[str, _Entry] = {}
        for key, value in raw.items():
            if isinstance(value, list):
                data[str(key)] = [
                    str(item) for item in value
                ]
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

    def _resolve_entry(
        self,
        key: str,
        lang: str,
        bundle: str,
        mode: str | None,
    ) -> _Entry | None:
        """Bundle → optional mode catalog → general → main."""
        settings = get_settings()
        catalogs: list[str] = []
        active = mode if mode is not None else self._default_mode
        if active and active != "general":
            catalogs.append(active)
        catalogs.extend(_CATALOG_FALLBACK)
        seen: set[str] = set()
        ordered: list[str] = []
        for name in (bundle, *catalogs):
            if name in seen:
                continue
            seen.add(name)
            ordered.append(name)
        for lng in (lang, settings.fallback_lang):
            for name in ordered:
                required = name == bundle and lng == lang
                data = self._load_bundle(
                    lng,
                    name,
                    required=required,
                )
                if key in data:
                    return data[key]
        return None

    def get(
        self,
        key: str,
        lang: str,
        *args: object,
        bundle: str = "lobby",
        mode: str | None = None,
    ) -> str:
        """Return text for key; random if multi-value."""
        raw = self._resolve_entry(
            key,
            lang,
            bundle,
            mode,
        )
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
