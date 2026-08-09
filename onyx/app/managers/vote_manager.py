"""Vote phase: UI, ballots, plurality finish."""

from __future__ import annotations

import json
from collections import Counter
from time import time
from typing import Any

from sqlalchemy import select

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import GAME_PHASES
from app.config.settings import Settings, get_settings
from app.database.models.game import GameRow
from app.database.session import session_scope
from app.keyboards.inline.vote_keyboard import (
    build_vote_keyboard,
)
from app.managers.chat_bridge import ChatBridge
from app.managers.game_event import log_game_event
from app.managers.game_state_manager import (
    GameStateManager,
)
from app.managers.json_loader import load_json
from app.managers.text_managers import TextManager
from app.managers.vote_ballots import VoteBallots


class VoteManager:
    """Run vote phase after successful day resolve."""

    def __init__(
        self,
        bridge: ChatBridge,
        keys: RedisKeySpace | None = None,
        texts: TextManager | None = None,
        settings: Settings | None = None,
        state: GameStateManager | None = None,
        lynch: Any | None = None,
    ) -> None:
        self._bridge = bridge
        self._keys = keys or RedisKeySpace()
        self._texts = texts or TextManager()
        self._settings = settings or get_settings()
        self._state = state or GameStateManager()
        self._lynch = lynch
        self._ballots = VoteBallots(
            bridge,
            self._keys,
            self._texts,
            self._settings,
        )

    def set_lynch(self, lynch: Any) -> None:
        """Inject lynch_resolver.resolve callable."""
        self._lynch = lynch

    async def start_vote(self, chat_id: int) -> None:
        """Enter vote; bump day_count here (doc)."""
        lang = self._settings.default_lang
        phases = load_json(GAME_PHASES)
        vote = str(phases["redis_phases"]["vote"])
        redis = await get_redis()
        flags = self._keys.game_flags(chat_id)
        peace = await redis.hget(
            flags,
            self._keys.field("peace_flag"),
        )
        key = self._keys.game_hash(chat_id)
        day_n = int(
            await redis.get(
                self._keys.day_count(chat_id)
            )
            or "1"
        )
        day_n += 1
        await redis.set(
            self._keys.day_count(chat_id),
            str(day_n),
        )
        await redis.hset(
            key,
            self._keys.field("day_count"),
            str(day_n),
        )
        game_id = int(
            await redis.hget(
                key,
                self._keys.field("game_id"),
            )
            or "0"
        )
        async with session_scope() as session:
            stmt = select(GameRow).where(
                GameRow.id == game_id
            )
            row = (
                await session.execute(stmt)
            ).scalar_one_or_none()
            if row is not None:
                row.day_count = day_n
                row.state = vote
                row.status = vote
        await self._state.set_phase(chat_id, vote)
        await redis.delete(self._keys.vote_ballots(chat_id))
        await redis.delete(self._keys.vote_sent(chat_id))
        if peace:
            await self._bridge.send_text(
                chat_id,
                self._texts.get(
                    "peace_no_lynch",
                    lang,
                    bundle="vote",
                ),
            )
            await redis.hdel(
                flags,
                self._keys.field("peace_flag"),
            )
            if self._lynch is not None:
                await self._lynch(
                    chat_id,
                    winner_id=None,
                    peace=True,
                )
            return
        duration = int(
            self._settings.vote_duration_seconds
        )
        secret = bool(self._settings.secret_vote)
        summary_key = (
            "MassgeFortypeSummery_Secretvote"
            if secret
            else "MassgeFortypeSummery_vote"
        )
        await self._bridge.send_text(
            chat_id,
            self._texts.get(
                summary_key,
                lang,
                duration,
                bundle="vote",
            ),
        )
        from app.managers.player_format import (
            announce_roster,
        )

        await announce_roster(
            self._bridge,
            self._texts,
            chat_id,
            lang,
        )
        end_at = int(time()) + duration
        await redis.set(
            self._keys.timer_end(chat_id),
            str(end_at),
        )
        await redis.sadd(
            self._keys.active_vote_chats(),
            str(chat_id),
        )
        await self.broadcast_vote_ui(chat_id)
        log_game_event(
            "vote_started",
            chat_id=chat_id,
            game_id=game_id,
            day_count=day_n,
        )

    async def broadcast_vote_ui(
        self,
        chat_id: int,
    ) -> None:
        """Send vote keyboards to living players."""
        lang = self._settings.default_lang
        redis = await get_redis()
        players = await self._alive_players(chat_id)
        sent = self._keys.vote_sent(chat_id)
        for voter in players:
            vid = int(voter["user_id"])
            if await redis.sismember(sent, str(vid)):
                continue
            targets = [
                (int(p["user_id"]), str(p["fullname"]))
                for p in players
                if int(p["user_id"]) != vid
            ]
            markup = build_vote_keyboard(
                chat_id,
                vid,
                targets,
            )
            await self._bridge.send_text(
                vid,
                self._texts.get(
                    "vote_prompt",
                    lang,
                    bundle="vote",
                ),
                reply_markup=markup,
            )
            await redis.sadd(sent, str(vid))

    async def cast_vote(
        self,
        chat_id: int,
        voter_id: int,
        target_id: int,
    ) -> bool:
        """Delegate ballot cast to VoteBallots."""
        players = await self._alive_players(chat_id)
        return await self._ballots.cast(
            chat_id,
            voter_id,
            target_id,
            players,
        )

    async def tick_vote(self, chat_id: int) -> bool:
        """True when vote timer expired."""
        redis = await get_redis()
        raw = await redis.get(
            self._keys.timer_end(chat_id)
        )
        if not raw:
            return False
        return int(raw) <= int(time())

    async def finish_vote(self, chat_id: int) -> None:
        """Plurality unique max; hand to lynch."""
        redis = await get_redis()
        await redis.srem(
            self._keys.active_vote_chats(),
            str(chat_id),
        )
        ballots = await redis.hgetall(
            self._keys.vote_ballots(chat_id)
        )
        scores: Counter[int] = Counter()
        for target_s, raw in ballots.items():
            scores[int(target_s)] = len(json.loads(raw))
        winner: int | None = None
        if scores:
            best = max(scores.values())
            tops = [
                tid
                for tid, n in scores.items()
                if n == best
            ]
            if len(tops) == 1:
                winner = tops[0]
        if self._lynch is None:
            return
        await self._lynch(
            chat_id,
            winner_id=winner,
            peace=False,
            had_votes=bool(scores),
        )

    async def _alive_players(
        self,
        chat_id: int,
    ) -> list[dict[str, Any]]:
        """Living players for vote UI/targets."""
        redis = await get_redis()
        raw = await redis.get(
            self._keys.game_players(chat_id)
        )
        players = json.loads(raw) if raw else []
        out: list[dict[str, Any]] = []
        for item in players:
            uid = int(item["user_id"])
            state = await redis.get(
                self._keys.player_state(uid)
            )
            if state == "dead":
                continue
            out.append(item)
        return out
