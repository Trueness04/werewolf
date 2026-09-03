"""Sanitize AI day-chat LLM output."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config.paths import ROOT

_CFG = ROOT / "data" / "config" / "chat_clean.json"


@lru_cache(maxsize=1)
def _patterns() -> dict[str, Any]:
    """Load and compile chat-clean regexes."""
    raw = json.loads(_CFG.read_text(encoding="utf-8"))
    return {
        "cjk": re.compile(str(raw["cjk"])),
        "camel": re.compile(str(raw["camel"])),
        "latin": re.compile(str(raw["latin_word"])),
        "space": re.compile(str(raw["space"])),
        "min_fa": int(raw["min_persian_chars"]),
        "ratio": float(raw["min_persian_ratio"]),
        "max_len": int(raw["max_len"]),
    }


def clean_chat_line(
    text: str,
    *,
    max_len: int | None = None,
) -> str:
    """Return clean Persian line, or empty if junk."""
    cfg = _patterns()
    limit = max_len if max_len is not None else cfg["max_len"]
    space: re.Pattern[str] = cfg["space"]
    line = space.sub(" ", str(text or "")).strip()
    if not line:
        return ""
    if cfg["cjk"].search(line):
        return ""
    if cfg["camel"].search(line):
        return ""
    latin = cfg["latin"].findall(line)
    if len(latin) >= 2:
        return ""
    if latin:
        for word in latin:
            line = line.replace(word, "")
        line = space.sub(" ", line).strip(" :،,-")
    persian = sum(
        1 for ch in line if "\u0600" <= ch <= "\u06FF"
    )
    if persian < cfg["min_fa"]:
        return ""
    if persian / max(len(line), 1) < cfg["ratio"]:
        return ""
    return line[: int(limit)]
