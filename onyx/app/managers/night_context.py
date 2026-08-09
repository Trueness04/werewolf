"""Build night resolution context from Redis."""

from __future__ import annotations

import json
from typing import Any

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from importlib import import_module

_Registry = import_module(
    "app.class.roles.registry"
).RoleRegistry


async def build_night_context(
    chat_id: int,
    keys: RedisKeySpace,
) -> dict[str, Any]:
    """Load players, roles, actions, flags into ctx."""
    redis = await get_redis()
    registry = _Registry()
    players = json.loads(
        await redis.get(keys.game_players(chat_id))
        or "[]"
    )
    roles = json.loads(
        await redis.get(keys.game_roles(chat_id)) or "{}"
    )
    actions = await redis.hgetall(
        keys.night_actions(chat_id)
    )
    flags = keys.game_flags(chat_id)
    enriched: list[dict[str, Any]] = []
    for item in players:
        uid = str(item["user_id"])
        rid = roles.get(uid)
        state = await redis.get(
            keys.player_state(int(uid))
        )
        alive = state != "dead"
        info = registry.definition(rid) if rid else {}
        enriched.append(
            {
                **item,
                "role": rid,
                "team": info.get("team"),
                "alive": alive,
            }
        )

    async def flag(name: str) -> str | None:
        return await redis.hget(flags, keys.field(name))

    night_raw = await redis.get(keys.night_count(chat_id))
    phoenix = await flag("phoenix_healer")
    heals: set[int] = set()
    if phoenix:
        try:
            heals.add(int(phoenix))
        except ValueError:
            pass
    return {
        "chat_id": chat_id,
        "players": enriched,
        "roles": roles,
        "actions": actions,
        "night_no": int(night_raw or "0"),
        "wolf_target": None,
        "sk_target": None,
        "protected": None,
        "cult_target": None,
        "natasha_host": None,
        "natasha_id": None,
        "silver_active": bool(
            await flag("silver_active")
        ),
        "mast_block": bool(await flag("mast_block")),
        "elder_used": bool(await flag("elder_saved")),
        "wild_child_model": await flag("wild_child_model"),
        "wild_child_id": await flag("wild_child_id"),
        "wolf_cube_pending": bool(
            await flag("wolf_cube_dead")
        ),
        "send_wolf_cube_dead": bool(
            await flag("send_wolf_cube_dead")
        ),
        "hunter_kill_pending": bool(
            await flag("hunter_kill")
        ),
        "royce_pending": bool(await flag("royce_dead")),
        "check_night_done": bool(
            await flag("check_night_done")
        ),
        "phoenix_heals": heals,
        "franc_guard": set(),
        "huntsman_trap": None,
        "alpha_dead": bool(await flag("alpha_dead")),
        "enchanter_mark": await flag("enchanter_mark"),
        "vampire_convert": await flag("vampire_convert"),
        "flags_out": {},
        "deaths": set(),
        "seer_notes": [],
        "messages": [],
        "stop_night": False,
        "defer_day": False,
        "extend_seconds": 0,
    }
