"""Challenge commands redirect to webapp (PN-06)."""

from __future__ import annotations

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    WebAppInfo,
)
from telegram.ext import ContextTypes

from app.config.settings import get_settings
from app.handlers import deps


async def start_challenge(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Challenge lives on webapp only (§7.0)."""
    await _redirect(update, context)


async def challenge_force(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Force-challenge → same webapp challenge surface."""
    await _redirect(update, context)


async def _redirect(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    chat = update.effective_chat
    if chat is None:
        return
    lang = deps.lang_of(update)
    tm = deps.texts()
    text = tm.get(
        "ChallengeMovedToWebapp",
        lang,
        bundle="lobby",
    )
    settings = get_settings()
    url = (settings.webapp_url or "").rstrip("/")
    kb = None
    if url:
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text=tm.get(
                            "OpenChallengeWebapp",
                            lang,
                            bundle="lobby",
                        ),
                        web_app=WebAppInfo(
                            url=f"{url}/?view=challenge"
                        ),
                    )
                ]
            ]
        )
    await context.bot.send_message(
        chat_id=chat.id,
        text=text,
        reply_markup=kb,
    )
