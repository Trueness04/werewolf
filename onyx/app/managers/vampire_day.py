"""Kent day-kill after vampires die (05bcd)."""

from __future__ import annotations

from typing import Any

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.managers.chat_bridge import ChatBridge
from app.managers.game_event import log_game_event
from app.managers.text_managers import TextManager


async def resolve_kent_day(
    ctx: dict[str, Any],
    lang: str,
    *,
    bridge: ChatBridge,
    keys: RedisKeySpace,
    texts: TextManager,
) -> None:
    """If kent_day_kill set, apply Kent day action kill."""
    redis = await get_redis()
    chat_id = int(ctx["chat_id"])
    flags = keys.game_flags(chat_id)
    armed = await redis.hget(
        flags,
        keys.field("kent_day_kill"),
    )
    if not armed:
        return
    roles = ctx.get("roles") or {}
    for uid_s, role_id in roles.items():
        if role_id != "role_Kent":
            continue
        state = await redis.get(
            keys.player_state(int(uid_s))
        )
        if state == "dead":
            continue
        raw = (ctx.get("actions") or {}).get(uid_s)
        if not raw:
            continue
        tid = int(raw)
        tstate = await redis.get(keys.player_state(tid))
        if tstate == "dead":
            continue
        await redis.set(keys.player_state(tid), "dead")
        t_role = str(roles.get(str(tid)) or "")
        await bridge.send_text(
            chat_id,
            texts.get(
                "KentVampireKillPlayer",
                lang,
                str(tid),
                t_role,
                bundle="general",
            ),
        )
        log_game_event(
            "kent_day_kill",
            chat_id=chat_id,
            killer=int(uid_s),
            target=tid,
        )
        return
