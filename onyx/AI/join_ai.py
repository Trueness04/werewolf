"""Fill join lobby with AI persona seats."""

from __future__ import annotations

from AI.personas import PersonaBook
from AI.registry import AgentRegistry
from AI.talker import fill_target
from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.settings import get_settings
from app.managers.chat_bridge import ChatBridge
from app.managers.game_event import log_game_event
from app.managers.lobby_manager import LobbyManager
from app.managers.text_managers import TextManager


async def fill_ai_players(
    chat_id: int,
    needed: int,
    bridge: ChatBridge | None = None,
    lobby: LobbyManager | None = None,
    keys: RedisKeySpace | None = None,
    texts: TextManager | None = None,
) -> int:
    """Register AI players with nicknames."""
    if needed <= 0:
        return 0
    settings = get_settings()
    if not settings.enable_bot_to_bot:
        return 0
    registry = AgentRegistry()
    if not bool(registry.config.get("join_when_enabled")):
        return 0
    lobby = lobby or LobbyManager()
    keys = keys or RedisKeySpace()
    texts = texts or TextManager()
    book = PersonaBook(keys)
    redis = await get_redis()
    added = 0
    index = 0
    while added < needed:
        uid = registry.make_user_id(index)
        index += 1
        other = await redis.get(keys.join_user(uid))
        if other and int(other) != chat_id:
            continue
        if await redis.sismember(
            keys.ai_players(chat_id),
            str(uid),
        ):
            continue
        persona = await book.assign(
            chat_id,
            uid,
            index - 1,
        )
        name = str(persona["nickname"])
        await lobby.register_player(chat_id, uid, name)
        await redis.sadd(
            keys.ai_players(chat_id),
            str(uid),
        )
        added += 1
        if index > needed + 50:
            break
    if bridge is not None and added:
        await bridge.send_text(
            chat_id,
            texts.get(
                "ai_players_joined",
                settings.default_lang,
                added,
            ),
        )
    log_game_event(
        "ai_fill_players",
        chat_id=chat_id,
        added=added,
        target=fill_target(),
    )
    return added
