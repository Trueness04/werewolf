"""Pick session senior (highest rank) and send PV panel."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.settings import get_settings
from app.database.models.group import GroupRow
from app.database.models.user import UserRow
from app.database.session import session_scope
from app.keyboards.inline.senior_keyboard import (
    build_senior_keyboard,
)
from app.managers.chat_bridge import ChatBridge
from app.managers.game_event import log_game_event
from app.managers.lobby_manager import LobbyManager
from app.managers.logger_manager import get_logger
from app.managers.text_managers import TextManager


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
                "session_senior.py: pick_session_senior hset chat={} exc={}",
                chat_id,
                exc,
            )
        return best
    except Exception as exc:
        get_logger().exception(
            "session_senior.py: pick_session_senior chat={} exc={}",
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
            "session_senior.py: roles_locked chat={} exc={}",
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
                    "session_senior.py: read_panel_flags hget field={} chat={} exc={}",
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
            "session_senior.py: read_panel_flags chat={} exc={}",
            chat_id,
            exc,
        )
        return {
            "magic_allowed": True,
            "mute_die": False,
            "secret_vote": False,
            "vampire_on": True,
            "blood_on": True,
        }


async def send_senior_panel(
    chat_id: int,
    senior_id: int,
    *,
    bridge: ChatBridge,
    texts: TextManager | None = None,
    keys: RedisKeySpace | None = None,
    lang: str | None = None,
    force: bool = False,
) -> None:
    """DM «پنل کنترل بازی» once per game — strictly once.

    هر پنلی فقط ۱ بار در هر بازی نمایش داده میشه؛ کیبوردها ادیت/دیلیت نمیشن.
    force is kept for compat but never bypasses the once-per-game guard.
    """
    try:
        keys = keys or RedisKeySpace()
        texts = texts or TextManager()
        lang = lang or get_settings().default_lang
        try:
            redis = await get_redis()
            flags = keys.game_flags(chat_id)
            sent = await redis.hget(
                flags,
                keys.field("senior_panel_sent"),
            )
        except Exception as exc:
            get_logger().exception(
                "session_senior.py: send_senior_panel hget sent chat={} senior={} exc={}",
                chat_id,
                senior_id,
                exc,
            )
            sent = None
            redis = await get_redis()
            flags = keys.game_flags(chat_id)
        # strictly once per game: if already sent, never resend (force ignored)
        if sent:
            return
        # AI players have negative IDs — skip DM for them
        if senior_id < 0:
            try:
                log_game_event(
                    "session_senior_panel_skipped_ai",
                    chat_id=chat_id,
                    user_id=senior_id,
                )
            except Exception as exc:
                get_logger().exception(
                    "session_senior.py: send_senior_panel log skipped chat={} senior={} exc={}",
                    chat_id,
                    senior_id,
                    exc,
                )
            return
        try:
            panel = await read_panel_flags(chat_id, keys)
        except Exception as exc:
            get_logger().exception(
                "session_senior.py: send_senior_panel read_panel_flags chat={} exc={}",
                chat_id,
                exc,
            )
            panel = {
                "magic_allowed": True,
                "mute_die": False,
                "secret_vote": False,
                "vampire_on": True,
                "blood_on": True,
            }
        try:
            locked = await roles_locked(chat_id, keys)
        except Exception as exc:
            get_logger().exception(
                "session_senior.py: send_senior_panel roles_locked chat={} exc={}",
                chat_id,
                exc,
            )
            locked = False
        try:
            markup = build_senior_keyboard(
                texts,
                lang,
                chat_id,
                magic_allowed=panel["magic_allowed"],
                mute_die=panel["mute_die"],
                secret_vote=panel["secret_vote"],
                vampire_on=panel["vampire_on"],
                blood_on=panel["blood_on"],
                roles_locked=locked,
            )
        except Exception as exc:
            get_logger().exception(
                "session_senior.py: send_senior_panel build_keyboard chat={} exc={}",
                chat_id,
                exc,
            )
            return
        try:
            title = texts.get(
                "SessionSeniorPanelTitle",
                lang,
                bundle="lobby",
            )
            body = texts.get(
                "SessionSeniorPanelBody",
                lang,
                bundle="lobby",
            )
        except Exception as exc:
            get_logger().exception(
                "session_senior.py: send_senior_panel texts.get chat={} exc={}",
                chat_id,
                exc,
            )
            title = "panel"
            body = ""
        try:
            msg_id = await bridge.send_text(
                senior_id,
                f"<b>{title}</b>\n\n{body}",
                reply_markup=markup,
            )
        except Exception as exc:
            get_logger().exception(
                "session_senior.py: send_senior_panel send_text chat={} senior={} exc={}",
                chat_id,
                senior_id,
                exc,
            )
            return
        if not msg_id:
            # Panel not delivered — don't mark as sent so next tick retries
            return
        try:
            await redis.hset(
                flags,
                keys.field("senior_panel_sent"),
                str(senior_id),
            )
        except Exception as exc:
            get_logger().exception(
                "session_senior.py: send_senior_panel hset sent chat={} senior={} exc={}",
                chat_id,
                senior_id,
                exc,
            )
            return
        try:
            log_game_event(
                "session_senior_panel",
                chat_id=chat_id,
                user_id=senior_id,
            )
        except Exception as exc:
            get_logger().exception(
                "session_senior.py: send_senior_panel log event chat={} senior={} exc={}",
                chat_id,
                senior_id,
                exc,
            )
    except Exception as exc:
        get_logger().exception(
            "session_senior.py: send_senior_panel chat={} senior={} exc={}",
            chat_id,
            senior_id,
            exc,
        )


async def maybe_refresh_session_senior(
    chat_id: int,
    *,
    bridge: ChatBridge,
    texts: TextManager | None = None,
    keys: RedisKeySpace | None = None,
    lobby: LobbyManager | None = None,
    lang: str | None = None,
) -> int | None:
    """Recompute senior on lobby join updates; send panel once per game."""
    try:
        keys = keys or RedisKeySpace()
        redis = await get_redis()
        try:
            locked = await roles_locked(chat_id, keys)
        except Exception as exc:
            get_logger().exception(
                "session_senior.py: maybe_refresh roles_locked chat={} exc={}",
                chat_id,
                exc,
            )
            locked = False
        if locked:
            try:
                raw = await redis.hget(
                    keys.game_flags(chat_id),
                    keys.field("session_senior"),
                )
            except Exception as exc:
                get_logger().exception(
                    "session_senior.py: maybe_refresh hget senior chat={} exc={}",
                    chat_id,
                    exc,
                )
                raw = None
            return int(raw) if raw else None
        senior = await pick_session_senior(
            chat_id,
            keys=keys,
            lobby=lobby,
        )
        if senior is None:
            return None
        # Frozen panel: update stored senior (already done in pick), but skip resend if panel already sent once
        try:
            prev = await redis.hget(
                keys.game_flags(chat_id),
                keys.field("senior_panel_sent"),
            )
        except Exception as exc:
            get_logger().exception(
                "session_senior.py: maybe_refresh hget sent chat={} exc={}",
                chat_id,
                exc,
            )
            prev = None
        if prev:
            # هر پنلی فقط ۱ بار در هر بازی نمایش داده میشه — do not force-resend on turnover
            return senior
        try:
            await send_senior_panel(
                chat_id,
                senior,
                bridge=bridge,
                texts=texts,
                keys=keys,
                lang=lang,
            )
        except Exception as exc:
            get_logger().exception(
                "session_senior.py: maybe_refresh send_panel chat={} senior={} exc={}",
                chat_id,
                senior,
                exc,
            )
        return senior
    except Exception as exc:
        get_logger().exception(
            "session_senior.py: maybe_refresh_session_senior chat={} exc={}",
            chat_id,
            exc,
        )
        return None


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
            "session_senior.py: is_session_senior chat={} user={} exc={}",
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
            "session_senior.py: _group_row chat={} exc={}",
            chat_id,
            exc,
        )
        return None


async def ensure_senior_at_start(
    chat_id: int,
    players: list[dict[str, Any]],
    *,
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
                "session_senior.py: ensure_senior_at_start hset senior chat={} best={} exc={}",
                chat_id,
                best,
                exc,
            )
        # Once-per-game: do not force; send_senior_panel guards on senior_panel_sent
        try:
            await send_senior_panel(
                chat_id,
                best,
                bridge=bridge,
                texts=texts,
                keys=keys,
                lang=lang,
            )
        except Exception as exc:
            get_logger().exception(
                "session_senior.py: ensure_senior_at_start send_panel chat={} best={} exc={}",
                chat_id,
                best,
                exc,
            )
        return best
    except Exception as exc:
        get_logger().exception(
            "session_senior.py: ensure_senior_at_start chat={} exc={}",
            chat_id,
            exc,
        )
        return None
