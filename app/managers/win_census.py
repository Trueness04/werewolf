"""Alive-player census for win judging."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import ROLES_JSON, WIN_TEAM_MAP
from app.managers.json_loader import load_json
from importlib import import_module

_Registry = import_module(
    "app.class.roles.registry"
).RoleRegistry


class WinCensus:
    """Build alive lists and win-count buckets."""

    def __init__(
        self,
        keys: RedisKeySpace | None = None,
    ) -> None:
        self._keys = keys or RedisKeySpace()
        self._map = load_json(WIN_TEAM_MAP)
        self._registry = _Registry()
        self._defs = {
            str(item["role_id"]): item
            for item in load_json(ROLES_JSON)["roles"]
        }

    async def alive_players(
        self,
        chat_id: int,
    ) -> list[dict[str, Any]]:
        """Return alive players with role + win_team."""
        redis = await get_redis()
        raw = await redis.get(
            self._keys.game_players(chat_id)
        )
        roles_raw = await redis.get(
            self._keys.game_roles(chat_id)
        )
        players = json.loads(raw) if raw else []
        roles = json.loads(roles_raw) if roles_raw else {}
        out: list[dict[str, Any]] = []
        for item in players:
            uid = int(item["user_id"])
            state = await redis.get(
                self._keys.player_state(uid)
            )
            if state in ("dead", "neutral"):
                continue
            role_id = str(roles.get(str(uid), "") or "")
            out.append(
                {
                    **item,
                    "role": role_id,
                    "win_team": self.bucket(role_id),
                }
            )
        return out

    def bucket(self, role_id: str) -> str:
        """Map role_id to win-count bucket."""
        if not role_id:
            return "rosta"
        by_role = self._map["by_role"]
        if role_id in by_role:
            return str(by_role[role_id])
        if role_id in self._map["count_as_rosta"]:
            return "rosta"
        team = "villager"
        if role_id in self._defs:
            team = str(self._defs[role_id].get("team"))
        defaults = self._map["default_by_team"]
        return str(defaults.get(team, "rosta"))

    def counts(
        self,
        alive: list[dict[str, Any]],
    ) -> Counter[str]:
        """Count win buckets among alive players."""
        counter: Counter[str] = Counter()
        for item in alive:
            counter[str(item["win_team"])] += 1
        return counter

    async def convert_queues_open(
        self,
        chat_id: int,
    ) -> bool:
        """True if delayed convert queues block end."""
        redis = await get_redis()
        flags = self._keys.game_flags(chat_id)
        for name in (
            "convert_enchanter",
            "convert_vampire",
            "convert_wolf",
        ):
            raw = await redis.hget(
                flags,
                self._keys.field(name),
            )
            if raw:
                return True
        return False
