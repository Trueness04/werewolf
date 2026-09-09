"""Message-tracking helpers (split of start_game.py)."""

from __future__ import annotations

import json

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from telegram import Update
from telegram.ext import ContextTypes


async def track_delete(
    chat_id: int, message_id: int
) -> None:
    """Append message id to deleteMessage list."""
    keys = RedisKeySpace()
    redis = await get_redis()
    key = keys.game_hash(chat_id)
    field = keys.field("delete_message")
    raw = await redis.hget(key, field)
    data = json.loads(raw) if raw else []
    if not isinstance(data, list):
        data = []
    data.append(message_id)
    await redis.hset(key, field, json.dumps(data))


async def track_edit(
    chat_id: int, message_id: int
) -> None:
    """Append message id to EditMarkup list."""
    keys = RedisKeySpace()
    redis = await get_redis()
    key = keys.game_hash(chat_id)
    field = keys.field("edit_markup")
    raw = await redis.hget(key, field)
    data = json.loads(raw) if raw else []
    if not isinstance(data, list):
        data = []
    data.append(message_id)
    await redis.hset(key, field, json.dumps(data))


async def remind_join(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    lang: str,
    challenge: bool,
) -> None:
    """Resend join button for existing lobby."""
    chat = update.effective_chat
    if chat is None:
        return
    from app.handlers import deps

    tm = deps.texts()
    url = await deps.join_url(chat.id)
    from app.keyboards.inline.lobby_keyboard import (
        build_join_keyboard,
    )
    keyboard = build_join_keyboard(
        tm,
        lang,
        url,
        challenge=challenge,
    )
    key_name = (
        "StartLastChallenge"
        if challenge
        else "startLastGame"
    )
    mid = await context.bot.send_message(
        chat_id=chat.id,
        text=tm.get(key_name, lang),
        reply_markup=keyboard,
    )
    await track_delete(chat.id, mid.message_id)


