"""Enchanter marked-uid list helpers (Redis JSON)."""

from __future__ import annotations

import json


def parse_list(raw: str | None) -> list[str]:
    """Parse Redis enchanter_list JSON to uid strings."""
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return [str(x) for x in data]


def append_uid(
    current: list[str],
    uid: str | int,
) -> list[str]:
    """Append uid if missing; return new list."""
    s = str(uid)
    if s in current:
        return list(current)
    return list(current) + [s]


def remove_uid(
    current: list[str],
    uid: str | int,
) -> list[str]:
    """Drop uid from list."""
    s = str(uid)
    return [x for x in current if x != s]


def dumps(uids: list[str]) -> str:
    """Serialize list for Redis / flags_out."""
    return json.dumps(list(uids))
