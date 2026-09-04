"""Advance vote → night after lynch settle."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import GAME_PHASES
from app.database.models.game import GameRow
from app.database.session import session_scope
from app.managers.chat_bridge import ChatBridge
from app.managers.end_game_manager import EndGameManager
from app.managers.game_event import log_game_event
from app.managers.json_loader import load_json


async def advance_to_night(
    bridge: ChatBridge,
    keys: RedisKeySpace,
    ender: EndGameManager,
    chat_id: int,
    night_starter: Any | None,
) -> None:
    """Bump night_count and start next night."""
    if await ender.is_ended(chat_id):
        return
    redis = await get_redis()
    await redis.srem(
        keys.active_vote_chats(),
        str(chat_id),
    )
    night_n = int(
        await redis.get(keys.night_count(chat_id))
        or "0"
    )
    flags = keys.game_flags(chat_id)
    await redis.hdel(
        flags,
        keys.field("mast_block"),
        keys.field("silver_active"),
    )
    from app.managers.bittan_check import BittanCheck

    await BittanCheck(bridge, keys).run(chat_id)
    from app.managers.afk_vote import process_vote_afk
    from app.managers.text_managers import TextManager
    from app.config.settings import get_settings

    await process_vote_afk(
        bridge,
        keys,
        TextManager(),
        chat_id,
        get_settings().default_lang,
    )
    night_n += 1
    await redis.set(
        keys.night_count(chat_id),
        str(night_n),
    )
    key = keys.game_hash(chat_id)
    await redis.hset(
        key,
        keys.field("night_count"),
        str(night_n),
    )
    game_id = int(
        await redis.hget(key, keys.field("game_id"))
        or "0"
    )
    async with session_scope() as session:
        stmt = select(GameRow).where(GameRow.id == game_id)
        row = (
            await session.execute(stmt)
        ).scalar_one_or_none()
        if row is not None:
            row.night_count = night_n
    phases = load_json(GAME_PHASES)
    night = str(phases["redis_phases"]["night"])
    await redis.hset(
        key,
        keys.field("game_state"),
        night,
    )
    await redis.delete(keys.vote_ballots(chat_id))
    await redis.delete(keys.night_actions(chat_id))
    log_game_event(
        "to_night",
        chat_id=chat_id,
        night_count=night_n,
    )
    if night_starter:
        await night_starter(chat_id)
