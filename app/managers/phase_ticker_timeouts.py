"""Timeout callbacks split out of phase_ticker."""

from __future__ import annotations

import json

from app.cache.redis_client import get_redis
from app.managers.lynch_resolver import LynchResolver
from app.managers.night_manager import NightManager


async def _sheriff_timeout(
    bridge,
    keys,
    texts,
    lang: str,
    chat_id: int,
    sheriff_id: int,
) -> None:
    """Skip sheriff shot and start night."""
    redis = await get_redis()
    raw = await redis.get(
        keys.game_players(chat_id),
    )
    players = json.loads(raw) if raw else []
    name = next(
        r["fullname"]
        for r in players
        if int(r["user_id"]) == sheriff_id
    )
    msg = texts.get(
        "sheriff_shot_skip",
        lang,
        name,
        bundle="vote",
    )
    await bridge.send_text(chat_id, msg)
    lynch = LynchResolver(bridge)
    night = NightManager(bridge)
    lynch.set_night_starter(night.start_night)
    await lynch.continue_after_shot_timeout(
        chat_id,
    )


async def _stop_black_timeout(
    bridge,
    keys,
    texts,
    lang: str,
    chat_id: int,
    actor_id: int,
) -> None:
    """Skip stop-black action and start night."""
    redis = await get_redis()
    raw = await redis.get(
        keys.game_players(chat_id),
    )
    players = json.loads(raw) if raw else []
    name = next(
        r["fullname"]
        for r in players
        if int(r["user_id"]) == actor_id
    )
    msg = texts.get(
        "StopBlackSkip",
        lang,
        name,
        bundle="vote",
    )
    await bridge.send_text(chat_id, msg)
    lynch = LynchResolver(bridge)
    night = NightManager(bridge)
    lynch.set_night_starter(night.start_night)
    await lynch.continue_after_black_timeout(
        chat_id,
    )
