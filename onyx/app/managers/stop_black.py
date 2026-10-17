"""StopBlack: BlackKnight revenge after real lynch."""

from __future__ import annotations

import json
from time import time

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.settings import Settings
from app.keyboards.inline.vote_keyboard import (
    build_black_revenge_keyboard,
)
from app.managers.chat_bridge import ChatBridge
from app.managers.text_managers import TextManager


async def open_stop_black(
    bridge: ChatBridge,
    keys: RedisKeySpace,
    texts: TextManager,
    settings: Settings,
    chat_id: int,
    actor_id: int,
    lang: str,
) -> None:
    """Extend vote timer; send revenge keyboard."""
    redis = await get_redis()
    flags = keys.game_flags(chat_id)
    await redis.hset(
        flags,
        keys.field("stop_black"),
        str(actor_id),
    )
    players = json.loads(
        await redis.get(keys.game_players(chat_id))
        or "[]"
    )
    targets: list[tuple[int, str]] = []
    for item in players:
        uid = int(item["user_id"])
        if uid == actor_id:
            continue
        state = await redis.get(keys.player_state(uid))
        if state == "dead":
            continue
        targets.append((uid, str(item["fullname"])))
    markup = build_black_revenge_keyboard(
        chat_id,
        actor_id,
        targets,
    )
    await bridge.send_text(
        actor_id,
        texts.get(
            "StopBlackPrompt",
            lang,
            bundle="vote",
        ),
        reply_markup=markup,
    )
    extend = int(settings.sheriff_shot_seconds)
    await redis.set(
        keys.timer_end(chat_id),
        str(int(time()) + extend),
    )
    await redis.sadd(
        keys.active_vote_chats(),
        str(chat_id),
    )


async def apply_stop_black_shot(
    bridge: ChatBridge,
    keys: RedisKeySpace,
    texts: TextManager,
    chat_id: int,
    actor_id: int,
    target_id: int,
    lang: str,
    mark_dead,
    to_night,
) -> None:
    """Kill revenge target then advance to night."""
    redis = await get_redis()
    pending = await redis.hget(
        keys.game_flags(chat_id),
        keys.field("stop_black"),
    )
    if not pending or int(pending) != actor_id:
        return
    await mark_dead(chat_id, target_id)
    players = json.loads(
        await redis.get(keys.game_players(chat_id))
        or "[]"
    )
    names = {
        int(p["user_id"]): str(p["fullname"])
        for p in players
    }
    await bridge.send_text(
        chat_id,
        texts.get(
            "StopBlackDone",
            lang,
            names.get(actor_id, str(actor_id)),
            names.get(target_id, str(target_id)),
            bundle="vote",
        ),
    )
    await _clear_and_night(keys, chat_id, to_night)


async def continue_stop_black_timeout(
    keys: RedisKeySpace,
    chat_id: int,
    to_night,
) -> None:
    """Skip revenge; advance to night."""
    await _clear_and_night(keys, chat_id, to_night)


async def _clear_and_night(
    keys: RedisKeySpace,
    chat_id: int,
    to_night,
) -> None:
    redis = await get_redis()
    await redis.hdel(
        keys.game_flags(chat_id),
        keys.field("stop_black"),
    )
    await redis.srem(
        keys.active_vote_chats(),
        str(chat_id),
    )
    await to_night(chat_id)
