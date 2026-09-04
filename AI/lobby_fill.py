"""Ensure AI seats fill an open join lobby."""

from __future__ import annotations

from importlib import import_module

from AI.join_ai import fill_ai_players
from AI.registry import ai_enabled
from AI.talker import fill_target
from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.settings import get_settings
from app.managers.chat_bridge import ChatBridge
from app.managers.lobby_manager import LobbyManager
from app.managers.text_managers import TextManager

_get_mode = import_module("app.class.game_mode").get_mode


async def ensure_ai_lobby_fill(
    chat_id: int,
    mode_name: str,
    bridge: ChatBridge | None = None,
    lobby: LobbyManager | None = None,
    keys: RedisKeySpace | None = None,
    texts: TextManager | None = None,
) -> int:
    """Add AI until fill_to / min_players is met."""
    settings = get_settings()
    if not settings.enable_bot_to_bot:
        return 0
    if not ai_enabled():
        return 0
    lobby = lobby or LobbyManager()
    info = _get_mode(mode_name or "Normal")
    target = max(int(info.min_players), fill_target())
    count = await lobby.count_players(chat_id)
    if count <= 0 or count >= target:
        return 0
    return await fill_ai_players(
        chat_id,
        target - count,
        bridge=bridge,
        lobby=lobby,
        keys=keys,
        texts=texts,
    )


async def ensure_ai_from_redis(
    chat_id: int,
    bridge: ChatBridge,
    lobby: LobbyManager,
    keys: RedisKeySpace,
    texts: TextManager,
) -> int:
    """Read mode from Redis then fill AI seats."""
    redis = await get_redis()
    mode = await redis.hget(
        keys.game_hash(chat_id),
        keys.field("game_mode"),
    )
    return await ensure_ai_lobby_fill(
        chat_id,
        str(mode or "Normal"),
        bridge=bridge,
        lobby=lobby,
        keys=keys,
        texts=texts,
    )
