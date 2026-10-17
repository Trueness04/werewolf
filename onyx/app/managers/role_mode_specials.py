"""Mode-specific role pool helpers."""

from __future__ import annotations

import json
from typing import Any

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace


def foolish_roles(need: int) -> list[str]:
    """Foolish early pool: 1 wolf + seer + fools."""
    roles = ["role_wolf", "role_pishgo"]
    while len(roles) < need:
        roles.append("role_Fool")
    return roles[:need]



async def romantic_pairs(
    chat_id: int,
    players: list[dict[str, Any]],
    keys: RedisKeySpace | None = None,
) -> None:
    """Pair seats with neighbor (+1 / last−1)."""
    keys = keys or RedisKeySpace()
    uids = [int(p["user_id"]) for p in players]
    if len(uids) < 2:
        return
    pairs: list[list[int]] = []
    for index in range(0, len(uids) - 1, 2):
        pairs.append([uids[index], uids[index + 1]])
    if len(uids) % 2 == 1:
        pairs.append([uids[-1], uids[-2]])
    redis = await get_redis()
    await redis.hset(
        keys.game_flags(chat_id),
        mapping={
            keys.field("lover_pair"): (
                f"{pairs[0][0]}:{pairs[0][1]}"
            ),
            keys.field("lover_pairs"): json.dumps(pairs),
        },
    )
