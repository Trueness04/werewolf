"""Lynch post-processing then return to night."""

from __future__ import annotations

import json
from typing import Any

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import LYNCH_ORDER
from app.config.settings import Settings, get_settings
from app.managers.chat_bridge import ChatBridge
from app.managers.end_game_manager import EndGameManager
from app.managers.game_event import log_game_event
from app.managers.json_loader import load_json
from app.managers.lynch_advance import advance_to_night
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
        """Inject night start callable."""
        self._night_starter = starter

    async def resolve(
        self,
        chat_id: int,
        winner_id: int | None,
        peace: bool = False,
        had_votes: bool = True,
        *,
        defer_night: bool = False,
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
            from app.managers.darneshan_resolve import (
                burn_mark_after_failed_lynch,
            )

            await burn_mark_after_failed_lynch(
                self._bridge,
                self._keys,
                self._texts,
                chat_id,
                lang,
            )
            if not defer_night:
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
            from app.managers.darneshan_resolve import (
                burn_mark_after_failed_lynch,
            )

            await burn_mark_after_failed_lynch(
                self._bridge,
                self._keys,
                self._texts,
                chat_id,
                lang,
            )
            if not defer_night:
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
        died = False
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
                saved = await self._fx.black_knight(
                    chat_id,
                    winner_id,
                    lang,
                )
                if saved:
                    handled = True
                    break
                await self._fx.normal_death(
                    chat_id,
                    winner_id,
                    role_id,
                    lang,
                )
                from app.managers.stop_black import (
                    open_stop_black,
                )

                await open_stop_black(
                    self._bridge,
                    self._keys,
                    self._texts,
                    self._settings,
                    chat_id,
                    winner_id,
                    lang,
                )
                return
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
                    # Death registered; pick after shot window
                    await redis.hset(
                        self._keys.game_flags(chat_id),
                        self._keys.field(
                            "darneshan_after_sheriff"
                        ),
                        str(winner_id),
                    )
                    return
            elif step == "normal_death" and not handled:
                await self._fx.normal_death(
                    chat_id,
                    winner_id,
                    role_id,
                    lang,
                )
                handled = True
                died = True
        if handled and not died:
            # prince / black-knight save — burn mark
            from app.managers.darneshan_resolve import (
                burn_mark_after_failed_lynch,
            )

            await burn_mark_after_failed_lynch(
                self._bridge,
                self._keys,
                self._texts,
                chat_id,
                lang,
            )
        elif handled and died:
            from app.managers.darneshan_resolve import (
                maybe_open_darneshan_pick,
            )

            opened = await maybe_open_darneshan_pick(
                self._bridge,
                self._keys,
                self._texts,
                self._settings,
                chat_id,
                winner_id,
                lang,
            )
            if opened:
                return
        if not defer_night:
            await self._to_night(chat_id)

    async def continue_after_shot_timeout(
        self,
        chat_id: int,
    ) -> None:
        """Sheriff skipped shot; advance by source."""
        from app.managers.lynch_resume import (
            resume_after_sheriff,
        )

        await resume_after_sheriff(
            self._bridge,
            self._keys,
            chat_id,
            self._to_night,
        )

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
        """Finish sheriff death-shot then resume."""
        from app.managers.sheriff_shot_apply import (
            finish_sheriff_shot,
        )

        await finish_sheriff_shot(
            self._bridge,
            self._keys,
            self._texts,
            self._settings.default_lang,
            chat_id,
            actor_id,
            target_id,
            self._fx.mark_dead,
            self._to_night,
        )

    async def apply_black_revenge(
        self,
        chat_id: int,
        actor_id: int,
        target_id: int,
    ) -> None:
        """StopBlack revenge shot then night."""
        from app.managers.stop_black import (
            apply_stop_black_shot,
        )

        await apply_stop_black_shot(
            self._bridge,
            self._keys,
            self._texts,
            chat_id,
            actor_id,
            target_id,
            self._settings.default_lang,
            self._fx.mark_dead,
            self._to_night,
        )

    async def continue_after_black_timeout(
        self,
        chat_id: int,
    ) -> None:
        """StopBlack skipped; go night."""
        from app.managers.stop_black import (
            continue_stop_black_timeout,
        )

        await continue_stop_black_timeout(
            self._keys,
            chat_id,
            self._to_night,
        )

    async def _to_night(self, chat_id: int) -> None:
        """Bump night_count and start next night."""
        await advance_to_night(
            self._bridge,
            self._keys,
            self._end,
            chat_id,
            self._night_starter,
        )
