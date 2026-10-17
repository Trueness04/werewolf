"""Central CheckEndGame-style winner judge."""

from __future__ import annotations

from collections import Counter
from typing import Any

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import WIN_TEAM_MAP
from app.managers.json_loader import load_json
from app.managers.win_branches import (
    solo_winner,
    two_winner,
)
from app.managers.win_census import WinCensus


class WinJudge:
    """Return winner code or None to continue."""

    def __init__(
        self,
        keys: RedisKeySpace | None = None,
        census: WinCensus | None = None,
    ) -> None:
        self._keys = keys or RedisKeySpace()
        self._census = census or WinCensus(self._keys)
        self._map = load_json(WIN_TEAM_MAP)

    async def check(
        self,
        chat_id: int,
    ) -> str | None:
        """Judge current board; None = keep playing."""
        redis = await get_redis()
        flags = self._keys.game_flags(chat_id)
        if await redis.hget(
            flags,
            self._keys.field("game_is_end"),
        ):
            return None
        # HunterKill / sheriff shot hold endgame.
        for hold in (
            "sheriff_shot_pending",
            "hunter_kill",
            "check_night_done",
            "stop_black",
            "darneshan_pick_pending",
        ):
            if await redis.hget(
                flags,
                self._keys.field(hold),
            ):
                return None
        # Gas queues block all wins (sprint 2).
        if await self._census.convert_queues_open(
            chat_id
        ):
            return None
        alive = await self._census.alive_players(chat_id)
        counts = self._census.counts(alive)
        dinamit = int(
            await redis.hget(
                flags,
                self._keys.field("dinamit_finds"),
            )
            or "0"
        )
        if dinamit >= 3:
            return "dinamit"
        n = len(alive)
        if n == 0:
            return "nothing"
        mode = await redis.hget(
            self._keys.game_hash(chat_id),
            self._keys.field("game_mode"),
        )
        if n == 1:
            return solo_winner(alive[0])
        if n == 2:
            two = await two_winner(
                chat_id,
                alive,
                counts,
                self._keys,
            )
            if two is not None:
                return two
        joker = await self._joker(chat_id, alive, n)
        if joker is not None:
            return joker
        # Qatel holds unless Archer exception path
        if counts.get("qatel", 0) > 0:
            if not any(
                p.get("role") == "role_Archer"
                for p in alive
            ):
                return None
        if self._fire_lock(counts):
            return None
        if counts.get("ferqeTeem", 0) > 0 and self._only(
            counts,
            "ferqeTeem",
        ):
            return "ferqeTeem"
        only = self._only_team(counts)
        if only is not None:
            return only
        if self._wolf_overpower(counts):
            return "wolf"
        if self._vamp_overpower(counts):
            return "vampire"
        if self._fire_overpower(counts):
            return "Firefighter"
        if self._black_overpower(counts):
            return "black"
        if self._village_clear(counts):
            return "rosta"
        return None

    async def _joker(
        self,
        chat_id: int,
        alive: list[dict[str, Any]],
        n: int,
    ) -> str | None:
        """Joker/Harley book or low-player win."""
        if not any(
            p.get("win_team") == "joker" for p in alive
        ):
            return None
        redis = await get_redis()
        books = int(
            await redis.hget(
                self._keys.game_flags(chat_id),
                self._keys.field("joker_books"),
            )
            or "0"
        )
        if books >= 3:
            return "joker"
        if n <= 3 and books == 0:
            return "joker"
        return None

    def _fire_lock(self, counts: Counter[str]) -> bool:
        """Firefighter/IceQueen keep game open."""
        fire = counts.get("Firefighter", 0)
        if fire <= 0:
            return False
        return not self._fire_overpower(counts)

    def _only(
        self,
        counts: Counter[str],
        name: str,
    ) -> bool:
        """True if only this bucket is non-zero."""
        present = [k for k, v in counts.items() if v > 0]
        return present == [name]

    def _only_team(
        self,
        counts: Counter[str],
    ) -> str | None:
        """If exactly one non-zero bucket remains."""
        present = [k for k, v in counts.items() if v > 0]
        if len(present) == 1:
            return present[0]
        return None

    def _wolf_overpower(
        self,
        counts: Counter[str],
    ) -> bool:
        """Wolf >= sum of counted threats."""
        wolf = counts.get("wolf", 0)
        if wolf <= 0:
            return False
        threat = (
            counts.get("rosta", 0)
            + counts.get("black", 0)
            + counts.get("ferqeTeem", 0)
            + counts.get("Firefighter", 0)
            + counts.get("vampire", 0)
            + counts.get("monafeq", 0)
        )
        return wolf >= threat

    def _vamp_overpower(
        self,
        counts: Counter[str],
    ) -> bool:
        """Vampire only if wolf=0 and cult=0."""
        vamp = counts.get("vampire", 0)
        if vamp <= 0:
            return False
        if counts.get("wolf", 0) or counts.get(
            "ferqeTeem",
            0,
        ):
            return False
        threat = (
            counts.get("rosta", 0)
            + counts.get("black", 0)
            + counts.get("Firefighter", 0)
            + counts.get("monafeq", 0)
        )
        return vamp >= threat

    def _fire_overpower(
        self,
        counts: Counter[str],
    ) -> bool:
        """Fire strictly greater than village threats."""
        fire = counts.get("Firefighter", 0)
        if fire <= 0:
            return False
        if (
            counts.get("wolf", 0)
            or counts.get("vampire", 0)
            or counts.get("ferqeTeem", 0)
        ):
            return False
        threat = (
            counts.get("rosta", 0)
            + counts.get("black", 0)
            + counts.get("monafeq", 0)
        )
        return fire > threat

    def _black_overpower(
        self,
        counts: Counter[str],
    ) -> bool:
        """Black > rosta+fire+monafeq (remediation fix)."""
        black = counts.get("black", 0)
        if black <= 0:
            return False
        if (
            counts.get("wolf", 0)
            or counts.get("vampire", 0)
            or counts.get("ferqeTeem", 0)
        ):
            return False
        threat = (
            counts.get("rosta", 0)
            + counts.get("Firefighter", 0)
            + counts.get("monafeq", 0)
        )
        return black > threat

    def _village_clear(
        self,
        counts: Counter[str],
    ) -> bool:
        """Village wins when hostiles are gone."""
        if counts.get("rosta", 0) <= 0:
            return False
        for name in self._map["hostile_buckets"]:
            if counts.get(str(name), 0) > 0:
                return False
        return True
