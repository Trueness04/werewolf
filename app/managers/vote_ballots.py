"""Ballot casting and early-end helpers."""

from __future__ import annotations

import json
from random import SystemRandom
from time import time
from typing import Any

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.settings import Settings
from app.managers.chat_bridge import ChatBridge
from app.managers.game_event import log_game_event
from app.managers.text_managers import TextManager


class VoteBallots:
    """Record votes with mayor/fool weight rules."""

    def __init__(
        self,
        bridge: ChatBridge,
        keys: RedisKeySpace,
        texts: TextManager,
        settings: Settings,
    ) -> None:
        self._bridge = bridge
        self._keys = keys
        self._texts = texts
        self._settings = settings
        self._rng = SystemRandom()

    async def cast(
        self,
        chat_id: int,
        voter_id: int,
        target_id: int,
        players: list[dict[str, Any]],
    ) -> bool:
        """Record vote once; announce public/secret."""
        redis = await get_redis()
        ballots_key = self._keys.vote_ballots(chat_id)
        all_ballots = await redis.hgetall(ballots_key)
        for raw in all_ballots.values():
            voters = json.loads(raw)
            if voter_id in voters:
                return False
        roles = json.loads(
            await redis.get(
                self._keys.game_roles(chat_id)
            )
            or "{}"
        )
        final_target = target_id
        if roles.get(str(voter_id)) == "role_PesarGij":
            if self._rng.random() < 0.5:
                others = [
                    int(p["user_id"])
                    for p in players
                    if int(p["user_id"])
                    not in {voter_id, target_id}
                ]
                if others:
                    final_target = self._rng.choice(
                        others
                    )
        weight = 1
        mayor = await redis.hget(
            self._keys.game_flags(chat_id),
            self._keys.field("mayor_revealed"),
        )
        if mayor and int(mayor) == voter_id:
            weight = 2
        raw = await redis.hget(
            ballots_key,
            str(final_target),
        )
        voters = json.loads(raw) if raw else []
        voters.extend([voter_id] * weight)
        await redis.hset(
            ballots_key,
            str(final_target),
            json.dumps(voters),
        )
        lang = self._settings.default_lang
        names = {
            int(p["user_id"]): str(p["fullname"])
            for p in players
        }
        from app.managers.group_flags import (
            group_secret_vote,
        )

        if await group_secret_vote(chat_id):
            alive = len(players)
            voters = set()
            for raw in (
                await redis.hgetall(ballots_key)
            ).values():
                for vid in json.loads(raw):
                    voters.add(int(vid))
            await self._bridge.send_text(
                chat_id,
                self._texts.get(
                    "vote_secret_count",
                    lang,
                    len(voters),
                    alive,
                    bundle="vote",
                ),
            )
        else:
            await self._bridge.send_text(
                chat_id,
                self._texts.get(
                    "vote_public",
                    lang,
                    names.get(voter_id, voter_id),
                    names.get(
                        final_target,
                        final_target,
                    ),
                    bundle="vote",
                ),
            )
        await self.maybe_early_end(chat_id)
        from app.managers.afk_vote import clear_dont_vote

        await clear_dont_vote(
            self._keys,
            chat_id,
            voter_id,
        )
        log_game_event(
            "vote_cast",
            chat_id=chat_id,
            user_id=voter_id,
            target=final_target,
            weight=weight,
        )
        return True

    async def maybe_early_end(
        self,
        chat_id: int,
    ) -> None:
        """If all vote UIs cast, cut timer to ~2s."""
        redis = await get_redis()
        sent = await redis.smembers(
            self._keys.vote_sent(chat_id)
        )
        if len(sent) <= 1:
            return
        ballots = await redis.hgetall(
            self._keys.vote_ballots(chat_id)
        )
        voters: set[int] = set()
        for raw in ballots.values():
            for vid in json.loads(raw):
                voters.add(int(vid))
        if len(voters) < len(sent):
            return
        await redis.set(
            self._keys.timer_end(chat_id),
            str(int(time()) + 2),
        )
