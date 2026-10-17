"""Upgrade cleanup for legacy AI lobby/game state."""

from __future__ import annotations

import json

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import REDIS_KEYS
from app.managers.json_loader import load_json

_LEGACY_NAMES = (
    "game_ai_players",
    "game_ai_personas",
    "game_ai_chat_queue",
    "game_ai_chat_count",
)


def _templates() -> list[str]:
    """Legacy key templates from the pre-removal config."""
    raw = load_json(REDIS_KEYS)
    return [str(raw[name]) for name in _LEGACY_NAMES]


def legacy_ai_keys(chat_id: int) -> list[str]:
    """Redis keys written by the removed AI module."""
    return [tpl.format(chat_id=chat_id) for tpl in _templates()]


async def drop_ai_members(
    keys: RedisKeySpace,
    chat_id: int,
) -> int:
    """Remove persisted AI seats from a lobby roster."""
    redis = await get_redis()
    ai_raw = await redis.get(legacy_ai_keys(chat_id)[0])
    try:
        ai_ids = {int(uid) for uid in json.loads(ai_raw or "[]")}
    except (TypeError, ValueError):
        return 0
    if not ai_ids:
        return 0
    field = keys.field("player_list")
    key = keys.game_hash(chat_id)
    raw = await redis.hget(key, field)
    players = json.loads(raw) if raw else []
    kept = [
        row
        for row in players
        if int(row.get("user_id", 0)) not in ai_ids
    ]
    if len(kept) != len(players):
        await redis.hset(
            key,
            field,
            json.dumps(kept, ensure_ascii=False),
        )
    return len(ai_ids)


async def purge_legacy_ai_keys(chat_id: int) -> None:
    """Delete stale AI Redis keys left by the old module."""
    redis = await get_redis()
    await redis.delete(*legacy_ai_keys(chat_id))


async def reconcile_ai_chats(
    bridge: ChatBridge,
    lang: str,
) -> None:
    """Drain active lobbies/games with legacy AI seats."""
    keys = RedisKeySpace()
    texts = TextManager()
    redis = await get_redis()
    chats: set[str] = set()
    for active in (
        keys.active_join_chats(),
        keys.active_night_chats(),
        keys.active_day_chats(),
        keys.active_vote_chats(),
    ):
        chats.update(await redis.smembers(active))
    for item in chats:
        chat_id = int(item)
        if await drop_ai_members(keys, chat_id) <= 0:
            continue
        await purge_legacy_ai_keys(chat_id)
        log_game_event("ai_legacy_reconciled", chat_id=chat_id)
        text = texts.get("NotStartGameForPlayer", lang)
        await bridge.send_text(chat_id, text)
