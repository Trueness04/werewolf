"""Lobby join/capacity/player-list manager."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from time import time
from typing import Any

from sqlalchemy import select

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import GAME_PHASES
from app.config.settings import Settings, get_settings
from app.database.models.game import GameRow
from app.database.models.player import PlayerRow
from app.database.models.user import UserRow
from app.database.session import session_scope
from app.managers.game_event import log_game_event
from app.managers.json_loader import load_json
from app.managers.text_managers import TextManager


class LobbyManager:
    """Create lobbies and register players."""

    def __init__(
        self,
        keys: RedisKeySpace | None = None,
        texts: TextManager | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._keys = keys or RedisKeySpace()
        self._texts = texts or TextManager()
        self._settings = settings or get_settings()

    async def start_game_for_group(
        self,
        chat_id: int,
        mode: str,
        user_id: int,
        fullname: str,
    ) -> int:
        """Create DB game + Redis join lobby."""
        phases = load_json(GAME_PHASES)
        join_phase = str(
            phases["redis_phases"]["join"]
        )
        now = datetime.now(timezone.utc)
        async with session_scope() as session:
            row = GameRow(
                chat_id=chat_id,
                mode=mode,
                starter_id=user_id,
                created_at=now,
                status=join_phase,
            )
            session.add(row)
            await session.flush()
            game_id = int(row.id)
        redis = await get_redis()
        key = self._keys.game_hash(chat_id)
        await redis.delete(key)
        await redis.delete(self._keys.ai_players(chat_id))
        await redis.delete(self._keys.ai_personas(chat_id))
        await redis.delete(
            self._keys.ai_chat_queue(chat_id)
        )
        await redis.delete(
            self._keys.ai_chat_count(chat_id)
        )
        timer = int(time()) + int(
            self._settings.join_duration_seconds
        )
        mapping = {
            self._keys.field("timer"): str(timer),
            self._keys.field("game_state"): join_phase,
            self._keys.field("starter_name"): fullname,
            self._keys.field("game_mode"): mode,
            self._keys.field("game_id"): str(game_id),
            self._keys.field("player_list"): "[]",
            self._keys.field("user_join"): "[]",
            self._keys.field("new_user_join"): "[]",
            self._keys.field("edit_markup"): "[]",
            self._keys.field("delete_message"): "[]",
        }
        await redis.hset(key, mapping=mapping)
        active = self._keys.active_join_chats()
        await redis.sadd(active, str(chat_id))
        log_game_event(
            "lobby_created",
            chat_id=chat_id,
            user_id=user_id,
            game_id=game_id,
            phase=join_phase,
            mode=mode,
        )
        return game_id

    async def count_players(self, chat_id: int) -> int:
        """Count players in Redis player_list."""
        players = await self.list_players(chat_id)
        return len(players)

    async def list_players(
        self,
        chat_id: int,
    ) -> list[dict[str, Any]]:
        """Return player dicts from Redis."""
        redis = await get_redis()
        key = self._keys.game_hash(chat_id)
        field = self._keys.field("player_list")
        raw = await redis.hget(key, field)
        if not raw:
            return []
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        return data

    async def name_taken(
        self,
        chat_id: int,
        fullname: str,
    ) -> bool:
        """True if fullname already in lobby."""
        players = await self.list_players(chat_id)
        needle = fullname.casefold()
        for item in players:
            name = str(item.get("fullname", ""))
            if name.casefold() == needle:
                return True
        return False

    async def register_player(
        self,
        chat_id: int,
        user_id: int,
        fullname: str,
    ) -> None:
        """Persist player and update Redis lists."""
        redis = await get_redis()
        key = self._keys.game_hash(chat_id)
        game_id_raw = await redis.hget(
            key,
            self._keys.field("game_id"),
        )
        game_id = int(game_id_raw or "0")
        async with session_scope() as session:
            session.add(
                PlayerRow(
                    game_id=game_id,
                    user_id=user_id,
                    fullname=fullname,
                    role=None,
                )
            )
        players = await self.list_players(chat_id)
        players.append(
            {
                "user_id": user_id,
                "fullname": fullname,
            }
        )
        await redis.hset(
            key,
            self._keys.field("player_list"),
            json.dumps(players, ensure_ascii=False),
        )
        await self._append_json_list(
            chat_id,
            "user_join",
            user_id,
        )
        await self._append_json_list(
            chat_id,
            "new_user_join",
            fullname,
        )
        join_key = self._keys.join_user(user_id)
        await redis.set(join_key, str(chat_id))
        log_game_event(
            "player_joined",
            chat_id=chat_id,
            user_id=user_id,
            game_id=game_id,
        )

    async def _append_json_list(
        self,
        chat_id: int,
        field_name: str,
        value: object,
    ) -> None:
        """Append a value to a JSON list field."""
        redis = await get_redis()
        key = self._keys.game_hash(chat_id)
        field = self._keys.field(field_name)
        raw = await redis.hget(key, field)
        data = json.loads(raw) if raw else []
        if not isinstance(data, list):
            data = []
        data.append(value)
        await redis.hset(
            key,
            field,
            json.dumps(data, ensure_ascii=False),
        )

    async def consume_new_joins(
        self,
        chat_id: int,
    ) -> list[str]:
        """Return and clear NewUserJoin names."""
        redis = await get_redis()
        key = self._keys.game_hash(chat_id)
        field = self._keys.field("new_user_join")
        raw = await redis.hget(key, field)
        await redis.hset(key, field, "[]")
        if not raw:
            return []
        data = json.loads(raw)
        if not isinstance(data, list):
            return []
        return [str(item) for item in data]

    async def get_user_coins(self, user_id: int) -> int:
        """Read user coin balance from PostgreSQL."""
        async with session_scope() as session:
            stmt = select(UserRow).where(
                UserRow.user_id == user_id
            )
            row = (
                await session.execute(stmt)
            ).scalar_one_or_none()
        if row is None:
            return 0
        return int(row.coins)

    async def deduct_coins(
        self,
        user_id: int,
        amount: int,
    ) -> bool:
        """Deduct coins; False if insufficient."""
        async with session_scope() as session:
            stmt = select(UserRow).where(
                UserRow.user_id == user_id
            )
            row = (
                await session.execute(stmt)
            ).scalar_one_or_none()
            if row is None or row.coins < amount:
                return False
            row.coins = int(row.coins) - amount
        return True

    async def force_timer_end(self, chat_id: int) -> None:
        """Set timer to now-5 to end join soon."""
        redis = await get_redis()
        key = self._keys.game_hash(chat_id)
        field = self._keys.field("timer")
        await redis.hset(key, field, str(int(time()) - 5))

    async def fill_debug_players(
        self,
        chat_id: int,
        needed: int,
    ) -> int:
        """Add ghost players so debug lobbies can start."""
        if needed <= 0:
            return 0
        added = 0
        for index in range(needed):
            uid = -(index + 1)
            name = f"DebugBot{index + 1}"
            await self.register_player(
                chat_id,
                uid,
                name,
            )
            added += 1
        log_game_event(
            "debug_fill_players",
            chat_id=chat_id,
            added=added,
        )
        return added

    async def set_timer(
        self,
        chat_id: int,
        unix_ts: int,
    ) -> None:
        """Write absolute Unix timer value."""
        redis = await get_redis()
        key = self._keys.game_hash(chat_id)
        field = self._keys.field("timer")
        await redis.hset(key, field, str(unix_ts))

    async def get_timer(self, chat_id: int) -> int:
        """Read absolute Unix timer value."""
        redis = await get_redis()
        key = self._keys.game_hash(chat_id)
        field = self._keys.field("timer")
        raw = await redis.hget(key, field)
        try:
            return int(raw or "0")
        except ValueError:
            return 0

    def player_list_text(
        self,
        lang: str,
        players: list[dict[str, Any]] | int,
        names: list[str] | None = None,
    ) -> str:
        """Build player counter message body."""
        if isinstance(players, int):
            count = players
            lines = names or []
        else:
            from app.managers.player_format import (
                mention_html,
                player_name,
            )

            count = len(players)
            lines = [
                mention_html(
                    int(p["user_id"]),
                    player_name(p),
                )
                for p in players
            ]
        header = self._texts.get("player", lang, count)
        if not lines:
            return header
        return f"{header}\n" + "\n".join(lines)
