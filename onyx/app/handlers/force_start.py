"""Force start handler (PHP CM_ForceStart)."""

from __future__ import annotations

from time import time

from telegram import Update
from telegram.ext import ContextTypes

from AI.lobby_fill import ensure_ai_lobby_fill
from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.filters import game_filters
from app.handlers import deps
from app.managers.game_event import log_game_event
from app.managers.game_state_manager import (
    GameState,
    GroupInactive,
)
from app.managers.timer_manager import TimerManager


async def force_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Fill AI if needed, then end join immediately."""
    chat = update.effective_chat
    user = update.effective_user
    if chat is None or user is None:
        return
    lang = deps.lang_of(update)
    tm = deps.texts()
    if not await game_filters.is_admin(update, context):
        await context.bot.send_message(
            chat_id=chat.id,
            text=tm.get("NotAllowForUser", lang),
        )
        return
    state_manager = deps.state_mgr()
    try:
        state = await state_manager.get_group_state(
            chat.id,
        )
    except GroupInactive:
        return
    if state == GameState.NO_GAME:
        await context.bot.send_message(
            chat_id=chat.id,
            text=tm.get("GameNotCreate", lang),
        )
        return
    if state == GameState.RUNNING:
        return
    if state != GameState.JOINING:
        return
    lobby = deps.lobby_mgr()
    bridge = deps.bridge(context)
    keys = RedisKeySpace()
    redis = await get_redis()
    mode = await redis.hget(
        keys.game_hash(chat.id),
        keys.field("game_mode"),
    )
    await ensure_ai_lobby_fill(
        chat.id,
        str(mode or "Normal"),
        bridge=bridge,
        lobby=lobby,
        keys=keys,
        texts=tm,
    )
    await lobby.set_timer(chat.id, int(time()) - 1)
    await TimerManager(bridge).finish_join(
        chat.id,
        lang,
    )
    log_game_event(
        "force_start",
        chat_id=chat.id,
        user_id=user.id,
        phase="join",
    )
