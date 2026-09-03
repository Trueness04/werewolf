""" /nextgame and cancel_nextgame callback."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes
from app.handlers.callback_safe import (
    answer_safe,
)

from app.config.paths import CALLBACK_TEMPLATES
from app.filters import game_filters
from app.handlers import deps
from app.keyboards.inline.lobby_keyboard import (
    build_cancel_next_keyboard,
)
from app.managers.game_event import log_game_event
from app.managers.game_state_manager import (
    GameState,
    GroupInactive,
)
from app.managers.json_loader import load_json
from app.managers.next_game_manager import NextGameManager


async def next_game_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Queue user for next lobby while a game runs."""
    chat = update.effective_chat
    user = update.effective_user
    if chat is None or user is None:
        return
    if not await game_filters.is_group(update):
        return
    lang = deps.lang_of(update)
    tm = deps.texts()
    try:
        state = await deps.state_mgr().get_group_state(
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
    if state == GameState.JOINING:
        await context.bot.send_message(
            chat_id=chat.id,
            text=tm.get(
                "NextGameAlreadyJoin",
                lang,
                bundle="lobby",
            ),
        )
        return
    mgr = NextGameManager()
    await mgr.add(chat.id, user.id)
    tpl = load_json(CALLBACK_TEMPLATES)
    data = str(tpl["cancel_nextgame"]).format(
        chat_id=chat.id,
        user_id=user.id,
    )
    markup = build_cancel_next_keyboard(
        tm,
        lang,
        data,
    )
    await context.bot.send_message(
        chat_id=chat.id,
        text=tm.get(
            "NextGame",
            lang,
            bundle="lobby",
        ),
        reply_markup=markup,
    )
    log_game_event(
        "nextgame_add",
        chat_id=chat.id,
        user_id=user.id,
    )


async def cancel_next_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Remove user from next-game queue."""
    query = update.callback_query
    if query is None or query.data is None:
        return
    user = update.effective_user
    if user is None:
        return
    await answer_safe(query)
    tpl = load_json(CALLBACK_TEMPLATES)
    if not query.data.startswith(
        str(tpl["cancel_next_prefix"])
    ):
        return
    parts = query.data.split(":")
    if len(parts) < 3:
        return
    try:
        chat_id = int(parts[1])
        uid = int(parts[2])
    except ValueError:
        return
    if uid != user.id:
        return
    await NextGameManager().remove(chat_id, uid)
    lang = deps.lang_of(update)
    await query.edit_message_text(
        deps.texts().get(
            "NextGameCancelled",
            lang,
            bundle="lobby",
        )
    )


def cancel_next_pattern() -> str:
    """Pattern for cancel nextgame callbacks."""
    tpl = load_json(CALLBACK_TEMPLATES)
    return str(tpl["cancel_next_handler_pattern"])
