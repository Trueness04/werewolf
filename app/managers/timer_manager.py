"""Join timer loop body (PHP join::Handel)."""

from __future__ import annotations

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
from app.managers.timer_finish import (
    TimerFinishMixin,
)


class TimerManager(
    TimerFinishMixin,
):
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
            try:
                await self.tick(int(item))
            except Exception as exc:
                log_game_event(
                    "tick_error",
                    chat_id=int(item),
                    error=f"{type(exc).__name__}:.{exc}",
                )
        # Periodic orphan cleanup (every call for now, can throttle later)
        try:
            from app.managers.orphan_cleaner import clean_orphaned_keys
            await clean_orphaned_keys()
        except Exception as exc:
            log_game_event("orphan_clean_err", error=str(exc))

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
        await self._countdown(chat_id, left, lang)
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
            from app.integrations.ai_gate import maybe_run_ai

            await maybe_run_ai(
                "AI.lobby_fill",
                "ensure_ai_from_redis",
                "timer_manager.py:_update_list_and_cap",
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
        """Edit Player_ListMessage_ID content (only on change)."""
        redis = await get_redis()
        key = self._keys.game_hash(chat_id)
        field = self._keys.field("player_list_msg")
        raw_id = await redis.hget(key, field)
        if not raw_id:
            return
        players = await self._lobby.list_players(chat_id)
        text = self._lobby.player_list_text(lang, players)
        seen_field = self._keys.field(
            "player_list_seen"
        )
        if await redis.hget(key, seen_field) == text:
            return
        try:
            await self._bridge.edit_text(
                chat_id,
                int(raw_id),
                text,
            )
        except Exception:
            return
        await redis.hset(key, seen_field, text)

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

    async def _countdown(
        self,
        chat_id: int,
        left: int,
        lang: str,
    ) -> None:
        """Cadenced join countdown with keyboard."""
        if left <= 0:
            return
        redis = await get_redis()
        key = self._keys.game_hash(chat_id)
        field = self._keys.field(
            "join_countdown_last",
        )
        raw = await redis.hget(key, field)
        last = int(raw) if raw else None
        from app.managers.timer_warnings import (
            emit_join_countdown,
        )

        new_last = await emit_join_countdown(
            self._bridge,
            self._texts,
            chat_id,
            left,
            lang,
            self._join_url,
            self._track_delete,
            last_left=last,
        )
        if new_last is not None:
            await redis.hset(
                key,
                field,
                str(new_last),
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
