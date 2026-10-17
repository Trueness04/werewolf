"""Admin /killgame — cancel current session."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.filters import game_filters
from app.handlers import deps
from app.managers.end_game_manager import EndGameManager
from app.managers.game_event import log_game_event
from app.managers.game_state_manager import (
    GameState,
    GroupInactive,
)


async def kill_game(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Kill join/running game when admin asks."""
    chat = update.effective_chat
    user = update.effective_user
    if chat is None or user is None:
        return
    lang = deps.lang_of(update)
    tm = deps.texts()
    if not await game_filters.is_group(update):
        return
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
    bridge = deps.bridge(context)
    await EndGameManager(bridge).kill(chat.id)
    log_game_event(
        "killgame_cmd",
        chat_id=chat.id,
        user_id=user.id,
    )
