"""Extend join timer (PHP CM_Extend)."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.filters import game_filters
from app.handlers import deps
from app.managers.game_event import log_game_event
from app.managers.game_state_manager import (
    GameState,
    GroupInactive,
)
from app.managers.lobby_extend import apply_extend


async def extend_join(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Add/subtract seconds on join timer."""
    chat = update.effective_chat
    user = update.effective_user
    if chat is None or user is None:
        return
    if not update.message:
        return
    lang = deps.lang_of(update)
    tm = deps.texts()
    cfg = deps.settings()
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
            text=tm.get("GameNotCreate", lang),
        )
        return
    if state != GameState.JOINING:
        return
    is_admin = await game_filters.is_admin(
        update,
        context,
    )
    if not group.allow_extend and not is_admin:
        await context.bot.send_message(
            chat_id=chat.id,
            text=tm.get("AllowExtendForAdmin", lang),
        )
        return
    delta = _parse_delta(
        update.message.text or "",
        cfg.extend_default_seconds,
    )
    if delta < 0 and not is_admin:
        await context.bot.send_message(
            chat_id=chat.id,
            text=tm.get("NotAllowUserminusExtend", lang),
        )
        return
    left = await apply_extend(
        deps.lobby_mgr(),
        chat.id,
        cfg,
        delta,
    )
    if left <= 0:
        return
    await context.bot.send_message(
        chat_id=chat.id,
        text=str(left),
    )
    log_game_event(
        "extend",
        chat_id=chat.id,
        user_id=user.id,
        delta=delta,
        left=left,
    )


def _parse_delta(text: str, default: int) -> int:
    """Extract integer seconds from command text."""
    parts = text.split()
    if len(parts) < 2:
        return default
    try:
        return int(parts[1])
    except ValueError:
        return default
