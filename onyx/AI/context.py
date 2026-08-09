"""Build per-agent game snapshots from Redis."""

from __future__ import annotations

import json
from typing import Any

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import DAY_ROLES
from app.managers.json_loader import load_json
from importlib import import_module

_Registry = import_module(
    "app.class.roles.registry"
).RoleRegistry


class GameContext:
    """Load shared + per-player AI view."""

    def __init__(
        self,
        keys: RedisKeySpace | None = None,
    ) -> None:
        self._keys = keys or RedisKeySpace()
        self._roles = _Registry()
        self._day_roles = load_json(DAY_ROLES)

    async def ai_ids(self, chat_id: int) -> list[int]:
        """Listed AI player ids for a chat."""
        redis = await get_redis()
        raw = await redis.smembers(
            self._keys.ai_players(chat_id)
        )
        return [int(item) for item in raw]

    async def snapshot(
        self,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any] | None:
        """Snapshot for one AI seat, or None if dead."""
        redis = await get_redis()
        state = await redis.get(
            self._keys.player_state(user_id)
        )
        if state == "dead":
            return None
        players_raw = await redis.get(
            self._keys.game_players(chat_id)
        )
        roles_raw = await redis.get(
            self._keys.game_roles(chat_id)
        )
        players = (
            json.loads(players_raw) if players_raw else []
        )
        roles = json.loads(roles_raw) if roles_raw else {}
        enriched: list[dict[str, Any]] = []
        for item in players:
            uid = int(item["user_id"])
            pst = await redis.get(
                self._keys.player_state(uid)
            )
            rid = str(roles.get(str(uid), "") or "")
            info: dict[str, Any] = {}
            if rid:
                info = self._roles.definition(rid)
            enriched.append(
                {
                    **item,
                    "alive": pst != "dead",
                    "role": rid,
                    "team": info.get("team"),
                }
            )
        role_id = str(roles.get(str(user_id), "") or "")
        role_def: dict[str, Any] = {}
        if role_id:
            role_def = dict(
                self._roles.definition(role_id)
            )
        return {
            "chat_id": chat_id,
            "self_id": user_id,
            "role_id": role_id,
            "role": role_def,
            "players": enriched,
            "day_roles": self._day_roles,
        }
