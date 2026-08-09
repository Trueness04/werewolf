"""Resume phase after sheriff death-shot window."""

from __future__ import annotations

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.managers.chat_bridge import ChatBridge


async def resume_after_sheriff(
    bridge: ChatBridge,
    keys: RedisKeySpace,
    chat_id: int,
    to_night,
) -> None:
    """Route day→vote, night→day, else→night."""
    redis = await get_redis()
    flags = keys.game_flags(chat_id)
    source = await redis.hget(
        flags,
        keys.field("hunter_kill_source"),
    )
    held = await redis.hget(
        flags,
        keys.field("check_night_done"),
    )
    after = await redis.hget(
        flags,
        keys.field("darneshan_after_sheriff"),
    )
    await redis.hdel(
        flags,
        keys.field("sheriff_shot_pending"),
        keys.field("hunter_kill"),
        keys.field("hunter_kill_source"),
        keys.field("check_night_done"),
        keys.field("royce_selectd2"),
        keys.field("darneshan_after_sheriff"),
    )
    if (
        after
        and source != "day"
        and source != "night"
        and not held
    ):
        from app.config.settings import get_settings
        from app.managers.darneshan_resolve import (
            maybe_open_darneshan_pick,
        )
        from app.managers.text_managers import TextManager

        settings = get_settings()
        opened = await maybe_open_darneshan_pick(
            bridge,
            keys,
            TextManager(),
            settings,
            chat_id,
            int(after),
            settings.default_lang,
        )
        if opened:
            return
    if source == "day":
        await redis.srem(
            keys.active_day_chats(),
            str(chat_id),
        )
        await redis.srem(
            keys.active_vote_chats(),
            str(chat_id),
        )
        from app.managers.phase_wiring import (
            build_day_pipeline,
        )

        _d, _r, vote = build_day_pipeline(bridge)
        await vote.start_vote(chat_id)
        return
    if source == "night" or held:
        await redis.srem(
            keys.active_night_chats(),
            str(chat_id),
        )
        await redis.srem(
            keys.active_vote_chats(),
            str(chat_id),
        )
        from app.managers.day_manager import DayManager

        await DayManager(bridge).start_day(chat_id)
        return
    await to_night(chat_id)
