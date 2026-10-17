"""Apply sheriff death-shot announcement + resume."""

from __future__ import annotations

import json
from typing import Any, Callable, Awaitable

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.managers.chat_bridge import ChatBridge
from app.managers.lynch_resume import resume_after_sheriff
from app.managers.text_managers import TextManager


async def finish_sheriff_shot(
    bridge: ChatBridge,
    keys: RedisKeySpace,
    texts: TextManager,
    lang: str,
    chat_id: int,
    actor_id: int,
    target_id: int,
    mark_dead: Callable[..., Awaitable[None]],
    to_night: Callable[[int], Awaitable[None]],
) -> None:
    """Kill target, announce, resume by source."""
    redis = await get_redis()
    await mark_dead(chat_id, target_id)
    players = json.loads(
        await redis.get(keys.game_players(chat_id))
        or "[]"
    )
    names = {
        int(item["user_id"]): str(item["fullname"])
        for item in players
    }
    hunter = names.get(actor_id, str(actor_id))
    target = names.get(target_id, str(target_id))
    roles = json.loads(
        await redis.get(keys.game_roles(chat_id))
        or "{}"
    )
    role_id = str(roles.get(str(target_id), ""))
    role_name = role_id
    if role_id:
        from importlib import import_module

        registry = import_module(
            "app.class.roles.registry"
        ).RoleRegistry()
        mk = registry.definition(role_id)[
            "message_keys"
        ]["name"]
        role_name = texts.get(
            str(mk),
            lang,
            bundle="roles",
        )
    role_line = texts.get(
        "user_role",
        lang,
        role_name,
        bundle="vote",
    )
    await bridge.send_text(
        chat_id,
        texts.get(
            "sheriff_shot_done",
            lang,
            hunter,
            target,
            role_line,
            bundle="vote",
        ),
    )
    await resume_after_sheriff(
        bridge,
        keys,
        chat_id,
        to_night,
    )
