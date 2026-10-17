"""Hero / achievement / online meta commands → webapp."""

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


async def myhero_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    await _open_meta(
        update,
        context,
        view="hero",
        key="HeroMovedToWebapp",
        btn_key="OpenHeroWebapp",
    )


async def achievement_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    await _open_meta(
        update,
        context,
        view="achievements",
        key="AchievementMovedToWebapp",
        btn_key="OpenAchievementsWebapp",
    )


async def onlinegame_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    await _open_meta(
        update,
        context,
        view="online",
        key="OnlineGameMovedToWebapp",
        btn_key="OpenOnlineWebapp",
    )


async def _open_meta(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    view: str,
    key: str,
    btn_key: str,
) -> None:
    chat = update.effective_chat
    if chat is None:
        return
    lang = deps.lang_of(update)
    tm = deps.texts()
    text = tm.get(key, lang, bundle="lobby")
    settings = get_settings()
    url = (settings.webapp_url or "").rstrip("/")
    kb = None
    if url:
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text=tm.get(
                            btn_key,
                            lang,
                            bundle="lobby",
                        ),
                        web_app=WebAppInfo(
                            url=f"{url}/?view={view}"
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
