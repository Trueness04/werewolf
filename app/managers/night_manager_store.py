"""Player store mixin for NightManager."""

from __future__ import annotations

import json
from typing import Any

from app.cache.redis_client import get_redis
from importlib import import_module

_Registry = import_module(
    "app.class.roles.registry"
).RoleRegistry


class NightManagerStore:
    """Mixin: Redis player loading (uses self._keys)."""

    async def _load_players(
        self,
        chat_id: int,
    ) -> list[dict[str, Any]]:
        """Load players list from Redis."""
        redis = await get_redis()
        raw = await redis.get(
            self._keys.game_players(chat_id),
        )
        roles_raw = await redis.get(
            self._keys.game_roles(chat_id),
        )
        players = json.loads(raw) if raw else []
        roles = json.loads(roles_raw) if roles_raw else {}
        out = []
        for item in players:
            uid = str(item["user_id"])
            role_id = roles.get(uid)
            state = await redis.get(
                self._keys.player_state(int(uid)),
            )
            alive = state != "dead"
            info = (
                self._registry.definition(role_id)
                if role_id
                else {}
            )
            out.append(
                {
                    **item,
                    "role": role_id,
                    "team": info.get("team"),
                    "alive": alive,
                }
            )
        return out
