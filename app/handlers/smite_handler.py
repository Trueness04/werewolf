"""Sudo-only /smite — remove a player as fugitive (neutral)."""

from __future__ import annotations

import json

from telegram import Update
from telegram.ext import ContextTypes

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.managers.game_event import log_game_event
from app.managers.game_state_manager import (
    GameState,
    GroupInactive,
)
from app.managers.sudo import is_sudo


async def smite_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Reply-to-player: mark fugitive + neutral."""
    chat = update.effective_chat
    user = update.effective_user
    if chat is None or user is None:
        return
    if not is_sudo(user.id):
        return
    reply = update.effective_message.reply_to_message
    target = (
        reply.from_user.id if reply and reply.from_user else None
    )
    if target is None:
        await context.bot.send_message(
            chat_id=chat.id,
            text=(
                "ریپلای کن روی بازیکنی که"
                " باید فرار کنه 🏃"
            ),
        )
        return
    state_mgr = deps_state()
    try:
        state = await state_mgr.get_group_state(chat.id)
    except GroupInactive:
        return
    if state is GameState.NO_GAME:
        await context.bot.send_message(
            chat_id=chat.id,
            text="بازی‌ای در جریان نیست.",
        )
        return
    redis = await get_redis()
    keys = RedisKeySpace()
    cur_state = await redis.get(keys.player_state(target))
    if cur_state == "dead":
        await context.bot.send_message(
            chat_id=chat.id,
            text=(
                "این بازیکن از قبل مرده —"
                " smite نمیشه."
            ),
        )
        return
    await redis.set(keys.player_state(target), "neutral")
    players_raw = await redis.get(
        keys.game_players(chat_id),
    )
    players = json.loads(players_raw) if players_raw else []
    name = str(target)
    for row in players:
        if int(row["user_id"]) == target:
            name = str(row.get("fullname") or target)
            row["alive"] = False
            row["neutral"] = True
            break
    await redis.set(
        keys.game_players(chat_id),
        json.dumps(players, ensure_ascii=False),
    )
    log_game_event(
        "smite_applied",
        chat_id=chat.id,
        user_id=target,
    )
    await context.bot.send_message(
        chat_id=chat.id,
        text=(
            f"🏃 {name} فراری و متواری شد!\n"
            "در برد و باخت خنثی حساب میشه."
        ),
    )


def deps_state():
    """Lazy import avoids circular handler deps."""
    from app.handlers import deps

    return deps.state_mgr()
