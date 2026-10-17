"""Queue players waiting for the next lobby."""

from __future__ import annotations

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.managers.chat_bridge import ChatBridge
from app.managers.text_managers import TextManager


class NextGameManager:
    """Redis set of users waiting for next start."""

    def __init__(
        self,
        keys: RedisKeySpace | None = None,
    ) -> None:
        self._keys = keys or RedisKeySpace()

    def _key(self, chat_id: int) -> str:
        return self._keys.next_game_list(chat_id)

    async def add(
        self,
        chat_id: int,
        user_id: int,
    ) -> bool:
        """Add user; True if newly added."""
        redis = await get_redis()
        added = await redis.sadd(
            self._key(chat_id),
            str(user_id),
        )
        return bool(added)

    async def remove(
        self,
        chat_id: int,
        user_id: int,
    ) -> None:
        """Drop user from next-game queue."""
        redis = await get_redis()
        await redis.srem(
            self._key(chat_id),
            str(user_id),
        )

    async def list_ids(self, chat_id: int) -> list[int]:
        """Return queued user ids."""
        redis = await get_redis()
        raw = await redis.smembers(self._key(chat_id))
        return [int(item) for item in raw]

    async def announce_and_clear(
        self,
        bridge: ChatBridge,
        texts: TextManager,
        chat_id: int,
        lang: str,
        names: dict[int, str] | None = None,
    ) -> None:
        """PHP NextGameMessage then clear queue."""
        ids = await self.list_ids(chat_id)
        if not ids:
            return
        labels: list[str] = []
        for uid in ids:
            if names and uid in names:
                labels.append(names[uid])
            else:
                labels.append(str(uid))
        body = texts.get(
            "NextGameList",
            lang,
            ", ".join(labels),
            bundle="lobby",
        )
        await bridge.send_text(chat_id, body)
        redis = await get_redis()
        await redis.delete(self._key(chat_id))
