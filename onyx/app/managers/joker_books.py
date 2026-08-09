"""Joker/Harley book seeding and night search."""

from __future__ import annotations

import json
from random import SystemRandom
from typing import Any

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.managers.chat_bridge import ChatBridge
from app.managers.text_managers import TextManager

_rng = SystemRandom()
_BOOK_ROLES = {"role_joker", "role_harley"}


async def seed_joker_books(
    chat_id: int,
    players: list[dict[str, Any]],
    roles: dict[str, str],
    keys: RedisKeySpace | None = None,
) -> int:
    """Hide books on up to 7 non-joker players."""
    keys = keys or RedisKeySpace()
    pool = [
        int(p["user_id"])
        for p in players
        if roles.get(str(p["user_id"]), "")
        not in _BOOK_ROLES
    ]
    _rng.shuffle(pool)
    holders = pool[: min(7, len(pool))]
    redis = await get_redis()
    flags = keys.game_flags(chat_id)
    await redis.hset(
        flags,
        keys.field("joker_book_holders"),
        json.dumps(holders),
    )
    await redis.hset(
        flags,
        keys.field("joker_books"),
        "0",
    )
    return len(holders)


async def resolve_joker_search(
    ctx: dict[str, Any],
    bridge: ChatBridge,
    texts: TextManager,
    lang: str,
    keys: RedisKeySpace | None = None,
) -> None:
    """Process joker/harley book search actions."""
    keys = keys or RedisKeySpace()
    chat_id = int(ctx["chat_id"])
    redis = await get_redis()
    flags = keys.game_flags(chat_id)
    raw = await redis.hget(
        flags,
        keys.field("joker_book_holders"),
    )
    try:
        holders = {
            int(x) for x in json.loads(raw or "[]")
        }
    except (TypeError, json.JSONDecodeError, ValueError):
        holders = set()
    found = int(
        await redis.hget(
            flags,
            keys.field("joker_books"),
        )
        or "0"
    )
    for player in ctx["players"]:
        if player.get("role") not in _BOOK_ROLES:
            continue
        if not player.get("alive", True):
            continue
        uid = str(player["user_id"])
        raw_t = ctx["actions"].get(uid)
        if not raw_t:
            continue
        try:
            target = int(raw_t)
        except ValueError:
            continue
        if target in holders:
            holders.discard(target)
            found += 1
            await bridge.send_text(
                int(player["user_id"]),
                texts.get(
                    "SuccessFindJoker",
                    lang,
                    found,
                    bundle="roles",
                ),
            )
        else:
            await bridge.send_text(
                int(player["user_id"]),
                texts.get(
                    "FiledFindJoker",
                    lang,
                    bundle="roles",
                ),
            )
    await redis.hset(
        flags,
        keys.field("joker_book_holders"),
        json.dumps(sorted(holders)),
    )
    await redis.hset(
        flags,
        keys.field("joker_books"),
        str(found),
    )
