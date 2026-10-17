"""Sudo command — open admin WebApp for allowlisted users."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import ContextTypes

from app.config.settings import get_settings
from app.handlers import deps
from app.managers.sudo import is_sudo


async def sudo_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """PV-only entry to sudo management panel."""
    user = update.effective_user
    chat = update.effective_chat
    if user is None or chat is None:
        return
    lang = deps.lang_of(update)
    tm = deps.texts()
    if not is_sudo(user.id):
        await context.bot.send_message(
            chat_id=chat.id,
            text=tm.get(
                "SudoDenied",
                lang,
                bundle="lobby",
            ),
        )
        return
    settings = get_settings()
    url = (settings.webapp_url or "").rstrip("/")
    if not url:
        await context.bot.send_message(
            chat_id=chat.id,
            text=tm.get(
                "SudoNoWebappUrl",
                lang,
                bundle="lobby",
            ),
        )
        return
    admin_url = f"{url}/?view=admin"
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=tm.get(
                        "SudoOpenPanel",
                        lang,
                        bundle="lobby",
                    ),
                    web_app=WebAppInfo(url=admin_url),
                )
            ]
        ]
    )
    await context.bot.send_message(
        chat_id=chat.id,
        text=tm.get(
            "SudoPanelIntro",
            lang,
            bundle="lobby",
        ),
        reply_markup=kb,
    )
