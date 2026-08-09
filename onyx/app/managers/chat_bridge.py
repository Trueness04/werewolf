"""Telegram send/edit helpers for managers."""

from __future__ import annotations

from typing import Any

from telegram import InlineKeyboardMarkup
from telegram.ext import ExtBot


class ChatBridge:
    """Thin async wrapper around ExtBot calls."""

    def __init__(self, bot: ExtBot) -> None:
        self._bot = bot

    async def send_text(
        self,
        chat_id: int,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> int:
        """Send text; return message_id (0 on fail)."""
        try:
            msg = await self._bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
            return int(msg.message_id)
        except Exception:
            return 0

    async def send_animation(
        self,
        chat_id: int,
        animation: str,
        caption: str,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> int:
        """Send GIF/animation; return message_id."""
        msg = await self._bot.send_animation(
            chat_id=chat_id,
            animation=animation,
            caption=caption,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
        return int(msg.message_id)

    async def edit_text(
        self,
        chat_id: int,
        message_id: int,
        text: str,
    ) -> None:
        """Edit an existing text message."""
        await self._bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            parse_mode="HTML",
        )

    async def pin(
        self,
        chat_id: int,
        message_id: int,
    ) -> None:
        """Pin a message silently if possible."""
        await self._bot.pin_chat_message(
            chat_id=chat_id,
            message_id=message_id,
            disable_notification=True,
        )

    async def delete(
        self,
        chat_id: int,
        message_id: int,
    ) -> None:
        """Delete one message; ignore failures."""
        try:
            await self._bot.delete_message(
                chat_id=chat_id,
                message_id=message_id,
            )
        except Exception:
            return

    async def get_member_status(
        self,
        chat_id: int,
        user_id: int,
    ) -> str:
        """Return chat member status string."""
        member = await self._bot.get_chat_member(
            chat_id=chat_id,
            user_id=user_id,
        )
        return str(member.status)

    async def get_chat_title(self, chat_id: int) -> str:
        """Return chat title for PV confirmations."""
        chat = await self._bot.get_chat(chat_id)
        return str(chat.title or chat_id)

    async def mute_member(
        self,
        chat_id: int,
        user_id: int,
    ) -> None:
        """Mute member (can_send_messages=False)."""
        from telegram import ChatPermissions

        try:
            await self._bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(
                    can_send_messages=False,
                ),
            )
        except Exception:
            return

