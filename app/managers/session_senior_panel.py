"""Senior panel send/refresh (split of session_senior)."""

from __future__ import annotations

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.settings import get_settings
from app.keyboards.inline.senior_keyboard import (
    build_senior_keyboard,
)


from app.managers.chat_bridge import ChatBridge
from app.managers.game_event import log_game_event
from app.managers.logger_manager import get_logger
from app.managers.lobby_manager import LobbyManager


from app.managers.text_managers import TextManager


async def send_senior_panel(
    chat_id: int,
    senior_id: int,
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
    from app.managers.session_senior import (
        read_panel_flags,
        roles_locked,
    )

    keys = keys or RedisKeySpace()
    texts = texts or TextManager()
    lang = lang or get_settings().default_lang
    redis = await get_redis()
    flags = keys.game_flags(chat_id)
    try:
        sent = await redis.hget(
            flags,
            keys.field("senior_panel_sent"),
        )
    except Exception as exc:
        get_logger().exception(
            "session_senior.py:"
            + ".send_senior_panel"
            + "hget.sent.chat={}"
            + "senior={}.exc={}",
            chat_id,
            senior_id,
            exc,
        )
        sent = None
        redis = await get_redis()
        flags = keys.game_flags(chat_id)
    if sent:
        return
    if senior_id < 0:
        try:
            log_game_event(
                "session_senior_panel_skipped_ai",
                chat_id=chat_id,
                user_id=senior_id,
            )
        except Exception as exc:
            get_logger().exception(
                "senior.log_skipped.c={c}.s={s}.e={e}",
                chat_id,
                senior_id,
                exc,
            )
        return
    try:
        panel = await read_panel_flags(
            chat_id, keys
        )
    except Exception as exc:
        get_logger().exception(
            "session_senior.py:.send_senior_pan" +
            "el.read_panel_flags.chat={}.exc={}",
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
        locked = await roles_locked(
            chat_id, keys
        )
    except Exception as exc:
        get_logger().exception(
            "session_senior.py:.send_senior_pan" +
            "el.roles_locked.chat={}.exc={}",
            chat_id,
            exc,
        )
        locked = False
    try:
        markup = build_senior_keyboard(
            texts,
            lang,
            chat_id,
            magic_allowed=panel[
                "magic_allowed"
            ],
            mute_die=panel["mute_die"],
            secret_vote=panel["secret_vote"],
            vampire_on=panel["vampire_on"],
            blood_on=panel["blood_on"],
            roles_locked=locked,
        )
    except Exception as exc:
        get_logger().exception(
            "senior.build_kb.c={c}.e={e}",
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
            "session_senior.py:.send_senior_pan" +
            "el.texts.get.chat={}.exc={}",
            chat_id,
            exc,
        )
        title = "panel"
        body = ""
    try:
        msg_id = await bridge.send_text(
            senior_id,
            texts.get(
                "senior_panel_text",
                "fa",
                title,
                body,
                bundle="webapp",
            ),
            reply_markup=markup,
        )
    except Exception as exc:
        get_logger().exception(
            "session_senior.py:.send_senior_pan" +
            "el.send_text.chat={}.senior={}.exc" +
            "={}",
            chat_id,
            senior_id,
            exc,
        )
        return
    if not msg_id:
        return
    try:
        await redis.hset(
            flags,
            keys.field("senior_panel_sent"),
            str(senior_id),
        )
    except Exception as exc:
        get_logger().exception(
            "session_senior.py:.send_senior_pan" +
            "el.hset.sent.chat={}.senior={}.exc" +
            "={}",
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
            "senior.log_event.c={c}.s={s}.e={e}",
            chat_id,
            senior_id,
            exc,
        )


async def maybe_refresh_session_senior(
    chat_id: int,
    bridge: ChatBridge,
    texts: TextManager | None = None,
    keys: RedisKeySpace | None = None,
    lobby: LobbyManager | None = None,
    lang: str | None = None,
) -> int | None:
    """Recompute senior on lobby join updates; send panel once per game."""
    from app.managers.session_senior import (
        pick_session_senior,
        roles_locked,
    )

    keys = keys or RedisKeySpace()
    redis = await get_redis()
    try:
        locked = await roles_locked(
            chat_id, keys
        )
    except Exception as exc:
        get_logger().exception(
            "senior.maybe_refresh.r" +
            "oles_locked.c={c}.e={e}",
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
                "senior.mr.h" +
                "get.senior.c={c}.e={e}",
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
    try:
        prev = await redis.hget(
            keys.game_flags(chat_id),
            keys.field("senior_panel_sent"),
        )
    except Exception as exc:
        get_logger().exception(
            "senior.mr.h6.get_sent.c={c}.e={e}",
            chat_id,
            exc,
        )
        prev = None
    if prev:
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
            "senior.maybe_refresh.s" +
            "end_panel.c={c}.s={s}.e={e}",
            chat_id,
            senior,
            exc,
        )
    return senior
