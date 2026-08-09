"""Flee from join lobby (PHP CM_Flee)."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.handlers import deps
from app.managers.game_event import log_game_event
from app.managers.game_state_manager import (
    GameState,
    GroupInactive,
)
from app.managers.lobby_extend import bump_if_late_join


async def flee_join(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Leave lobby during join when flee is allowed."""
    chat = update.effective_chat
    user = update.effective_user
    if chat is None or user is None:
        return
    lang = deps.lang_of(update)
    tm = deps.texts()
    state_manager = deps.state_mgr()
    try:
        state = await state_manager.get_group_state(
            chat.id,
        )
        group = await state_manager.ensure_group_active(
            chat.id,
        )
    except GroupInactive:
        return
    if group is None:
        return
    if state == GameState.NO_GAME:
        await context.bot.send_message(
            chat_id=chat.id,
            text=tm.get(
                "NotInGameForFlee",
                lang,
                bundle="lobby",
            ),
        )
        return
    if state != GameState.JOINING:
        await context.bot.send_message(
            chat_id=chat.id,
            text=tm.get(
                "NotAllowFleeInGame",
                lang,
                bundle="lobby",
            ),
        )
        return
    if not bool(getattr(group, "allow_flee", True)):
        await context.bot.send_message(
            chat_id=chat.id,
            text=tm.get(
                "NotAllowFlee",
                lang,
                bundle="lobby",
            ),
        )
        return
    lobby = deps.lobby_mgr()
    removed = await lobby.unregister_player(
        chat.id,
        user.id,
    )
    if not removed:
        await context.bot.send_message(
            chat_id=chat.id,
            text=tm.get(
                "NotInGameForFlee",
                lang,
                bundle="lobby",
            ),
        )
        return
    await bump_if_late_join(
        lobby,
        chat.id,
        deps.settings(),
    )
    count = await lobby.count_players(chat.id)
    await context.bot.send_message(
        chat_id=chat.id,
        text=tm.get(
            "okFlee",
            lang,
            user.full_name,
            bundle="lobby",
        ),
    )
    await context.bot.send_message(
        chat_id=chat.id,
        text=tm.get(
            "FleeCoutPlayer",
            lang,
            count,
            bundle="lobby",
        ),
    )
    log_game_event(
        "flee",
        chat_id=chat.id,
        user_id=user.id,
        left=count,
    )
