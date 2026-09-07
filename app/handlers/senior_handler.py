"""Session senior «پنل کنترل بازی» callbacks (sr:)."""

from __future__ import annotations

from time import time
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from AI.lobby_fill import ensure_ai_lobby_fill
from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import CALLBACK_TEMPLATES
from app.handlers import deps
from app.handlers.callback_safe import answer_safe
from app.managers.end_game_manager import EndGameManager
from app.managers.game_event import log_game_event
from app.managers.game_state_manager import GameState
from app.managers.json_loader import load_json
from app.managers.lobby_extend import (
    apply_extend,
    format_hms,
)
from app.keyboards.inline.lobby_keyboard import (
    build_join_keyboard,
)
from app.managers.logger_manager import get_logger
from app.managers.session_senior import (
    is_session_senior,
)


async def senior_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle sr:chat:action:value from senior panel.

    Frozen panel: هر پنلی فقط ۱ بار در هر بازی نمایش داده میشه؛ کیبوردها ادیت/دیلیت نمیشن.
    Callbacks only answer() and toggle redis flags; panel message is never edited/deleted.
    """
    try:
        query = update.callback_query
        if query is None or query.data is None:
            return
        user = update.effective_user
        if user is None:
            return
        try:
            tpl = load_json(CALLBACK_TEMPLATES)
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py: senior_callback load_json exc={}",
                exc,
            )
            return
        try:
            if not query.data.startswith(
                str(tpl["senior_prefix"])
            ):
                return
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py: senior_callback prefix check exc={}",
                exc,
            )
            return
        parts = query.data.split(":")
        if len(parts) < 4:
            return
        try:
            chat_id = int(parts[1])
        except (ValueError, TypeError) as exc:
            get_logger().exception(
                "senior_handler.py: senior_callback bad chat_id data={} exc={}",
                query.data,
                exc,
            )
            return
        action = parts[2]
        value = parts[3]
        try:
            lang = deps.lang_of(update)
            tm = deps.texts()
            keys = RedisKeySpace()
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py: senior_callback deps chat={} exc={}",
                chat_id,
                exc,
            )
            return
        try:
            is_senior = await is_session_senior(
                chat_id,
                user.id,
                keys,
            )
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py: senior_callback is_session_senior chat={} user={} exc={}",
                chat_id,
                user.id,
                exc,
            )
            return
        if not is_senior:
            try:
                await answer_safe(
                    query,
                    tm.get(
                        "SessionSeniorNotYou",
                        lang,
                        bundle="lobby",
                    ),
                )
            except Exception as exc:
                get_logger().exception(
                    "senior_handler.py: senior_callback answer not-you chat={} user={} exc={}",
                    chat_id,
                    user.id,
                    exc,
                )
            return
        try:
            await answer_safe(query)
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py: senior_callback answer chat={} user={} exc={}",
                chat_id,
                user.id,
                exc,
            )
        try:
            bridge = deps.bridge(context)
            redis = await get_redis()
            flags = keys.game_flags(chat_id)
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py: senior_callback bridge/redis chat={} exc={}",
                chat_id,
                exc,
            )
            return

        # Toggle actions — only redis flag + answer, no panel edit/delete
        if action == "magic":
            try:
                from app.managers.session_senior import read_panel_flags

                panel = await read_panel_flags(chat_id, keys)
                await redis.hset(
                    flags,
                    keys.field("magic_allowed"),
                    "0" if panel["magic_allowed"] else "1",
                )
            except Exception as exc:
                get_logger().exception(
                    "senior_handler.py: senior_callback magic chat={} exc={}",
                    chat_id,
                    exc,
                )
                return
        elif action == "mute":
            try:
                from app.managers.session_senior import read_panel_flags

                panel = await read_panel_flags(chat_id, keys)
                await redis.hset(
                    flags,
                    keys.field("mute_die"),
                    "0" if panel["mute_die"] else "1",
                )
            except Exception as exc:
                get_logger().exception(
                    "senior_handler.py: senior_callback mute chat={} exc={}",
                    chat_id,
                    exc,
                )
                return
        elif action == "secret":
            try:
                from app.managers.session_senior import read_panel_flags

                panel = await read_panel_flags(chat_id, keys)
                await redis.hset(
                    flags,
                    keys.field("secret_vote"),
                    "0" if panel["secret_vote"] else "1",
                )
            except Exception as exc:
                get_logger().exception(
                    "senior_handler.py: senior_callback secret chat={} exc={}",
                    chat_id,
                    exc,
                )
                return
        elif action in {"vamp", "blood"}:
            try:
                from app.managers.session_senior import (
                    read_panel_flags,
                    roles_locked,
                )

                if await roles_locked(chat_id, keys):
                    try:
                        await answer_safe(
                            query,
                            tm.get(
                                "SessionSeniorLocked",
                                lang,
                                bundle="lobby",
                            ),
                        )
                    except Exception as exc:
                        get_logger().exception(
                            "senior_handler.py: senior_callback locked answer chat={} exc={}",
                            chat_id,
                            exc,
                        )
                    return
                panel = await read_panel_flags(chat_id, keys)
                field = (
                    "vampire_role_on"
                    if action == "vamp"
                    else "bloodthirsty_role_on"
                )
                cur = (
                    panel["vampire_on"]
                    if action == "vamp"
                    else panel["blood_on"]
                )
                await redis.hset(
                    flags,
                    keys.field(field),
                    "0" if cur else "1",
                )
            except Exception as exc:
                get_logger().exception(
                    "senior_handler.py: senior_callback vamp/blood chat={} action={} exc={}",
                    chat_id,
                    action,
                    exc,
                )
                return
        elif action == "extend":
            try:
                await _do_extend(
                    chat_id,
                    user.id,
                    lang,
                    tm,
                    bridge,
                    query,
                )
            except Exception as exc:
                get_logger().exception(
                    "senior_handler.py: senior_callback extend chat={} user={} exc={}",
                    chat_id,
                    user.id,
                    exc,
                )
            return
        elif action == "force":
            try:
                await _do_force(
                    chat_id,
                    user.id,
                    lang,
                    tm,
                    bridge,
                    query,
                )
            except Exception as exc:
                get_logger().exception(
                    "senior_handler.py: senior_callback force chat={} user={} exc={}",
                    chat_id,
                    user.id,
                    exc,
                )
            return
        elif action == "kill":
            try:
                await _do_kill(
                    chat_id,
                    user.id,
                    value,
                    lang,
                    tm,
                    bridge,
                    keys,
                    query,
                )
            except Exception as exc:
                get_logger().exception(
                    "senior_handler.py: senior_callback kill chat={} user={} value={} exc={}",
                    chat_id,
                    user.id,
                    value,
                    exc,
                )
            return
        else:
            return

        try:
            log_game_event(
                "session_senior_toggle",
                chat_id=chat_id,
                user_id=user.id,
                action=action,
            )
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py: senior_callback log toggle chat={} user={} action={} exc={}",
                chat_id,
                user.id,
                action,
                exc,
            )
        # Frozen panel: do not edit keyboard/message
        try:
            await answer_safe(query)
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py: senior_callback final answer chat={} exc={}",
                chat_id,
                exc,
            )
    except Exception as exc:
        get_logger().exception(
            "senior_handler.py: senior_callback outer chat exc={}",
            exc,
        )


async def _do_extend(
    chat_id: int,
    user_id: int,
    lang: str,
    tm: Any,
    bridge: Any,
    query: Any,
) -> None:
    try:
        state = await deps.state_mgr().get_group_state(chat_id)
        if state != GameState.JOINING:
            try:
                await answer_safe(
                    query,
                    tm.get(
                        "SessionSeniorNotJoin",
                        lang,
                        bundle="lobby",
                    ),
                )
            except Exception as exc:
                get_logger().exception(
                    "senior_handler.py: _do_extend not-join answer chat={} exc={}",
                    chat_id,
                    exc,
                )
            return
        cfg = deps.settings()
        try:
            left = await apply_extend(
                deps.lobby_mgr(),
                chat_id,
                cfg,
                60,
            )
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py: _do_extend apply_extend chat={} exc={}",
                chat_id,
                exc,
            )
            return
        try:
            text = tm.get(
                "SessionSeniorExtended",
                lang,
                left,
                bundle="lobby",
            )
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py: _do_extend texts chat={} exc={}",
                chat_id,
                exc,
            )
            text = str(left)
        try:
            await answer_safe(query, text)
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py: _do_extend answer chat={} exc={}",
                chat_id,
                exc,
            )
        try:
            url = deps.join_url(chat_id)
            keyboard = build_join_keyboard(tm, lang, url)
            await bridge.send_text(
                chat_id,
                tm.get(
                    "ExtendConfirm",
                    lang,
                    format_hms(left),
                    bundle="lobby",
                ),
                reply_markup=keyboard,
            )
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py: _do_extend send_text chat={} exc={}",
                chat_id,
                exc,
            )
        try:
            log_game_event(
                "session_senior_extend",
                chat_id=chat_id,
                user_id=user_id,
                left=left,
            )
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py: _do_extend log chat={} exc={}",
                chat_id,
                exc,
            )
    except Exception as exc:
        get_logger().exception(
            "senior_handler.py: _do_extend outer chat={} user={} exc={}",
            chat_id,
            user_id,
            exc,
        )


async def _do_force(
    chat_id: int,
    user_id: int,
    lang: str,
    tm: Any,
    bridge: Any,
    query: Any,
) -> None:
    try:
        state = await deps.state_mgr().get_group_state(chat_id)
        if state != GameState.JOINING:
            try:
                await answer_safe(
                    query,
                    tm.get(
                        "SessionSeniorNotJoin",
                        lang,
                        bundle="lobby",
                    ),
                )
            except Exception as exc:
                get_logger().exception(
                    "senior_handler.py: _do_force not-join answer chat={} exc={}",
                    chat_id,
                    exc,
                )
            return
        lobby = deps.lobby_mgr()
        keys = RedisKeySpace()
        try:
            redis = await get_redis()
            mode = await redis.hget(
                keys.game_hash(chat_id),
                keys.field("game_mode"),
            )
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py: _do_force hget mode chat={} exc={}",
                chat_id,
                exc,
            )
            mode = None
        try:
            await ensure_ai_lobby_fill(
                chat_id,
                str(mode or "Normal"),
                bridge=bridge,
                lobby=lobby,
                keys=keys,
                texts=tm,
            )
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py: _do_force ai fill chat={} exc={}",
                chat_id,
                exc,
            )
        try:
            await lobby.set_timer(chat_id, int(time()) - 1)
            await TimerManager(bridge).finish_join(chat_id, lang)
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py: _do_force finish_join chat={} exc={}",
                chat_id,
                exc,
            )
        try:
            await answer_safe(
                query,
                tm.get(
                    "SessionSeniorForced",
                    lang,
                    bundle="lobby",
                ),
            )
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py: _do_force answer chat={} exc={}",
                chat_id,
                exc,
            )
        try:
            log_game_event(
                "session_senior_force",
                chat_id=chat_id,
                user_id=user_id,
            )
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py: _do_force log chat={} exc={}",
                chat_id,
                exc,
            )
    except Exception as exc:
        get_logger().exception(
            "senior_handler.py: _do_force outer chat={} user={} exc={}",
            chat_id,
            user_id,
            exc,
        )


async def _do_kill(
    chat_id: int,
    user_id: int,
    value: str,
    lang: str,
    tm: Any,
    bridge: Any,
    keys: RedisKeySpace,
    query: Any,
) -> None:
    try:
        if value == "ask":
            # Frozen panel: do not edit message — just answer with confirm text
            try:
                text = tm.get(
                    "SessionSeniorKillConfirm",
                    lang,
                    bundle="lobby",
                )
                await answer_safe(query, text)
            except Exception as exc:
                get_logger().exception(
                    "senior_handler.py: _do_kill ask answer chat={} exc={}",
                    chat_id,
                    exc,
                )
            return
        if value == "no":
            # Frozen panel: just acknowledge, do not restore/edit markup
            try:
                await answer_safe(query)
            except Exception as exc:
                get_logger().exception(
                    "senior_handler.py: _do_kill no answer chat={} exc={}",
                    chat_id,
                    exc,
                )
            return
        if value != "yes":
            return
        try:
            await EndGameManager(bridge).kill(
                chat_id,
                by_user_id=user_id,
            )
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py: _do_kill kill chat={} user={} exc={}",
                chat_id,
                user_id,
                exc,
            )
            return
        try:
            text = tm.get(
                "SessionSeniorKilled",
                lang,
                bundle="lobby",
            )
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py: _do_kill texts chat={} exc={}",
                chat_id,
                exc,
            )
            text = "killed"
        # Frozen panel: do not edit/delete panel message — answer + optional DM
        try:
            await answer_safe(query, text)
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py: _do_kill answer killed chat={} exc={}",
                chat_id,
                exc,
            )
        try:
            # also DM the senior as fallback visibility without editing panel
            await bridge.send_text(user_id, text)
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py: _do_kill send_text killed chat={} exc={}",
                chat_id,
                exc,
            )
        try:
            log_game_event(
                "session_senior_kill",
                chat_id=chat_id,
                user_id=user_id,
            )
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py: _do_kill log chat={} exc={}",
                chat_id,
                exc,
            )
    except Exception as exc:
        get_logger().exception(
            "senior_handler.py: _do_kill outer chat={} user={} value={} exc={}",
            chat_id,
            user_id,
            value,
            exc,
        )


async def _refresh_markup(
    query: Any,
    chat_id: int,
    lang: str,
    tm: Any,
    keys: RedisKeySpace,
    *,
    restore_body: bool = False,
) -> None:
    """Frozen — panel is never edited/deleted. No-op with log."""
    try:
        get_logger().debug(
            "senior_handler.py: _refresh_markup frozen no-op chat={} restore={}",
            chat_id,
            restore_body,
        )
    except Exception as exc:
        get_logger().exception(
            "senior_handler.py: _refresh_markup log chat={} exc={}",
            chat_id,
            exc,
        )
    return


def senior_callback_pattern() -> str:
    """Pattern for sr: callbacks."""
    try:
        tpl = load_json(CALLBACK_TEMPLATES)
        return str(tpl["senior_handler_pattern"])
    except Exception as exc:
        get_logger().exception(
            "senior_handler.py: senior_callback_pattern exc={}",
            exc,
        )
        return r"^sr:"
