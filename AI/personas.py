"""Load and assign nickname personas to AI seats."""

from __future__ import annotations

import json
from random import SystemRandom
from typing import Any

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import AI_PERSONAS
from app.managers.json_loader import load_json


class PersonaBook:
    """Persona catalog + per-game assignment."""

    def __init__(
        self,
        keys: RedisKeySpace | None = None,
    ) -> None:
        self._keys = keys or RedisKeySpace()
        self._rng = SystemRandom()
        raw = load_json(AI_PERSONAS)
        self._list = [
            dict(item) for item in raw["personas"]
        ]
        self._by_id = {
            str(item["id"]): item for item in self._list
        }
        pool = raw.get("name_pool") or {}
        self._first = [str(x) for x in pool.get("first", [])]
        self._epithet = [
            str(x) for x in pool.get("epithet", [])
        ]

    def by_index(self, index: int) -> dict[str, Any]:
        """Persona for seat index (wraps)."""
        if not self._list:
            raise RuntimeError("no_personas")
        return self._list[index % len(self._list)]

    def get(self, persona_id: str) -> dict[str, Any]:
        """Lookup persona by id."""
        return self._by_id[persona_id]

    def _random_nickname(self, used: set[str]) -> str:
        """Build a fresh first+epithet nickname."""
        if not self._first or not self._epithet:
            raise RuntimeError("empty_name_pool")
        for _ in range(80):
            name = (
                f"{self._rng.choice(self._first)} "
                f"{self._rng.choice(self._epithet)}"
            )
            if name not in used:
                return name
        return (
            f"{self._rng.choice(self._first)} "
            f"{self._rng.choice(self._epithet)}"
            f" {self._rng.randrange(10, 99)}"
        )

    def _hydrate(
        self,
        persona_id: str,
        nickname: str,
    ) -> dict[str, Any]:
        """Persona copy with live nickname + system."""
        base = dict(self.get(persona_id))
        base["nickname"] = nickname
        system = str(base.get("system", ""))
        base["system"] = system.replace(
            "{nickname}",
            nickname,
        )
        return base

    async def _lobby_name(
        self,
        chat_id: int,
        user_id: int,
    ) -> str:
        """Read display name already in lobby/game."""
        redis = await get_redis()
        raw = await redis.get(
            self._keys.game_players(chat_id)
        )
        if not raw:
            return ""
        try:
            players = json.loads(raw)
        except json.JSONDecodeError:
            return ""
        for item in players:
            if int(item.get("user_id", 0)) == user_id:
                return str(item.get("name") or "")
        return ""

    async def assign(
        self,
        chat_id: int,
        user_id: int,
        index: int,
    ) -> dict[str, Any]:
        """Bind random name + persona to AI user."""
        redis = await get_redis()
        key = self._keys.ai_personas(chat_id)
        existing = await redis.hgetall(key)
        used_ids: set[str] = set()
        used_names: set[str] = set()
        for raw in existing.values():
            try:
                data = json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                used_ids.add(str(raw))
                continue
            used_ids.add(str(data.get("id", "")))
            nick = str(data.get("nickname", ""))
            if nick:
                used_names.add(nick)
        available = [
            p for p in self._list
            if str(p["id"]) not in used_ids
        ]
        base = (
            self._rng.choice(available)
            if available
            else self.by_index(index)
        )
        nickname = self._random_nickname(used_names)
        payload = json.dumps(
            {"id": str(base["id"]), "nickname": nickname},
            ensure_ascii=False,
        )
        await redis.hset(key, str(user_id), payload)
        return self._hydrate(str(base["id"]), nickname)

    async def for_user(
        self,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any] | None:
        """Return assigned persona or None."""
        redis = await get_redis()
        key = self._keys.ai_personas(chat_id)
        raw = await redis.hget(key, str(user_id))
        if not raw:
            return None
        persona_id = ""
        nickname = ""
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                persona_id = str(data.get("id") or "")
                nickname = str(
                    data.get("nickname") or ""
                )
        except (TypeError, json.JSONDecodeError):
            persona_id = str(raw)
        if not persona_id or persona_id not in self._by_id:
            return None
        if not nickname:
            nickname = await self._lobby_name(
                chat_id,
                user_id,
            )
        if not nickname:
            nickname = self._random_nickname(set())
        payload = json.dumps(
            {"id": persona_id, "nickname": nickname},
            ensure_ascii=False,
        )
        await redis.hset(key, str(user_id), payload)
        return self._hydrate(persona_id, nickname)
