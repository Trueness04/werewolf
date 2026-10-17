"""Ack inline selections by editing the callback msg."""

from __future__ import annotations

from telegram import CallbackQuery


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
    except Exception:
        pass
    try:
        await query.edit_message_reply_markup(
            reply_markup=None,
        )
    except Exception:
        return
