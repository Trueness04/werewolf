"""Callback handler for night target / yes-no."""

from __future__ import annotations

import json

from telegram import Update
from telegram.ext import ContextTypes

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import CALLBACK_TEMPLATES
from app.handlers import deps
from app.handlers.callback_ack import ack_selection
from app.managers.game_event import log_game_event
from app.managers.json_loader import load_json
from app.managers.night_early import maybe_early_end_night
from importlib import import_module

_Registry = import_module(
    "app.class.roles.registry"
).RoleRegistry


async def night_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Store night action from inline callback."""
    query = update.callback_query
    if query is None or query.data is None:
        return
    user = update.effective_user
    if user is None:
        return
    await query.answer()
    tpl = load_json(CALLBACK_TEMPLATES)
    prefix = str(tpl["prefix"])
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
    role_id = await redis.get(keys.player_role(actor))
    if not role_id:
        return
    registry = _Registry()
    role = registry.create(str(role_id))
    if not role.night1_active:
        name = tm.get(
            str(role.message_keys["name"]),
            lang,
            bundle="roles",
        )
        await context.bot.send_message(
            chat_id=actor,
            text=tm.get(
                "ErrorSelect",
                lang,
                name,
                bundle="night",
            ),
        )
        return
    label = choice
    if role.target_type == "yes_no":
        if choice not in {"yes", "no"}:
            return
        value = choice
        ok_key = (
            "SelectOk" if choice == "yes" else "SelectOk_no"
        )
    elif role.target_type == "single_target":
        try:
            target_id = int(choice)
        except ValueError:
            return
        value = str(target_id)
        ok_key = "SelectOk"
        label = await _target_name(
            redis,
            keys,
            chat_id,
            target_id,
        )
    else:
        return
    await redis.hset(
        keys.night_actions(chat_id),
        str(actor),
        value,
    )
    if ok_key == "SelectOk":
        text = tm.get(
            ok_key,
            lang,
            label,
            bundle="night",
        )
    else:
        text = tm.get(ok_key, lang, bundle="night")
    await ack_selection(query, text)
    log_game_event(
        "night_action",
        chat_id=chat_id,
        user_id=actor,
        role=str(role_id),
        choice=value,
    )
    await maybe_early_end_night(chat_id, keys)


async def _target_name(
    redis,
    keys: RedisKeySpace,
    chat_id: int,
    target_id: int,
) -> str:
    """Resolve target display name from Redis."""
    raw = await redis.get(keys.game_players(chat_id))
    if not raw:
        return str(target_id)
    players = json.loads(raw)
    for item in players:
        if int(item.get("user_id", 0)) == target_id:
            return str(item.get("fullname", target_id))
    return str(target_id)


def night_callback_pattern() -> str:
    """Pattern for PTB CallbackQueryHandler."""
    tpl = load_json(CALLBACK_TEMPLATES)
    return str(tpl["handler_pattern"])
