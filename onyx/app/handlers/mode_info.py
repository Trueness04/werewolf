"""Mode info command (PHP CM_ModeInfo)."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.handlers import deps
from app.managers.game_state_manager import GroupInactive
from importlib import import_module

_get_mode = import_module("app.class.game_mode").get_mode


async def mode_info(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Explain current lobby/game mode."""
    chat = update.effective_chat
    if chat is None:
        return
    lang = deps.lang_of(update)
    tm = deps.texts()
    try:
        await deps.state_mgr().get_group_state(chat.id)
    except GroupInactive:
        return
    redis = await get_redis()
    keys = RedisKeySpace()
    mode = await redis.hget(
        keys.game_hash(chat.id),
        keys.field("game_mode"),
    )
    if not mode:
        await context.bot.send_message(
            chat_id=chat.id,
            text=tm.get("GameNotCreate", lang),
        )
        return
    try:
        info = _get_mode(str(mode))
    except KeyError:
        await context.bot.send_message(
            chat_id=chat.id,
            text=str(mode),
        )
        return
    text = tm.get(
        info.start_text_key,
        lang,
        "",
        bundle="lobby",
    )
    footer = tm.get(
        "StartGameFooter",
        lang,
        bundle="lobby",
    )
    await context.bot.send_message(
        chat_id=chat.id,
        text=f"{text}\n{footer}\n/{info.command}",
    )
