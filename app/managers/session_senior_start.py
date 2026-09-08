"""Start-time senior pick (split of session_senior)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.database.models.user import UserRow
from app.database.session import session_scope
from app.managers.chat_bridge import ChatBridge
from app.managers.logger_manager import get_logger
from app.managers.text_managers import TextManager


async def ensure_senior_at_start(
    chat_id: int,
    players: list[dict[str, Any]],
    bridge: ChatBridge,
    keys: RedisKeySpace | None = None,
    texts: TextManager | None = None,
    lang: str | None = None,
) -> int | None:
    """Pick senior from game players at game start.

    Runs after role assignment so every running game has
    exactly one senior, even if no lobby tick fired.
    Strictly once per game — never force-resend.
    """
    try:
        keys = keys or RedisKeySpace()
        ids = [
            int(p["user_id"])
            for p in players
            if int(p["user_id"]) > 0
        ]
        if not ids:
            return None
        async with session_scope() as session:
            rows = (
                await session.execute(
                    select(UserRow).where(
                        UserRow.user_id.in_(
                            ids
                        )
                    )
                )
            ).scalars().all()
        by_id = {
            int(r.user_id): r
            for r in rows
        }

        def sort_key(
            uid: int,
        ) -> tuple[int, int, int]:
            row = by_id.get(uid)
            rank = (
                int(row.rank)
                if row
                else 1
            )
            xp = (
                int(row.xp) if row else 0
            )
            return (rank, xp, uid)

        best = max(ids, key=sort_key)
        try:
            redis = await get_redis()
            await redis.hset(
                keys.game_flags(chat_id),
                keys.field("session_senior"),
                str(best),
            )
        except Exception as exc:
            get_logger().exception(
                "session_senior.py: ensure_senior_a" +
                "t_start hset senior"
                "} exc={}",
                chat_id,
                best,
                exc,
            )
        return best
    except Exception as exc:
        get_logger().exception(
            "session_senior.py: ensure_senior_a" +
            "t_start chat={} exc={}",
            chat_id,
            exc,
        )
        return None
