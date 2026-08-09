"""Lynch post-processing then return to night."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import GAME_PHASES, LYNCH_ORDER
from app.config.settings import Settings, get_settings
from app.database.models.game import GameRow
from app.database.session import session_scope
from app.managers.chat_bridge import ChatBridge
from app.managers.end_game_manager import EndGameManager
from app.managers.game_event import log_game_event
from app.managers.json_loader import load_json
from app.managers.lynch_effects import LynchEffects
from app.managers.text_managers import TextManager


class LynchResolver:
    """Apply plurality winner with fixed post-order."""

    def __init__(
        self,
        bridge: ChatBridge,
        keys: RedisKeySpace | None = None,
        texts: TextManager | None = None,
        settings: Settings | None = None,
        night_starter: Any | None = None,
    ) -> None:
        self._bridge = bridge
        self._keys = keys or RedisKeySpace()
        self._texts = texts or TextManager()
        self._settings = settings or get_settings()
        self._order = [
            str(item)
            for item in load_json(LYNCH_ORDER)["order"]
        ]
        self._night_starter = night_starter
        self._fx = LynchEffects(
            bridge,
            self._keys,
            self._texts,
            self._settings,
        )
        self._end = EndGameManager(
            bridge,
            self._keys,
            self._texts,
            self._settings,
        )

    def set_night_starter(self, starter: Any) -> None:
        """Inject night_manager start for next night."""
        self._night_starter = starter

    async def resolve(
        self,
        chat_id: int,
        winner_id: int | None,
        peace: bool = False,
        had_votes: bool = True,
    ) -> None:
        """Post-process lynch then advance night."""
        lang = self._settings.default_lang
        log_game_event(
            "lynch_resolve",
            chat_id=chat_id,
            winner=winner_id,
            peace=peace,
        )
        if peace:
            await self._to_night(chat_id)
            return
        if winner_id is None:
            key = "no_kill" if had_votes else "no_votes"
            await self._bridge.send_text(
                chat_id,
                self._texts.get(
                    key,
                    lang,
                    bundle="vote",
                ),
            )
            await self._to_night(chat_id)
            return
        redis = await get_redis()
        roles = json.loads(
            await redis.get(
                self._keys.game_roles(chat_id)
            )
            or "{}"
        )
        role_id = str(roles.get(str(winner_id), ""))
        handled = False
        for step in self._order:
            if step == "prince" and role_id == (
                "role_Shahzade"
            ):
                handled = await self._fx.prince(
                    chat_id,
                    winner_id,
                    lang,
                )
                if handled:
                    break
            elif (
                step == "black_knight"
                and role_id == "role_BlackKnight"
            ):
                handled = await self._fx.black_knight(
                    chat_id,
                    winner_id,
                    lang,
                )
                if handled:
                    break
            elif (
                step == "hypocrite"
                and role_id == "role_monafeq"
            ):
                await self._fx.normal_death(
                    chat_id,
                    winner_id,
                    role_id,
                    lang,
                )
                await self._end.end(chat_id, "monafeq")
                return
            elif step == "sheriff" and role_id == (
                "role_kalantar"
            ):
                handled = await self._fx.sheriff(
                    chat_id,
                    winner_id,
                    lang,
                )
                if handled:
                    return
            elif step == "normal_death" and not handled:
                await self._fx.normal_death(
                    chat_id,
                    winner_id,
                    role_id,
                    lang,
                )
                handled = True
        await self._to_night(chat_id)

    async def continue_after_shot_timeout(
        self,
        chat_id: int,
    ) -> None:
        """Sheriff skipped shot; advance to night."""
        redis = await get_redis()
        await redis.hdel(
            self._keys.game_flags(chat_id),
            self._keys.field("sheriff_shot_pending"),
        )
        await self._to_night(chat_id)

    async def open_sheriff_shot(
        self,
        chat_id: int,
        sheriff_id: int,
    ) -> None:
        """Public entry for gunner→sheriff interrupt."""
        lang = self._settings.default_lang
        await self._fx.sheriff(
            chat_id,
            sheriff_id,
            lang,
        )

    async def apply_sheriff_shot(
        self,
        chat_id: int,
        actor_id: int,
        target_id: int,
    ) -> None:
        """Finish sheriff death-shot then go night."""
        lang = self._settings.default_lang
        redis = await get_redis()
        await self._fx.mark_dead(chat_id, target_id)
        players = json.loads(
            await redis.get(
                self._keys.game_players(chat_id)
            )
            or "[]"
        )
        names = {
            int(item["user_id"]): str(item["fullname"])
            for item in players
        }
        hunter = names.get(actor_id, str(actor_id))
        target = names.get(target_id, str(target_id))
        roles = json.loads(
            await redis.get(
                self._keys.game_roles(chat_id)
            )
            or "{}"
        )
        role_id = str(roles.get(str(target_id), ""))
        role_name = role_id
        if role_id:
            from importlib import import_module

            registry = import_module(
                "app.class.roles.registry"
            ).RoleRegistry()
            mk = registry.definition(role_id)[
                "message_keys"
            ]["name"]
            role_name = self._texts.get(
                str(mk),
                lang,
                bundle="roles",
            )
        role_line = self._texts.get(
            "user_role",
            lang,
            role_name,
            bundle="vote",
        )
        await self._bridge.send_text(
            chat_id,
            self._texts.get(
                "sheriff_shot_done",
                lang,
                hunter,
                target,
                role_line,
                bundle="vote",
            ),
        )
        flags = self._keys.game_flags(chat_id)
        await redis.hdel(
            flags,
            self._keys.field("sheriff_shot_pending"),
        )
        # Night HunterKill interrupt → resume day.
        hunter = await redis.hget(
            flags,
            self._keys.field("hunter_kill"),
        )
        held = await redis.hget(
            flags,
            self._keys.field("check_night_done"),
        )
        if hunter or held:
            await redis.hdel(
                flags,
                self._keys.field("hunter_kill"),
                self._keys.field("check_night_done"),
                self._keys.field("royce_selectd2"),
            )
            await redis.srem(
                self._keys.active_night_chats(),
                str(chat_id),
            )
            from app.managers.day_manager import (
                DayManager,
            )

            await DayManager(self._bridge).start_day(
                chat_id
            )
            return
        await self._to_night(chat_id)

    async def _to_night(self, chat_id: int) -> None:
        """Bump night_count and start next night."""
        if await self._end.is_ended(chat_id):
            return
        redis = await get_redis()
        await redis.srem(
            self._keys.active_vote_chats(),
            str(chat_id),
        )
        night_n = int(
            await redis.get(
                self._keys.night_count(chat_id)
            )
            or "0"
        )
        # Clear timed mast/silver-style blocks.
        flags = self._keys.game_flags(chat_id)
        await redis.hdel(
            flags,
            self._keys.field("mast_block"),
            self._keys.field("silver_active"),
        )
        # Sprint 2: delayed gas before next night.
        from app.managers.bittan_check import BittanCheck

        await BittanCheck(self._bridge, self._keys).run(
            chat_id
        )
        night_n += 1
        await redis.set(
            self._keys.night_count(chat_id),
            str(night_n),
        )
        key = self._keys.game_hash(chat_id)
        await redis.hset(
            key,
            self._keys.field("night_count"),
            str(night_n),
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
                row.night_count = night_n
        phases = load_json(GAME_PHASES)
        night = str(phases["redis_phases"]["night"])
        await redis.hset(
            key,
            self._keys.field("game_state"),
            night,
        )
        await redis.delete(self._keys.vote_ballots(chat_id))
        await redis.delete(self._keys.night_actions(chat_id))
        await redis.delete(self._keys.night_sent(chat_id))
        log_game_event(
            "to_night",
            chat_id=chat_id,
            night_count=night_n,
        )
        if self._night_starter is not None:
            await self._night_starter(chat_id)
