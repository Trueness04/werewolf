"""Initial game flow (PHP GameStarted)."""

from __future__ import annotations

from datetime import datetime, timezone
from importlib import import_module

from sqlalchemy import select

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.database.models.game import GameRow
from app.database.session import session_scope
from app.managers.chat_bridge import ChatBridge
from app.managers.flow_wiring import wire_role_assignment
from app.managers.game_event import log_game_event
from app.managers.game_state_manager import (
    GameStateManager,
)
from app.managers.role_setup_manager import (
    RoleBalanceError,
    RoleSetupManager,
)
from app.managers.text_managers import TextManager

_get_mode = import_module("app.class.game_mode").get_mode


class InitialFlow:
    """Close join and start role distribution."""

    def __init__(
        self,
        bridge: ChatBridge,
        roles: RoleSetupManager | None = None,
        state: GameStateManager | None = None,
        texts: TextManager | None = None,
        keys: RedisKeySpace | None = None,
    ) -> None:
        self._bridge = bridge
        self._roles = roles or RoleSetupManager()
        self._state = state or GameStateManager()
        self._texts = texts or TextManager()
        self._keys = keys or RedisKeySpace()
        wire_role_assignment(bridge, self._roles)

    async def start_initial_flow(
        self,
        chat_id: int,
        lang: str,
    ) -> None:
        """PHP GameStarted then role/night pipeline."""
        redis = await get_redis()
        key = self._keys.game_hash(chat_id)
        game_id_raw = await redis.hget(
            key,
            self._keys.field("game_id"),
        )
        game_id = int(game_id_raw or "0")
        now = datetime.now(timezone.utc)
        async with session_scope() as session:
            stmt = select(GameRow).where(
                GameRow.id == game_id
            )
            row = (
                await session.execute(stmt)
            ).scalar_one_or_none()
            if row is not None:
                row.started_at = now
        await redis.hset(
            key,
            self._keys.field("kill_flag"),
            "1",
        )
        text = self._texts.get("GameStart", lang)
        await self._bridge.send_text(chat_id, text)
        mode = await redis.hget(
            key,
            self._keys.field("game_mode"),
        )
        info = _get_mode(str(mode or "Normal"))
        await redis.srem(
            self._keys.active_join_chats(),
            str(chat_id),
        )
        if not info.skip_role_assign:
            try:
                await self._roles.assign_roles(chat_id)
            except RoleBalanceError:
                fail = self._texts.get(
                    "ErrorStartGame_Balance",
                    lang,
                )
                await self._bridge.send_text(
                    chat_id,
                    fail,
                )
                await self._state.close_lobby(
                    chat_id,
                    reason="balance_failed",
                )
                return
        done = self._texts.get(
            "GameStarted",
            lang,
            bundle="night",
        )
        await self._bridge.send_text(chat_id, done)
        log_game_event(
            "initial_flow_done",
            chat_id=chat_id,
            game_id=game_id,
        )
