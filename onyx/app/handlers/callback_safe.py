"""Always answer Telegram callback queries (MF-26)."""

from __future__ import annotations

from telegram import CallbackQuery


async def answer_safe(
    query: CallbackQuery | None,
    text: str | None = None,
) -> None:
    """Answer callback; ignore already-answered errors."""
    if query is None:
        return
    try:
        if text:
            await query.answer(text=text)
        else:
            await query.answer()
    except Exception:
        return
