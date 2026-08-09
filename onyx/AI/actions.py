"""Submit AI night/day/vote actions into Redis."""

from __future__ import annotations

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import DAY_ROLES
from app.config.settings import get_settings
from app.managers.chat_bridge import ChatBridge
from app.managers.day_actions import DayActions
from app.managers.game_event import log_game_event
from app.managers.json_loader import load_json
from app.managers.night_early import maybe_early_end_night
from app.managers.text_managers import TextManager
from app.managers.vote_manager import VoteManager


class AiActions:
    """Apply AI decisions using real game managers."""

    def __init__(
        self,
        bridge: ChatBridge,
        keys: RedisKeySpace | None = None,
        texts: TextManager | None = None,
    ) -> None:
        self._bridge = bridge
        self._keys = keys or RedisKeySpace()
        self._texts = texts or TextManager()
        self._day = DayActions(
            bridge,
            self._keys,
            self._texts,
        )
        self._day_cfg = load_json(DAY_ROLES)

    async def night(
        self,
        chat_id: int,
        user_id: int,
        choice: str,
    ) -> None:
        """Store night action and maybe early-end."""
        redis = await get_redis()
        await redis.hset(
            self._keys.night_actions(chat_id),
            str(user_id),
            choice,
        )
        await maybe_early_end_night(chat_id, self._keys)
        log_game_event(
            "ai_night_action",
            chat_id=chat_id,
            user_id=user_id,
            choice=choice,
        )

    async def day(
        self,
        chat_id: int,
        user_id: int,
        role_id: str,
        choice: str,
        fullname: str,
    ) -> None:
        """Immediate day effect and/or store target."""
        lang = get_settings().default_lang
        immediate = {
            str(item)
            for item in self._day_cfg["immediate"]
        }
        if role_id in immediate:
            await self._day.apply_immediate(
                chat_id,
                user_id,
                role_id,
                choice,
                lang,
                fullname,
            )
        redis = await get_redis()
        await redis.hset(
            self._keys.day_actions(chat_id),
            str(user_id),
            choice,
        )
        log_game_event(
            "ai_day_action",
            chat_id=chat_id,
            user_id=user_id,
            choice=choice,
        )

    async def vote(
        self,
        chat_id: int,
        user_id: int,
        target_id: int,
    ) -> None:
        """Cast vote through VoteManager."""
        vote = VoteManager(self._bridge)
        await vote.cast_vote(
            chat_id,
            user_id,
            target_id,
        )
        log_game_event(
            "ai_vote",
            chat_id=chat_id,
            user_id=user_id,
            target=target_id,
        )

    async def sheriff_shot(
        self,
        chat_id: int,
        actor_id: int,
        target_id: int,
    ) -> None:
        """Finish sheriff death-shot via lynch path."""
        from app.managers.lynch_resolver import (
            LynchResolver,
        )
        from app.managers.night_manager import (
            NightManager,
        )

        lynch = LynchResolver(self._bridge)
        night = NightManager(self._bridge)
        lynch.set_night_starter(night.start_night)
        await lynch.apply_sheriff_shot(
            chat_id,
            actor_id,
            target_id,
        )
