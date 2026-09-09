"""Lobby finish + cleanup mixin for TimerManager."""

from __future__ import annotations

import json
from time import time

from importlib import import_module

from app.cache.redis_client import get_redis
from app.managers.game_event import log_game_event

_get_mode = import_module(
    "app.class.game_mode"
).get_mode


class TimerFinishMixin:
    """Mixin: finish body + delete tracking."""

    async def _finish_body(self, chat_id: int, lang: str) -> None:
        """Close lobby or start initial flow body."""
        redis = await get_redis()
        key = self._keys.game_hash(chat_id)
        await redis.hset(
            key,
            self._keys.field("start_new_game"),
            "1",
        )
        await redis.hdel(
            key,
            self._keys.field("time_update"),
            self._keys.field("user_join"),
        )
        mode = await redis.hget(
            key,
            self._keys.field("game_mode"),
        )
        mode_name = str(mode or "Normal")
        info = _get_mode(mode_name)
        count = await self._lobby.count_players(chat_id)
        if (
            count > 0
            and self._settings.enable_bot_to_bot
        ):
            from app.integrations.ai_gate import maybe_run_ai

            await maybe_run_ai(
                "AI.lobby_fill",
                "ensure_ai_from_redis",
                "timer_manager.py:_finish_body",
                chat_id,
                self._bridge,
                self._lobby,
                self._keys,
                self._texts,
            )
            count = await self._lobby.count_players(chat_id)
        elif (
            self._settings.debug_mode
            and count < info.min_players
            and count > 0
        ):
            await self._lobby.fill_debug_players(
                chat_id,
                info.min_players - count,
            )
            count = await self._lobby.count_players(chat_id)
        await self.update_player_list(chat_id, lang)
        await self._flush_deletes(chat_id)
        if count < info.min_players:
            await self._state.close_lobby(
                chat_id,
                reason="join",
            )
            text = self._texts.get(
                "NotStartGameForPlayer",
                lang,
            )
            await self._bridge.send_text(chat_id, text)
            log_game_event(
                "join_failed_count",
                chat_id=chat_id,
                count=count,
            )
            return
        await self._flow.start_initial_flow(chat_id, lang)

    async def _left(self, chat_id: int) -> int:
        """Seconds remaining on join timer."""
        timer = await self._lobby.get_timer(chat_id)
        return timer - int(time())

    async def _join_url(self, chat_id: int) -> str:
        """Build deeplink join URL from templates."""
        from app.config.paths import (
            COMMANDS_JSON,
            URL_TEMPLATES,
        )
        from app.managers.json_loader import (
            load_json as lj,
        )

        urls = lj(URL_TEMPLATES)
        cmds = lj(COMMANDS_JSON)
        prefix = str(cmds["start_payload_prefix"])
        redis = await get_redis()
        raw = await redis.hget(
            self._keys.game_hash(chat_id),
            self._keys.field("game_id"),
        )
        return str(urls["join_deeplink"]).format(
            bot=self._settings.bot_username,
            prefix=prefix,
            chat_id=chat_id,
            game_id=str(raw or "0"),
        )

    async def _track_delete(
        self,
        chat_id: int,
        message_id: int,
    ) -> None:
        """Append message_id to deleteMessage list."""
        redis = await get_redis()
        key = self._keys.game_hash(chat_id)
        field = self._keys.field("delete_message")
        raw = await redis.hget(key, field)
        data = json.loads(raw) if raw else []
        if not isinstance(data, list):
            data = []
        data.append(message_id)
        await redis.hset(key, field, json.dumps(data))

    async def _flush_deletes(self, chat_id: int) -> None:
        """Delete tracked ephemeral lobby messages."""
        redis = await get_redis()
        key = self._keys.game_hash(chat_id)
        field = self._keys.field("delete_message")
        raw = await redis.hget(key, field)
        await redis.hset(key, field, "[]")
        if not raw:
            return
        data = json.loads(raw)
        if not isinstance(data, list):
            return
        for mid in data:
            await self._bridge.delete(chat_id, int(mid))
