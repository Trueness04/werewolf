"""Load JSON documents from data/config."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


@lru_cache(maxsize=32)
def load_cached_json(path_str: str) -> Any:
    """Load and cache JSON by absolute path string."""
    with Path(path_str).open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def load_json(path: Path) -> Any:
    """Load JSON from a Path (cached)."""
    return load_cached_json(str(path.resolve()))
