"""Pick session senior (highest rank) and send PV panel."""

from __future__ import annotations

from sqlalchemy import select

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.database.models.group import GroupRow
from app.database.models.user import UserRow
from app.database.session import session_scope
from app.managers.logger_manager import get_logger
from app.managers.lobby_manager import LobbyManager

from app.managers.session_senior_panel import (  # noqa: F401
    maybe_refresh_session_senior,
    send_senior_panel,
)
from app.managers.session_senior_start import (  # noqa: F401
    ensure_senior_at_start,
)


async def pick_session_senior(
    chat_id: int,
    *,
    keys: RedisKeySpace | None = None,
    lobby: LobbyManager | None = None,
) -> int | None:
    """Highest rank among lobby; ties: xp, then user_id."""
    try:
        keys = keys or RedisKeySpace()
        lobby = lobby or LobbyManager()
        players = await lobby.list_players(chat_id)
        if not players:
            return None
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
                        UserRow.user_id.in_(ids)
                    )
                )
            ).scalars().all()
        by_id = {int(r.user_id): r for r in rows}

        def sort_key(uid: int) -> tuple[int, int, int]:
            row = by_id.get(uid)
            rank = int(row.rank) if row is not None else 1
            xp = int(row.xp) if row is not None else 0
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
                "session_senior.py:.pick_session_senior"
                + "hset.chat={}.exc={}",
                chat_id,
                exc,
            )
        return best
    except Exception as exc:
        get_logger().exception(
            "session_senior.py:.pick_session_senior"
            + "chat={}.exc={}",
            chat_id,
            exc,
        )
        return None


async def roles_locked(
    chat_id: int,
    keys: RedisKeySpace | None = None,
) -> bool:
    """True after leave join (roles assigned / running)."""
    try:
        keys = keys or RedisKeySpace()
        redis = await get_redis()
        state = await redis.hget(
            keys.game_hash(chat_id),
            keys.field("game_state"),
        )
        if not state:
            return False
        return str(state) != "join"
    except Exception as exc:
        get_logger().exception(
            "session_senior.py:.roles_locked.chat={}"
            + "exc={}",
            chat_id,
            exc,
        )
        return False


async def read_panel_flags(
    chat_id: int,
    keys: RedisKeySpace | None = None,
) -> dict[str, bool]:
    """Session flags with group defaults."""
    try:
        keys = keys or RedisKeySpace()
        redis = await get_redis()
        flags = keys.game_flags(chat_id)
        group = await _group_row(chat_id)

        async def flag(
            field: str,
            default: bool,
        ) -> bool:
            try:
                raw = await redis.hget(flags, keys.field(field))
            except Exception as exc:
                get_logger().exception(
                    "session_senior.py:.read_panel_flags.hget"
                    + "field={}.chat={}.exc={}",
                    field,
                    chat_id,
                    exc,
                )
                return default
            if raw is None:
                return default
            return str(raw) not in ("0", "false", "no", "")

        vamp_def = bool(
            getattr(group, "vampire_role_on", True)
            if group
            else True
        )
        blood_def = bool(
            getattr(group, "bloodthirsty_role_on", True)
            if group
            else True
        )
        mute_def = bool(
            getattr(group, "mute_die", False)
            if group
            else False
        )
        secret_def = bool(
            getattr(group, "secret_vote", False)
            if group
            else False
        )
        return {
            "magic_allowed": await flag(
                "magic_allowed",
                True,
            ),
            "mute_die": await flag("mute_die", mute_def),
            "secret_vote": await flag(
                "secret_vote",
                secret_def,
            ),
            "vampire_on": await flag(
                "vampire_role_on",
                vamp_def,
            ),
            "blood_on": await flag(
                "bloodthirsty_role_on",
                blood_def,
            ),
        }
    except Exception as exc:
        get_logger().exception(
            "senior.read_flags",
            exc,
        )
        return {
            "magic_allowed": True,
            "mute_die": False,
            "secret_vote": False,
            "vampire_on": True,
            "blood_on": True,
        }


async def is_session_senior(
    chat_id: int,
    user_id: int,
    keys: RedisKeySpace | None = None,
) -> bool:
    """True if user_id matches SessionSenior flag."""
    try:
        keys = keys or RedisKeySpace()
        redis = await get_redis()
        raw = await redis.hget(
            keys.game_flags(chat_id),
            keys.field("session_senior"),
        )
        if not raw:
            return False
        return int(raw) == int(user_id)
    except Exception as exc:
        get_logger().exception(
            "session_senior.py:.is_session_senior"
            + "chat={}.user={}.exc={}",
            chat_id,
            user_id,
            exc,
        )
        return False


async def _group_row(chat_id: int) -> GroupRow | None:
    try:
        async with session_scope() as session:
            return (
                await session.execute(
                    select(GroupRow).where(
                        GroupRow.chat_id == chat_id
                    )
                )
            ).scalar_one_or_none()
    except Exception as exc:
        get_logger().exception(
            "session_senior.py:._group_row.chat={}"
            + "exc={}",
            chat_id,
            exc,
        )
        return None
