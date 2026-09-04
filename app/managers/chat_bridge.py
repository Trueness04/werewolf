"""Telegram send/edit helpers for managers."""

from __future__ import annotations

import asyncio
from typing import Any

import telegram
from telegram import InlineKeyboardMarkup
from telegram.ext import ExtBot

from app.managers.logger_manager import get_logger


class ChatBridge:
    """Thin async wrapper around ExtBot calls."""

    _ai_base: int | None = None
    _last_edit: dict[tuple[int, int], str] = {}

    def __init__(self, bot: ExtBot) -> None:
        self._bot = bot
        self._log = get_logger()

    def _ai_id_base(self) -> int | None:
        """AI seat id base; None when unknown."""
        if self._ai_base is None:
            try:
                from AI.registry import AgentRegistry
                cfg = AgentRegistry().config
                self._ai_base = int(cfg["id_base"])
            except Exception:
                self._ai_base = 0
        if self._ai_base == 0:
            return None
        return self._ai_base

    def _is_ai_target(self, chat_id: int) -> bool:
        """True for AI player seat ids (skip DM)."""
        base = self._ai_id_base()
        if base is None:
            return False
        return base - 2000 <= chat_id < base

    # -- send helpers ---------------------------------------------------

    async def send_text(
        self,
        chat_id: int,
        text: str,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> int:
        """Send text; return message_id (0 on fail).

        Handles RetryAfter by sleeping and retrying once.
        """
        if self._is_ai_target(chat_id):
            self._log.warning(
                "skip_ai_dm chat={}", chat_id,
            )
            return 0
        for attempt in range(2):
            try:
                msg = await self._bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode="HTML",
                )
                return int(msg.message_id)
            except telegram.error.RetryAfter as exc:
                if attempt == 0:
                    self._log.warning(
                        "rate_limited chat={} retry_after={}",
                        chat_id,
                        exc.retry_after,
                    )
                    await asyncio.sleep(exc.retry_after)
                    continue
                self._log.warning(
                    "rate_limited_giveup chat={}", chat_id,
                )
                return 0
            except telegram.error.BadRequest as exc:
                preview = " ".join(text.split())[:120]
                self._log.warning(
                    "send_failed chat={} err={} text={!r}",
                    chat_id,
                    exc,
                    preview,
                )
                return 0
            except telegram.error.TimedOut as exc:
                preview = " ".join(text.split())[:120]
                self._log.warning(
                    "send_timed_out c={} a={} t={!r}",
                    chat_id,
                    attempt,
                    preview,
                )
                if attempt == 0:
                    await asyncio.sleep(1)
                    continue
                return 0
            except Exception as exc:
                preview = " ".join(text.split())[:120]
                self._log.exception(
                    "send_failed chat={} err={} text={!r}",
                    chat_id,
                    exc,
                    preview,
                )
                return 0
        return 0

    async def send_animation(
        self,
        chat_id: int,
        animation: str,
        caption: str,
        reply_markup: InlineKeyboardMarkup | None = None,
    ) -> int:
        """Send GIF/animation; return message_id (0 on fail)."""
        if self._is_ai_target(chat_id):
            self._log.warning(
                "skip_ai_anim chat={}", chat_id,
            )
            return 0
        for attempt in range(2):
            try:
                msg = await self._bot.send_animation(
                    chat_id=chat_id,
                    animation=animation,
                    caption=caption,
                    reply_markup=reply_markup,
                    parse_mode="HTML",
                )
                return int(msg.message_id)
            except telegram.error.RetryAfter as exc:
                if attempt == 0:
                    self._log.warning(
                        "anim_rate_limited chat={} retry_after={}",
                        chat_id,
                        exc.retry_after,
                    )
                    await asyncio.sleep(exc.retry_after)
                    continue
                self._log.warning(
                    "anim_rate_limited_giveup chat={}", chat_id,
                )
                return 0
            except Exception as exc:
                self._log.exception(
                    "anim_send_failed chat={} err={}",
                    chat_id,
                    exc,
                )
                return 0
        return 0

    async def send_rich(
        self,
        chat_id: int,
        markdown: str,
    ) -> bool:
        """Send Rich Message (Bot API sendRichMessage).

        Returns False when unsupported or failed; caller falls back.
        """
        if self._is_ai_target(chat_id):
            self._log.warning(
                "skip_ai_rich chat={}", chat_id,
            )
            return False
        for attempt in range(2):
            try:
                await self._bot._post(
                    "sendRichMessage",
                    data={
                        "chat_id": chat_id,
                        "rich_message": {
                            "markdown": markdown,
                        },
                    },
                )
                return True
            except telegram.error.RetryAfter as exc:
                if attempt == 0:
                    await asyncio.sleep(exc.retry_after)
                    continue
                self._log.warning(
                    "rich_rate_limited_giveup chat={}",
                    chat_id,
                )
                return False
            except Exception as exc:
                head = markdown.splitlines()[0][:80] if markdown else ""
                self._log.warning(
                    "rich_failed chat={} err={} head={!r}",
                    chat_id,
                    exc,
                    head,
                )
                return False
        return False

    async def edit_text(
        self,
        chat_id: int,
        message_id: int,
        text: str,
    ) -> None:
        """Edit an existing text message (skip identical edits)."""
        key = (chat_id, message_id)
        if self._last_edit.get(key) == text:
            return
        if len(self._last_edit) > 500:
            self._last_edit.clear()
        for attempt in range(2):
            try:
                await self._bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    parse_mode="HTML",
                )
                self._last_edit[key] = text
                return
            except telegram.error.RetryAfter as exc:
                if attempt == 0:
                    self._log.warning(
                        "edit_rl c={} m={} r={}",
                        chat_id,
                        message_id,
                        exc.retry_after,
                    )
                    await asyncio.sleep(exc.retry_after)
                    continue
                self._log.warning(
                    "edit_rate_limited_giveup chat={} msg={}",
                    chat_id,
                    message_id,
                )
                return
            except telegram.error.BadRequest as exc:
                if "Message is not modified" in str(exc):
                    self._last_edit[key] = text
                    return
                self._log.warning(
                    "edit_failed chat={} msg={} err={}",
                    chat_id,
                    message_id,
                    exc,
                )
                return
            except Exception as exc:
                self._log.exception(
                    "edit_failed chat={} msg={} err={}",
                    chat_id,
                    message_id,
                    exc,
                )
                return

    async def pin(
        self,
        chat_id: int,
        message_id: int,
    ) -> None:
        """Pin a message silently if possible (safe)."""
        try:
            await self._bot.pin_chat_message(
                chat_id=chat_id,
                message_id=message_id,
                disable_notification=True,
            )
        except Exception as exc:
            self._log.warning(
                "pin_failed chat={} msg={} err={}",
                chat_id,
                message_id,
                exc,
            )

    # -- delete / member helpers ----------------------------------------

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

