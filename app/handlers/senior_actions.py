"""Action helpers for the senior panel."""

from __future__ import annotations

from time import time
from typing import Any

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.handlers import deps
from app.handlers.callback_safe import answer_safe
from app.managers.game_event import log_game_event
from app.managers.game_state_manager import GameState
from app.managers.json_loader import load_json
from app.managers.lobby_extend import apply_extend, format_hms
from app.keyboards.inline.lobby_keyboard import build_join_keyboard
from app.managers.logger_manager import get_logger


async def _do_extend(
    chat_id: int,
    user_id: int,
    lang: str,
    tm: Any,
    bridge: Any,
    query: Any,
) -> None:
    """Extend the lobby timer by 60s from the senior panel."""
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
                    "senior.do_extend.not" +
                    "join.answer.c={c}.e={e}",
                    chat_id,
                    exc,
                )
            return
        try:
            cfg = deps.settings()
            left = await apply_extend(
                deps.lobby_mgr(),
                chat_id,
                cfg,
                60,
            )
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py:._do_extend.appl"
                "y_extend",
                + ".c={c}.e={e}",
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
                "senior.do_extend.text" +
                "s.c={c}.e={e}",
                chat_id,
                exc,
            )
            text = str(left)
        try:
            await answer_safe(query, text)
        except Exception as exc:
            get_logger().exception(
                "senior_handler.py:._do_extend.answ" +
                "er.chat={}.exc={}",
                chat_id,
                exc,
            )
        try:
            url = await deps.join_url(chat_id)
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
                "senior_handler.py:._do_extend.send"
                "_text",
                + "chat={}.exc={}",
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
                "senior_handler.py:._do_extend.log" +
                "chat={}.exc={}",
                chat_id,
                exc,
            )
    except Exception as exc:
        get_logger().exception(
            "senior.do_extend_outer.u={u}.e={e}",
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
    """Force-start the game from the senior panel."""
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
                    "senior.do_force.notjoin.c={c}.e={e}",
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
                "senior.do_force.hget.mode.c={c}.e={e}",
                chat_id,
                exc,
            )
            mode = None
        try:
            from app.integrations.ai_gate import ai_callable

            await ai_callable(
                "AI.lobby_fill",
                "ensure_ai_lobby_fill",
                "senior_actions:_do_force",
            )(
                chat_id,
                str(mode) if mode else "Normal",
                bridge=bridge,
                lobby=lobby,
                keys=keys,
                texts=tm,
            )
        except Exception as exc:
            get_logger().exception(
                "senior.do_force.ai_fill" +
                "ll.c={c}.e={e}",
                chat_id,
                exc,
            )
        try:
            await lobby.set_timer(
                chat_id,
                int(time()) - 1,
            )
            from app.managers.timer_manager import TimerManager

            await TimerManager(bridge).finish_join(chat_id, lang)
        except Exception as exc:
            get_logger().exception(
                "senior.do_force_finish_join",
                ".c={c}.e={e}",
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
                "senior.do_force.answer.c={c}.e={e}",
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
                "senior.do_force.log_c" +
                "hat={h}.e={e}",
                chat_id,
                exc,
            )
    except Exception as exc:
        get_logger().exception(
            "senior.do_force.outer"
            ".c={c}.u={u}.e={e}",
            chat_id,
            user_id,
            exc,
        )


async def _refresh_markup(
    query: Any = None,
    chat_id: int | None = None,
    lang: str | None = None,
    tm: Any = None,
    keys: RedisKeySpace | None = None,
    *,
    restore_body: bool = False,
) -> None:
    """Frozen — panel is never edited/deleted. No-op with log."""
    try:
        get_logger().debug(
            "senior_handler.py:._refresh_markup" +
            "frozen",
            + "no-op.chat={}.restore={}",
            chat_id,
            restore_body,
        )
    except Exception as exc:
        get_logger().exception(
            "senior.refresh_markup" +
            ".log.c={c}.e={e}",
            chat_id,
            exc,
        )
