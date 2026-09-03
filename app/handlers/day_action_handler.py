"""Callback handler for day yes/no and targets."""

from __future__ import annotations

import json

from telegram import Update
from telegram.ext import ContextTypes
from app.handlers.callback_safe import (
    answer_safe,
)

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import CALLBACK_TEMPLATES, DAY_ROLES
from app.handlers import deps
from app.handlers.callback_ack import ack_selection
from app.managers.day_actions import DayActions
from app.managers.game_event import log_game_event
from app.managers.json_loader import load_json


async def day_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Store/apply day action from inline callback."""
    query = update.callback_query
    if query is None or query.data is None:
        return
    user = update.effective_user
    if user is None:
        return
    await answer_safe(query)
    tpl = load_json(CALLBACK_TEMPLATES)
    prefix = str(tpl["day_prefix"])
    data = query.data
    if not data.startswith(prefix):
        return
    parts = data.split(":")
    if len(parts) < 4:
        return
    try:
        chat_id = int(parts[1])
        actor = int(parts[2])
    except ValueError:
        return
    if actor != user.id:
        return
    choice = parts[3]
    lang = deps.lang_of(update)
    tm = deps.texts()
    keys = RedisKeySpace()
    redis = await get_redis()
    role_id = str(
        await redis.get(keys.player_role(actor)) or ""
    )
    day_cfg = load_json(DAY_ROLES)
    immediate = set(day_cfg["immediate"])
    deferred = set(day_cfg["deferred"])
    if role_id not in immediate | deferred:
        name = role_id
        await context.bot.send_message(
            chat_id=actor,
            text=tm.get(
                "ErrorSelect",
                lang,
                name,
                bundle="day",
            ),
        )
        return
    label = choice
    if choice in {"yes", "no"}:
        value = choice
        if role_id in immediate:
            bridge = deps.bridge(context)
            actions = DayActions(bridge)
            ack = await actions.apply_immediate(
                chat_id,
                actor,
                role_id,
                choice,
                lang,
                user.full_name,
            )
            if ack == "SelectOk":
                text = tm.get(
                    ack,
                    lang,
                    choice,
                    bundle="day",
                )
            else:
                text = tm.get(
                    ack,
                    lang,
                    bundle="day",
                )
            await ack_selection(query, text)
            await redis.hset(
                keys.day_actions(chat_id),
                str(actor),
                value,
            )
            return
    else:
        try:
            target_id = int(choice)
        except ValueError:
            return
        value = str(target_id)
        label = await _name(
            redis,
            keys,
            chat_id,
            target_id,
        )
    await redis.hset(
        keys.day_actions(chat_id),
        str(actor),
        value,
    )
    await ack_selection(
        query,
        tm.get(
            "SelectOk",
            lang,
            label,
            bundle="day",
        ),
    )
    log_game_event(
        "day_action",
        chat_id=chat_id,
        user_id=actor,
        role=role_id,
        choice=value,
    )


async def _name(
    redis,
    keys: RedisKeySpace,
    chat_id: int,
    target_id: int,
) -> str:
    """Resolve player display name."""
    raw = await redis.get(keys.game_players(chat_id))
    if not raw:
        return str(target_id)
    for item in json.loads(raw):
        if int(item.get("user_id", 0)) == target_id:
            return str(item.get("fullname", target_id))
    return str(target_id)


def day_callback_pattern() -> str:
    """Pattern for day CallbackQueryHandler."""
    tpl = load_json(CALLBACK_TEMPLATES)
    return str(tpl["day_handler_pattern"])
