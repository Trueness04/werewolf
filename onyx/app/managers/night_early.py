"""Pull night timer early when all actors acted."""

from __future__ import annotations

import json
from time import time

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.settings import get_settings
from importlib import import_module

_Registry = import_module(
    "app.class.roles.registry"
).RoleRegistry


async def maybe_early_end_night(
    chat_id: int,
    keys: RedisKeySpace | None = None,
) -> None:
    """Half timer elapsed + all actors chose → cut."""
    keys = keys or RedisKeySpace()
    redis = await get_redis()
    roles_raw = await redis.get(keys.game_roles(chat_id))
    players_raw = await redis.get(
        keys.game_players(chat_id)
    )
    if not roles_raw or not players_raw:
        return
    roles = json.loads(roles_raw)
    players = json.loads(players_raw)
    registry = _Registry()
    needed: set[str] = set()
    for item in players:
        uid = str(item["user_id"])
        state = await redis.get(
            keys.player_state(int(uid))
        )
        if state == "dead":
            continue
        role_id = roles.get(uid)
        if not role_id:
            continue
        role = registry.create(str(role_id))
        if role.night1_active:
            needed.add(uid)
    if not needed:
        return
    actions = await redis.hgetall(
        keys.night_actions(chat_id)
    )
    if not needed.issubset(set(actions.keys())):
        return
    end_raw = await redis.get(keys.timer_end(chat_id))
    if not end_raw:
        return
    settings = get_settings()
    duration = int(settings.night_duration_seconds)
    half = max(duration // 2, 1)
    end_at = int(end_raw)
    started = end_at - duration
    if int(time()) < started + half:
        return
    await redis.set(
        keys.timer_end(chat_id),
        str(int(time()) - 5),
    )
