"""Remove a player from an active join lobby."""

from __future__ import annotations

import json

from sqlalchemy import select

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.database.models.player import PlayerRow
from app.database.session import session_scope
from app.managers.game_event import log_game_event


async def unregister_lobby_player(
    keys: RedisKeySpace,
    chat_id: int,
    user_id: int,
) -> bool:
    """Remove player from join lobby; False if absent."""
    redis = await get_redis()
    key = keys.game_hash(chat_id)
    field = keys.field("player_list")
    raw = await redis.hget(key, field)
    players = json.loads(raw) if raw else []
    if not isinstance(players, list):
        return False
    kept = [
        p
        for p in players
        if int(p.get("user_id", 0)) != user_id
    ]
    if len(kept) == len(players):
        return False
    await redis.hset(
        key,
        field,
        json.dumps(kept, ensure_ascii=False),
    )
    game_id = int(
        await redis.hget(key, keys.field("game_id"))
        or "0"
    )
    if game_id:
        async with session_scope() as session:
            stmt = select(PlayerRow).where(
                PlayerRow.game_id == game_id,
                PlayerRow.user_id == user_id,
            )
            row = (
                await session.execute(stmt)
            ).scalar_one_or_none()
            if row is not None:
                await session.delete(row)
    await redis.delete(keys.join_user(user_id))
    log_game_event(
        "player_fled",
        chat_id=chat_id,
        user_id=user_id,
        game_id=game_id,
    )
    return True
