"""Callback handlers for vote and sheriff shot."""

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
from app.managers.lynch_resolver import LynchResolver
from app.managers.vote_manager import VoteManager


async def vote_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Record a player's lynch vote."""
    query = update.callback_query
    if query is None or query.data is None:
        return
    user = update.effective_user
    if user is None:
        return
    await answer_safe(query)
    tpl = load_json(CALLBACK_TEMPLATES)
    if not query.data.startswith(str(tpl["vote_prefix"])):
        return
    parts = query.data.split(":")
    if len(parts) < 4:
        return
    try:
        chat_id = int(parts[1])
        voter = int(parts[2])
        target = int(parts[3])
    except ValueError:
        return
    if voter != user.id:
        return
    bridge = deps.bridge(context)
    manager = VoteManager(bridge)
    ok = await manager.cast_vote(chat_id, voter, target)
    if not ok:
        return
    lang = deps.lang_of(update)
    tm = deps.texts()
    await ack_selection(
        query,
        tm.get("SelectOk", lang, bundle="vote"),
    )


async def sheriff_shot_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle sheriff death-shot target pick."""
    query = update.callback_query
    if query is None or query.data is None:
        return
    user = update.effective_user
    if user is None:
        return
    await answer_safe(query)
    tpl = load_json(CALLBACK_TEMPLATES)
    prefix = str(tpl["sheriff_prefix"])
    if not query.data.startswith(prefix):
        return
    parts = query.data.split(":")
    if len(parts) < 4:
        return
    try:
        chat_id = int(parts[1])
        actor = int(parts[2])
        target = int(parts[3])
    except ValueError:
        return
    if actor != user.id:
        return
    redis = await get_redis()
    keys = RedisKeySpace()
    pending = await redis.hget(
        keys.game_flags(chat_id),
        keys.field("sheriff_shot_pending"),
    )
    if not pending or int(pending) != actor:
        return
    bridge = deps.bridge(context)
    lynch = LynchResolver(bridge)
    from app.managers.night_manager import NightManager

    lynch.set_night_starter(
        NightManager(bridge).start_night
    )
    await lynch.apply_sheriff_shot(
        chat_id,
        actor,
        target,
    )
    lang = deps.lang_of(update)
    tm = deps.texts()
    await ack_selection(
        query,
        tm.get("SelectOk", lang, bundle="vote"),
    )


async def black_revenge_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle StopBlack revenge target pick."""
    query = update.callback_query
    if query is None or query.data is None:
        return
    user = update.effective_user
    if user is None:
        return
    await answer_safe(query)
    tpl = load_json(CALLBACK_TEMPLATES)
    prefix = str(tpl["black_revenge_prefix"])
    if not query.data.startswith(prefix):
        return
    parts = query.data.split(":")
    if len(parts) < 4:
        return
    try:
        chat_id = int(parts[1])
        actor = int(parts[2])
        target = int(parts[3])
    except ValueError:
        return
    if actor != user.id:
        return
    redis = await get_redis()
    keys = RedisKeySpace()
    pending = await redis.hget(
        keys.game_flags(chat_id),
        keys.field("stop_black"),
    )
    if not pending or int(pending) != actor:
        return
    bridge = deps.bridge(context)
    lynch = LynchResolver(bridge)
    from app.managers.night_manager import NightManager

    lynch.set_night_starter(
        NightManager(bridge).start_night
    )
    await lynch.apply_black_revenge(
        chat_id,
        actor,
        target,
    )
    lang = deps.lang_of(update)
    tm = deps.texts()
    await ack_selection(
        query,
        tm.get("SelectOk", lang, bundle="vote"),
    )


async def darneshan_pick_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle DarNeshan convert pick after marked lynch."""
    query = update.callback_query
    if query is None or query.data is None:
        return
    user = update.effective_user
    if user is None:
        return
    await answer_safe(query)
    tpl = load_json(CALLBACK_TEMPLATES)
    prefix = str(tpl["darneshan_pick_prefix"])
    if not query.data.startswith(prefix):
        return
    parts = query.data.split(":")
    if len(parts) < 4:
        return
    try:
        chat_id = int(parts[1])
        actor = int(parts[2])
        target = int(parts[3])
    except ValueError:
        return
    if actor != user.id:
        return
    redis = await get_redis()
    keys = RedisKeySpace()
    pending = await redis.hget(
        keys.game_flags(chat_id),
        keys.field("darneshan_pick_pending"),
    )
    if not pending or int(pending) != actor:
        return
    bridge = deps.bridge(context)
    lynch = LynchResolver(bridge)
    from app.managers.night_manager import NightManager

    lynch.set_night_starter(
        NightManager(bridge).start_night
    )
    from app.managers.darneshan_resolve import (
        apply_darneshan_pick,
    )

    lang = deps.lang_of(update)
    tm = deps.texts()
    await apply_darneshan_pick(
        bridge,
        keys,
        tm,
        chat_id,
        actor,
        target,
        lang,
        lynch._to_night,
    )
    await ack_selection(
        query,
        tm.get("SelectOk", lang, bundle="vote"),
    )


def vote_callback_pattern() -> str:
    """Pattern for vote callbacks."""
    tpl = load_json(CALLBACK_TEMPLATES)
    return str(tpl["vote_handler_pattern"])


def sheriff_callback_pattern() -> str:
    """Pattern for sheriff death-shot callbacks."""
    tpl = load_json(CALLBACK_TEMPLATES)
    return str(tpl["sheriff_handler_pattern"])


def black_revenge_pattern() -> str:
    """Pattern for StopBlack revenge callbacks."""
    tpl = load_json(CALLBACK_TEMPLATES)
    return str(tpl["black_revenge_handler_pattern"])


def darneshan_pick_pattern() -> str:
    """Pattern for DarNeshan pick callbacks."""
    tpl = load_json(CALLBACK_TEMPLATES)
    return str(tpl["darneshan_pick_handler_pattern"])
