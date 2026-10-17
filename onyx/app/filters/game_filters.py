"""Telegram filters for lobby/game handlers."""

from __future__ import annotations

from telegram import Chat, Update
from telegram.ext import ContextTypes


async def is_group(update: Update) -> bool:
    """True when update comes from a group chat."""
    chat = update.effective_chat
    if chat is None:
        return False
    return chat.type in {
        Chat.GROUP,
        Chat.SUPERGROUP,
    }


async def is_private(update: Update) -> bool:
    """True when update is a private chat."""
    chat = update.effective_chat
    if chat is None:
        return False
    return chat.type == Chat.PRIVATE


async def is_admin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    """True when sender is group administrator."""
    chat = update.effective_chat
    user = update.effective_user
    if chat is None or user is None:
        return False
    member = await context.bot.get_chat_member(
        chat.id,
        user.id,
    )
    status = str(member.status)
    return status in {"creator", "administrator"}
