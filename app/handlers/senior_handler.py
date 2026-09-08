"""Session senior «پنل کنترل بازی» callbacks (sr:)."""

from __future__ import annotations

from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import CALLBACK_TEMPLATES
from app.handlers import deps
from app.handlers.callback_safe import answer_safe
from app.handlers.senior_actions import (  # noqa: F401
    _do_extend,
    _do_force,
    _refresh_markup,
)
from app.handlers.senior_kill import (  # noqa: F401
    _do_kill,
)
from app.managers.game_event import log_game_event
from app.managers.json_loader import load_json
from app.managers.logger_manager import get_logger
from app.managers.session_senior import (
    is_session_senior,
)


async def senior_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle sr:chat:action:value from senior panel.

    Frozen panel: هر پنلی فقط ۱ بار در هر بازی نمایش
    داده میشه؛ کیبوردها ادیت/دیلیت نمیشن.
    Callbacks only answer() and toggle redis
    flags; panel message is never edited/deleted.
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
                "senior_handler.py:.senior_callback"
                + "load_json.exc={}",
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
                "senior.prefix_check.exc={}",
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
                "senior_handler.py:.senior_callback.bad"
                + "chat_id.data={}.exc={}",
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
                "senior_handler.py:.senior_callback.deps"
                + "chat={}.exc={}",
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
                "senior.cb_is_senior"
                ".c={c}.u={u}.e={e}",
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
                    "senior.cb.not_you.c={c}.u={u}",
                    + ".exc={}",
                    chat_id,
                    user.id,
                    exc,
                )
            return
        try:
            await answer_safe(query)
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py:.senior_callback"
                + ".a.c={c}.u={u}.e={e}",
                chat_id,
                user.id,
                exc,
            )
        try:
            bridge = deps.bridge(context)
        except Exception as exc:
            get_logger().exception(
                "senior.cb_bridge.redis.c={c}.e={e}",
                chat_id,
                exc,
            )
            return

        # Toggle actions — only redis flag + answer, no panel edit/delete
        if action in (
            "magic",
            "mute",
            "secret",
            "vamp",
            "blood",
        ):
            from app.handlers.senior_kill import (
                apply_toggle,
            )

            try:
                ok = await apply_toggle(
                    action,
                    chat_id,
                    lang,
                    tm,
                    keys,
                    query,
                )
            except Exception as exc:
                get_logger().exception(
                    "senior.cb_toggle.c={c}.a={a}.e={e}",
                    chat_id,
                    action,
                    exc,
                )
                return
            if ok:
                try:
                    log_game_event(
                        "session_senior_toggle",
                        chat_id=chat_id,
                        user_id=user.id,
                        action=action,
                    )
                except Exception as exc:
                    get_logger().exception(
                        "senior.cb6.log_toggle",
                        chat_id,
                        user.id,
                        action,
                        exc,
                    )
            return
        if action == "extend":
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
                    "senior_handler.py:.senior_callback"
                    + "extend.chat={}.user={}.exc={}",
                    chat_id,
                    user.id,
                    exc,
                )
            return
        if action == "force":
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
                    "senior_handler.py:.senior_callback.force"
                    + "chat={}.user={}.exc={}",
                    chat_id,
                    user.id,
                    exc,
                )
            return
        if action == "kill":
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
                    "senior_handler.py:.senior_callback.kill"
                    + "chat={}.user={}.value={}.exc={}",
                    chat_id,
                    user.id,
                    value,
                    exc,
                )
            return
    except Exception as exc:
        get_logger().exception(
            "senior_handler.py:.senior_callback.outer"
            + "chat.exc={}",
            exc,
        )


def senior_callback_pattern() -> str:
    """Pattern for sr: callbacks."""
    try:
        tpl = load_json(CALLBACK_TEMPLATES)
        return str(tpl["senior_handler_pattern"])
    except Exception as exc:
        get_logger().exception(
            "senior_handler.py:"
            + "senior_callback_pattern.exc={}",
            exc,
        )
        return r"^sr:"
