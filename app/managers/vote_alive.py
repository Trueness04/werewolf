"""Living player list for vote UI/targets."""

from __future__ import annotations

import json
from typing import Any

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace


async def load_vote_alive(
    keys: RedisKeySpace,
    chat_id: int,
) -> list[dict[str, Any]]:
    """Living players for vote UI/targets."""
    redis = await get_redis()
    raw = await redis.get(keys.game_players(chat_id))
    players = json.loads(raw) if raw else []
    out: list[dict[str, Any]] = []
    for item in players:
        uid = int(item["user_id"])
        state = await redis.get(keys.player_state(uid))
        if state == "dead":
            continue
        out.append(item)
    from app.managers.magic_targets import (
        players_without_ghosts,
    )

    return await players_without_ghosts(
        chat_id,
        out,
        keys,
    )