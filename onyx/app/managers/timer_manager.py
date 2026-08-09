"""Join timer loop body (PHP join::Handel)."""

from __future__ import annotations

import json
from time import time

from importlib import import_module

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace

_get_mode = import_module("app.class.game_mode").get_mode
from app.config.settings import Settings, get_settings
from app.managers.chat_bridge import ChatBridge
from app.managers.game_event import (
    log_debug_tick,
    log_game_event,
)
from app.managers.game_state_manager import (
    GameStateManager,
)
from app.managers.initial_flow import InitialFlow
from app.managers.json_loader import load_json
from app.managers.lobby_manager import LobbyManager
from app.managers.text_managers import TextManager


class TimerManager:
    """Periodic join-phase processing per chat."""

    def __init__(
        self,
        bridge: ChatBridge,
        lobby: LobbyManager | None = None,
        state: GameStateManager | None = None,
        flow: InitialFlow | None = None,
        texts: TextManager | None = None,
        keys: RedisKeySpace | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._bridge = bridge
        self._lobby = lobby or LobbyManager()
        self._state = state or GameStateManager()
        self._flow = flow or InitialFlow(bridge)
        self._texts = texts or TextManager()
        self._keys = keys or RedisKeySpace()
        self._settings = settings or get_settings()

    async def tick_all(self) -> None:
        """Run tick for every active join chat."""
        redis = await get_redis()
        active = self._keys.active_join_chats()
        chats = await redis.smembers(active)
        for item in chats:
            await self.tick(int(item))

    async def tick(self, chat_id: int) -> None:
        """One join::Handel iteration for a chat."""
        redis = await get_redis()
        key = self._keys.game_hash(chat_id)
        data = await redis.hgetall(key)
        if not data:
            return
        flag = self._keys.field("start_new_game")
        if data.get(flag):
            return
        timer = int(data.get(self._keys.field("timer"), "0"))
        left = timer - int(time())
        lang = self._settings.default_lang
        log_debug_tick(chat_id, left)
        await self._maybe_starter(chat_id, data, lang)
        await self._update_list_and_cap(chat_id, lang)
        await self._warnings(chat_id, left, lang)
        if left <= 0:
            await self._finish(chat_id, lang)

    async def _maybe_starter(
        self,
        chat_id: int,
        data: dict[str, str],
        lang: str,
    ) -> None:
        """Send StarterMessage once."""
        field = self._keys.field("send_starter")
        if data.get(field):
            return
        name = data.get(
            self._keys.field("starter_name"),
            "",
        )
        text = self._texts.get(
            "StarterMessage",
            lang,
            name,
        )
        await self._bridge.send_text(chat_id, text)
        redis = await get_redis()
        key = self._keys.game_hash(chat_id)
        await redis.hset(key, field, "1")

    async def _update_list_and_cap(
        self,
        chat_id: int,
        lang: str,
    ) -> None:
        """Refresh pinned list; end if full."""
        await self.update_player_list(chat_id, lang)
        names = await self._lobby.consume_new_joins(
            chat_id,
        )
        if names:
            from app.managers.join_announce import (
                announce_player_joins,
            )

            await announce_player_joins(
                self._bridge,
                self._lobby,
                self._keys,
                self._texts,
                self._settings,
                chat_id,
                lang,
                names,
                self._track_delete,
            )
            from app.managers.session_senior import (
                maybe_refresh_session_senior,
            )

            await maybe_refresh_session_senior(
                chat_id,
                bridge=self._bridge,
                texts=self._texts,
                keys=self._keys,
                lobby=self._lobby,
                lang=lang,
            )
        count = await self._lobby.count_players(chat_id)
        if self._settings.enable_bot_to_bot and count > 0:
            from AI.lobby_fill import ensure_ai_from_redis

            await ensure_ai_from_redis(
                chat_id,
                self._bridge,
                self._lobby,
                self._keys,
                self._texts,
            )
            count = await self._lobby.count_players(
                chat_id,
            )
        if await self._at_capacity(chat_id, count):
            await self._lobby.force_timer_end(chat_id)

    async def _at_capacity(
        self,
        chat_id: int,
        count: int,
    ) -> bool:
        """True when lobby reached group max players."""
        group = await self._state.ensure_group_active(
            chat_id,
        )
        from app.managers.group_limits import max_players_of

        cap = max_players_of(
            group,
            self._settings,
        ) if group else self._settings.max_players
        return count >= cap

    async def update_player_list(
        self,
        chat_id: int,
        lang: str,
    ) -> None:
        """Edit Player_ListMessage_ID content."""
        redis = await get_redis()
        key = self._keys.game_hash(chat_id)
        field = self._keys.field("player_list_msg")
        raw_id = await redis.hget(key, field)
        if not raw_id:
            return
        players = await self._lobby.list_players(chat_id)
        text = self._lobby.player_list_text(lang, players)
        try:
            await self._bridge.edit_text(
                chat_id,
                int(raw_id),
                text,
            )
        except Exception:
            return

    async def _warnings(
        self,
        chat_id: int,
        left: int,
        lang: str,
    ) -> None:
        """Emit join time warnings in config windows."""
        from app.managers.timer_warnings import (
            emit_join_warnings,
        )

        await emit_join_warnings(
            self._bridge,
            self._texts,
            chat_id,
            left,
            lang,
            self._join_url,
            self._track_delete,
        )

    async def finish_join(
        self,
        chat_id: int,
        lang: str,
    ) -> None:
        """Public entry used by /forcestart."""
        await self._finish(chat_id, lang)

    async def _finish(
        self,
        chat_id: int,
        lang: str,
    ) -> None:
        """Close lobby or start initial flow."""
        await self._finish_body(chat_id, lang)

    async def _finish_body(
        self,
        chat_id: int,
        lang: str,
    ) -> None:
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
        if count > 0 and self._settings.enable_bot_to_bot:
            from AI.lobby_fill import ensure_ai_from_redis

            await ensure_ai_from_redis(
                chat_id,
                self._bridge,
                self._lobby,
                self._keys,
                self._texts,
            )
            count = await self._lobby.count_players(
                chat_id,
            )
        elif (
            self._settings.debug_mode
            and count < info.min_players
            and count > 0
        ):
            await self._lobby.fill_debug_players(
                chat_id,
                info.min_players - count,
            )
            count = await self._lobby.count_players(
                chat_id,
            )
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
        from app.managers.json_loader import load_json as lj

        urls = lj(URL_TEMPLATES)
        cmds = lj(COMMANDS_JSON)
        prefix = str(cmds["start_payload_prefix"])
        return str(urls["join_deeplink"]).format(
            bot=self._settings.bot_username,
            prefix=prefix,
            chat_id=chat_id,
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
        await redis.hset(
            key,
            field,
            json.dumps(data),
        )

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
