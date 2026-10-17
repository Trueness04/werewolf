"""Filter magic-ghost players from target lists."""

from __future__ import annotations

from typing import Any

from app.cache.redis_keys import RedisKeySpace
from app.managers.magic_effects import is_magic_ghost


async def without_magic_ghosts(
    chat_id: int,
    targets: list[tuple[int, str]],
    keys: RedisKeySpace | None = None,
) -> list[tuple[int, str]]:
    """Drop MajikGhost-hidden users from (uid, name) list."""
    keys = keys or RedisKeySpace()
    out: list[tuple[int, str]] = []
    for uid, name in targets:
        if await is_magic_ghost(chat_id, uid, keys):
            continue
        out.append((uid, name))
    return out


async def players_without_ghosts(
    chat_id: int,
    players: list[dict[str, Any]],
    keys: RedisKeySpace | None = None,
) -> list[dict[str, Any]]:
    """Drop ghost users from player dict list."""
    keys = keys or RedisKeySpace()
    out: list[dict[str, Any]] = []
    for p in players:
        uid = int(p["user_id"])
        if await is_magic_ghost(chat_id, uid, keys):
            continue
        out.append(p)
    return out
