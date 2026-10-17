"""Lucifer dodge day/vote callback handlers."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes
from app.handlers.callback_safe import (
    answer_safe,
)

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import CALLBACK_TEMPLATES
from app.handlers import deps
from app.handlers.callback_ack import ack_selection
from app.managers.json_loader import load_json
from app.managers.vote_manager import VoteManager


async def dodge_day_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Store day action as victim; clicked by lucifer."""
    query = update.callback_query
    if query is None or query.data is None:
        return
    user = update.effective_user
    if user is None:
        return
    await answer_safe(query)
    tpl = load_json(CALLBACK_TEMPLATES)
    if not query.data.startswith(
        str(tpl["dodge_day_prefix"])
    ):
        return
    parts = query.data.split(":")
    if len(parts) < 5:
        return
    try:
        chat_id = int(parts[1])
        lucifer = int(parts[2])
        victim = int(parts[3])
        target = int(parts[4])
    except ValueError:
        return
    if lucifer != user.id:
        return
    keys = RedisKeySpace()
    redis = await get_redis()
    owner = await redis.hget(
        keys.game_flags(chat_id),
        keys.field(f"dodge_day:{victim}"),
    )
    if not owner or int(owner) != lucifer:
        return
    await redis.hset(
        keys.day_actions(chat_id),
        str(victim),
        str(target),
    )
    await redis.hdel(
        keys.game_flags(chat_id),
        keys.field(f"dodge_day:{victim}"),
    )
    lang = deps.lang_of(update)
    await ack_selection(
        query,
        deps.texts().get(
            "SelectOk",
            lang,
            bundle="day",
        ),
    )


async def dodge_vote_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Cast vote as victim; clicked by lucifer."""
    query = update.callback_query
    if query is None or query.data is None:
        return
    user = update.effective_user
    if user is None:
        return
    await answer_safe(query)
    tpl = load_json(CALLBACK_TEMPLATES)
    if not query.data.startswith(
        str(tpl["dodge_vote_prefix"])
    ):
        return
    parts = query.data.split(":")
    if len(parts) < 5:
        return
    try:
        chat_id = int(parts[1])
        lucifer = int(parts[2])
        victim = int(parts[3])
        target = int(parts[4])
    except ValueError:
        return
    if lucifer != user.id:
        return
    keys = RedisKeySpace()
    redis = await get_redis()
    owner = await redis.hget(
        keys.game_flags(chat_id),
        keys.field(f"dodge_vote:{victim}"),
    )
    if not owner or int(owner) != lucifer:
        return
    bridge = deps.bridge(context)
    ok = await VoteManager(bridge).cast_vote(
        chat_id,
        victim,
        target,
    )
    if not ok:
        return
    await redis.hdel(
        keys.game_flags(chat_id),
        keys.field(f"dodge_vote:{victim}"),
    )
    lang = deps.lang_of(update)
    await ack_selection(
        query,
        deps.texts().get(
            "SelectOk",
            lang,
            bundle="vote",
        ),
    )


def dodge_day_pattern() -> str:
    """Pattern for dodge-day callbacks."""
    tpl = load_json(CALLBACK_TEMPLATES)
    return str(tpl["dodge_day_handler_pattern"])


def dodge_vote_pattern() -> str:
    """Pattern for dodge-vote callbacks."""
    tpl = load_json(CALLBACK_TEMPLATES)
    return str(tpl["dodge_vote_handler_pattern"])
