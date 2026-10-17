"""Load day/night player snapshots from Redis."""

from __future__ import annotations

import json
from typing import Any

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from importlib import import_module

_Registry = import_module(
    "app.class.roles.registry"
).RoleRegistry


async def load_enriched_players(
    keys: RedisKeySpace,
    chat_id: int,
) -> list[dict[str, Any]]:
    """Living/dead players with role and team."""
    redis = await get_redis()
    registry = _Registry()
    raw = await redis.get(keys.game_players(chat_id))
    roles_raw = await redis.get(keys.game_roles(chat_id))
    players = json.loads(raw) if raw else []
    roles = json.loads(roles_raw) if roles_raw else {}
    out: list[dict[str, Any]] = []
    for item in players:
        uid = str(item["user_id"])
        role_id = roles.get(uid)
        state = await redis.get(
            keys.player_state(int(uid))
        )
        alive = state != "dead"
        info = (
            registry.definition(role_id) if role_id else {}
        )
        out.append(
            {
                **item,
                "role": role_id,
                "team": info.get("team"),
                "alive": alive,
            }
        )
    return out
