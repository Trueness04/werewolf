"""Ack inline selections by editing the callback msg."""

from __future__ import annotations

from telegram import CallbackQuery
from app.managers.logger_manager import get_logger


async def ack_selection(
    query: CallbackQuery,
    text: str,
) -> None:
    """Replace callback message with ack; drop buttons."""
    try:
        await query.edit_message_text(
            text=text,
            parse_mode="HTML",
        )
        return
    except Exception as exc:
        get_logger().warning("silent_swallow.line=19.exc={}", exc)
        pass
    try:
        await query.edit_message_reply_markup(
            reply_markup=None,
        )
    except Exception as exc:
        get_logger().warning("silent_swallow.line=25.exc={}", exc)
        return
