"""Players list command handler."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.handlers import deps
from app.managers.game_state_manager import GroupInactive
from app.managers.logger_manager import get_logger


async def players_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Send current Redis player list to group."""
    chat = update.effective_chat
    if chat is None:
        return
    lang = deps.lang_of(update)
    tm = deps.texts()
    state_manager = deps.state_mgr()
    try:
        await state_manager.ensure_group_active(chat.id)
    except GroupInactive as exc:
        get_logger().warning("silent_swallow.line=25.exc={}", exc)
        return
    group = await state_manager.ensure_group_active(
        chat.id,
    )
    if group is None:
        return
    lobby = deps.lobby_mgr()
    players = await lobby.list_players(chat.id)
    header = tm.get("playerList", lang)
    body = lobby.player_list_text(lang, players)
    await context.bot.send_message(
        chat_id=chat.id,
        text=tm.get(
            "players_list_body",
            lang,
            header,
            body,
            bundle="webapp",
        ),
        parse_mode="HTML",
    )
