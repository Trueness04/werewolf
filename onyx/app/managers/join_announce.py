"""Announce new lobby joins in classic format."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from importlib import import_module

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.settings import Settings
from app.managers.chat_bridge import ChatBridge
from app.managers.lobby_manager import LobbyManager
from app.managers.text_managers import TextManager

_get_mode = import_module("app.class.game_mode").get_mode
TrackFn = Callable[[int, int], Awaitable[None]]


async def announce_player_joins(
    bridge: ChatBridge,
    lobby: LobbyManager,
    keys: RedisKeySpace,
    texts: TextManager,
    settings: Settings,
    chat_id: int,
    lang: str,
    names: list[str],
    track_delete: TrackFn,
) -> None:
    """Send PlayerJoined for each new name."""
    if not names:
        return
    count = await lobby.count_players(chat_id)
    redis = await get_redis()
    mode = await redis.hget(
        keys.game_hash(chat_id),
        keys.field("game_mode"),
    )
    min_n = 5
    if mode:
        try:
            min_n = int(_get_mode(str(mode)).min_players)
        except Exception:
            min_n = 5
    max_n = int(settings.max_players)
    for name in names:
        text = texts.get(
            "PlayerJoined",
            lang,
            name,
            count,
            min_n,
            max_n,
        )
        mid = await bridge.send_text(chat_id, text)
        await track_delete(chat_id, mid)
