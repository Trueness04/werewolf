"""Periodic orphan Redis keys cleanup.

Scans for game:* keys without corresponding active sets and removes them,
plus any stranded join_user entries.
"""

from __future__ import annotations

import json

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.managers.game_event import log_game_event


async def clean_orphaned_keys() -> dict[str, int]:
    """Remove orphaned game:* keys and stranded join_user entries.

    Returns counts of deleted items.
    """
    redis = await get_redis()
    keys = RedisKeySpace()
    stats = {"games": 0, "join_users": 0, "other": 0}

    # Get all active sets
    active_night = await redis.smembers(keys.active_night_chats())
    active_day = await redis.smembers(keys.active_day_chats())
    active_vote = await redis.smembers(keys.active_vote_chats())
    active_join = await redis.smembers(keys.active_join_chats())

    active_chats = set()
    for s in (active_night, active_day, active_vote, active_join):
        for item in s:
            active_chats.add(int(item))

    # Scan all game:* keys
    all_game_keys = await redis.keys("game:*")
    for key in all_game_keys:
        # Extract chat_id from key like
        # "game:-1002763212841" or
        # "game:-1002763212841:roles"
        parts = key.split(":")
        if len(parts) < 2:
            continue
        try:
            chat_id = int(parts[1])
        except ValueError:
            continue

        # If this chat is not active, the key is orphaned
        if chat_id not in active_chats:
            await redis.delete(key)
            stats["games"] += 1

    # Clean stranded join_user keys
    all_join_keys = await redis.keys("GamePl:join_user:*")
    for key in all_join_keys:
        # Get the chat_id this join_user points to
        chat_id_str = await redis.get(key)
        if chat_id_str is None:
            await redis.delete(key)
            stats["join_users"] += 1
            continue

        try:
            chat_id = int(chat_id_str)
        except ValueError:
            await redis.delete(key)
            stats["join_users"] += 1
            continue

        # If the chat is not active, this join_user is stranded
        if chat_id not in active_chats:
            await redis.delete(key)
            stats["join_users"] += 1

    if stats["games"] > 0 or stats["join_users"] > 0:
        log_game_event(
            "orphan_cleanup",
            games=stats["games"],
            join_users=stats["join_users"],
        )

    return stats
