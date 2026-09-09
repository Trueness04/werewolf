"""Member/chat-info helpers mixin for ChatBridge."""

from __future__ import annotations

import asyncio
from app.managers.logger_manager import get_logger


class ChatBridgeMembers:
    """Mixin: delete + member/chat queries (uses self._bot/_log)."""

    async def delete(self, chat_id: int, message_id: int) -> None:
        """Delete one message; ignore failures."""
        try:
            await self._bot.delete_message(
                chat_id=chat_id,
                message_id=message_id,
            )
        except Exception as exc:
            get_logger().warning("silent_swallow.line=18.exc={}", exc)
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

    async def mute_member(self, chat_id: int, user_id: int) -> None:
        """Mute member (can_send_messages=False)."""
        try:
            from telegram import ChatPermissions

            await self._bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=ChatPermissions(
                    can_send_messages=False,
                ),
            )
        except Exception as exc:
            get_logger().warning("silent_swallow.line=50.exc={}", exc)
            return
