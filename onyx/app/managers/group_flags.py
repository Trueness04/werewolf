"""Load per-group gameplay toggles (session override)."""

from __future__ import annotations

from sqlalchemy import select

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.settings import get_settings
from app.database.models.group import GroupRow
from app.database.session import session_scope


async def _session_flag(
    chat_id: int,
    field: str,
) -> bool | None:
    """Session override from game flags; None if unset."""
    keys = RedisKeySpace()
    redis = await get_redis()
    raw = await redis.hget(
        keys.game_flags(chat_id),
        keys.field(field),
    )
    if raw is None:
        return None
    return str(raw) not in ("0", "false", "no", "")


async def group_secret_vote(chat_id: int) -> bool:
    """Session secret_vote override, else group/env."""
    ov = await _session_flag(chat_id, "secret_vote")
    if ov is not None:
        return ov
    async with session_scope() as session:
        row = (
            await session.execute(
                select(GroupRow).where(
                    GroupRow.chat_id == chat_id
                )
            )
        ).scalar_one_or_none()
        if row is not None:
            return bool(
                getattr(row, "secret_vote", False)
            )
    return bool(get_settings().secret_vote)


async def group_mute_die(chat_id: int) -> bool:
    """Session mute_die override, else group setting."""
    ov = await _session_flag(chat_id, "mute_die")
    if ov is not None:
        return ov
    async with session_scope() as session:
        row = (
            await session.execute(
                select(GroupRow).where(
                    GroupRow.chat_id == chat_id
                )
            )
        ).scalar_one_or_none()
        if row is not None:
            return bool(
                getattr(row, "mute_die", False)
            )
    return False
