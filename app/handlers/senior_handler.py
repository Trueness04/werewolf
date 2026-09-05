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
from app.keyboards.inline.senior_keyboard import (
    build_senior_keyboard,
)
from app.keyboards.inline.lobby_keyboard import (
    build_join_keyboard,
)
from app.managers.end_game_manager import EndGameManager
from app.managers.game_event import log_game_event
from app.managers.game_state_manager import GameState
from app.managers.json_loader import load_json
from app.managers.lobby_extend import (
    apply_extend,
    format_hms,
)
from app.managers.session_senior import (
    is_session_senior,
    read_panel_flags,
    roles_locked,
)
from app.managers.timer_manager import TimerManager


async def senior_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle sr:chat:action:value from senior panel."""
    query = update.callback_query
    if query is None or query.data is None:
        return
    user = update.effective_user
    if user is None:
        return
    tpl = load_json(CALLBACK_TEMPLATES)
    if not query.data.startswith(
        str(tpl["senior_prefix"])
    ):
        return
    parts = query.data.split(":")
    if len(parts) < 4:
        return
    try:
        chat_id = int(parts[1])
    except ValueError:
        return
    action = parts[2]
    value = parts[3]
    lang = deps.lang_of(update)
    tm = deps.texts()
    keys = RedisKeySpace()
    if not await is_session_senior(
        chat_id,
        user.id,
        keys,
    ):
        await answer_safe(
            query,
            tm.get(
                "SessionSeniorNotYou",
                lang,
                bundle="lobby",
            ),
        )
        return
    await answer_safe(query)
    bridge = deps.bridge(context)
    redis = await get_redis()
    flags = keys.game_flags(chat_id)
    panel = await read_panel_flags(chat_id, keys)

    if action == "magic":
        await redis.hset(
            flags,
            keys.field("magic_allowed"),
            "0" if panel["magic_allowed"] else "1",
        )
    elif action == "mute":
        await redis.hset(
            flags,
            keys.field("mute_die"),
            "0" if panel["mute_die"] else "1",
        )
    elif action == "secret":
        await redis.hset(
            flags,
            keys.field("secret_vote"),
            "0" if panel["secret_vote"] else "1",
        )
    elif action in {"vamp", "blood"}:
        if await roles_locked(chat_id, keys):
            return
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
    elif action == "extend":
        await _do_extend(
            chat_id,
            user.id,
            lang,
            tm,
            bridge,
            query,
        )
        return
    elif action == "force":
        await _do_force(
            chat_id,
            user.id,
            lang,
            tm,
            bridge,
            query,
        )
        return
    elif action == "kill":
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
        return
    else:
        return

    log_game_event(
        "session_senior_toggle",
        chat_id=chat_id,
        user_id=user.id,
        action=action,
    )
    await _refresh_markup(
        query,
        chat_id,
        lang,
        tm,
        keys,
    )


async def _do_extend(
    chat_id: int,
    user_id: int,
    lang: str,
    tm: Any,
    bridge: Any,
    query: Any,
) -> None:
    state = await deps.state_mgr().get_group_state(chat_id)
    if state != GameState.JOINING:
        await answer_safe(
            query,
            tm.get(
                "SessionSeniorNotJoin",
                lang,
                bundle="lobby",
            ),
        )
        return
    cfg = deps.settings()
    left = await apply_extend(
        deps.lobby_mgr(),
        chat_id,
        cfg,
        60,
    )
    text = tm.get(
        "SessionSeniorExtended",
        lang,
        left,
        bundle="lobby",
    )
    await answer_safe(query, text)
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
    log_game_event(
        "session_senior_extend",
        chat_id=chat_id,
        user_id=user_id,
        left=left,
    )


async def _do_force(
    chat_id: int,
    user_id: int,
    lang: str,
    tm: Any,
    bridge: Any,
    query: Any,
) -> None:
    state = await deps.state_mgr().get_group_state(chat_id)
    if state != GameState.JOINING:
        await answer_safe(
            query,
            tm.get(
                "SessionSeniorNotJoin",
                lang,
                bundle="lobby",
            ),
        )
        return
    lobby = deps.lobby_mgr()
    keys = RedisKeySpace()
    redis = await get_redis()
    mode = await redis.hget(
        keys.game_hash(chat_id),
        keys.field("game_mode"),
    )
    await ensure_ai_lobby_fill(
        chat_id,
        str(mode or "Normal"),
        bridge=bridge,
        lobby=lobby,
        keys=keys,
        texts=tm,
    )
    await lobby.set_timer(chat_id, int(time()) - 1)
    await TimerManager(bridge).finish_join(chat_id, lang)
    await answer_safe(
        query,
        tm.get(
            "SessionSeniorForced",
            lang,
            bundle="lobby",
        ),
    )
    log_game_event(
        "session_senior_force",
        chat_id=chat_id,
        user_id=user_id,
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
    if value == "ask":
        markup = build_senior_keyboard(
            tm,
            lang,
            chat_id,
            magic_allowed=True,
            mute_die=False,
            secret_vote=False,
            vampire_on=True,
            blood_on=True,
            roles_locked=True,
            kill_confirm=True,
        )
        try:
            await query.edit_message_text(
                tm.get(
                    "SessionSeniorKillConfirm",
                    lang,
                    bundle="lobby",
                ),
                reply_markup=markup,
            )
        except Exception:
            pass
        return
    if value == "no":
        await _refresh_markup(
            query,
            chat_id,
            lang,
            tm,
            keys,
            restore_body=True,
        )
        return
    if value != "yes":
        return
    await EndGameManager(bridge).kill(
        chat_id,
        by_user_id=user_id,
    )
    text = tm.get(
        "SessionSeniorKilled",
        lang,
        bundle="lobby",
    )
    try:
        await query.edit_message_text(text)
    except Exception:
        await bridge.send_text(user_id, text)
    log_game_event(
        "session_senior_kill",
        chat_id=chat_id,
        user_id=user_id,
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
    panel = await read_panel_flags(chat_id, keys)
    locked = await roles_locked(chat_id, keys)
    markup = build_senior_keyboard(
        tm,
        lang,
        chat_id,
        magic_allowed=panel["magic_allowed"],
        mute_die=panel["mute_die"],
        secret_vote=panel["secret_vote"],
        vampire_on=panel["vampire_on"],
        blood_on=panel["blood_on"],
        roles_locked=locked,
    )
    try:
        if restore_body:
            title = tm.get(
                "SessionSeniorPanelTitle",
                lang,
                bundle="lobby",
            )
            body = tm.get(
                "SessionSeniorPanelBody",
                lang,
                bundle="lobby",
            )
            await query.edit_message_text(
                f"<b>{title}</b>\n\n{body}",
                reply_markup=markup,
                parse_mode="HTML",
            )
        else:
            await query.edit_message_reply_markup(
                reply_markup=markup,
            )
    except Exception:
        pass


def senior_callback_pattern() -> str:
    """Pattern for sr: callbacks."""
    tpl = load_json(CALLBACK_TEMPLATES)
    return str(tpl["senior_handler_pattern"])
