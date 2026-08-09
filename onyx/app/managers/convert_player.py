"""ConvertPlayer: Redis + DB role/team swap."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.database.models.player import PlayerRow
from app.database.session import session_scope
from importlib import import_module

_Registry = import_module(
    "app.class.roles.registry"
).RoleRegistry


async def convert_player(
    chat_id: int,
    user_id: int,
    new_role: str,
    *,
    keys: RedisKeySpace | None = None,
) -> bool:
    """Set role+team in Redis and DB. True if ok."""
    keys = keys or RedisKeySpace()
    redis = await get_redis()
    registry = _Registry()
    try:
        info = registry.definition(new_role)
    except Exception:
        return False
    team = str(info.get("team") or "villager")
    roles_raw = await redis.get(keys.game_roles(chat_id))
    roles: dict[str, Any] = (
        json.loads(roles_raw) if roles_raw else {}
    )
    roles[str(user_id)] = new_role
    await redis.set(
        keys.game_roles(chat_id),
        json.dumps(roles),
    )
    await redis.set(keys.player_role(user_id), new_role)
    game_id = int(
        await redis.hget(
            keys.game_hash(chat_id),
            keys.field("game_id"),
        )
        or "0"
    )
    if not game_id:
        return True
    async with session_scope() as session:
        stmt = select(PlayerRow).where(
            PlayerRow.game_id == game_id,
            PlayerRow.user_id == user_id,
        )
        row = (
            await session.execute(stmt)
        ).scalar_one_or_none()
        if row is None:
            return True
        row.role = new_role
        row.team = team
    return True
