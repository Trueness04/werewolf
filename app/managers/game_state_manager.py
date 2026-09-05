"""Group game state (PHP GR::CheckGPGameState)."""

from __future__ import annotations

from enum import IntEnum
from json import loads as json_loads
from time import time

from sqlalchemy import select

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import GAME_PHASES
from app.database.models.group import GroupRow
from app.database.session import session_scope
from app.managers.game_event import log_game_event
from app.managers.json_loader import load_json


class GroupInactive(Exception):
    """Group exists but is not active."""


def _states() -> dict[str, int]:
    """Load numeric state codes from config."""
    raw = load_json(GAME_PHASES)
    return {
        str(k): int(v)
        for k, v in raw["states"].items()
    }


def _phases() -> dict[str, object]:
    """Load phase config document."""
    return load_json(GAME_PHASES)


class GameState(IntEnum):
    """Placeholder; values overwritten at runtime."""

    NO_GAME = 0
    RUNNING = 1
    JOINING = 2
    CHALLENGE_JOINING = 3


def build_game_state_enum() -> type[IntEnum]:
    """Build IntEnum from game_phases.json."""
    return IntEnum("GameState", _states())


GameState = build_game_state_enum()  # type: ignore[misc]


class GameStateManager:
    """Read/write lobby phase in Redis + group gate."""

    def __init__(
        self,
        keys: RedisKeySpace | None = None,
    ) -> None:
        self._keys = keys or RedisKeySpace()

    async def ensure_group_active(
        self,
        chat_id: int,
    ) -> GroupRow | None:
        """Return active group; auto-create if missing.

        Inactive groups yield silent ignore (PHP).
        """
        from app.config.settings import get_settings

        phases = _phases()
        active = str(phases["group_active_value"])
        async with session_scope() as session:
            stmt = select(GroupRow).where(
                GroupRow.chat_id == chat_id
            )
            row = (
                await session.execute(stmt)
            ).scalar_one_or_none()
            if row is None:
                lang = get_settings().default_lang
                row = GroupRow(
                    chat_id=chat_id,
                    status=active,
                    lang=lang,
                    text_mode="general",
                    pin_player_message=False,
                    allow_extend=True,
                    allow_flee=True,
                    vampire_role_on=True,
                    bloodthirsty_role_on=True,
                )
                session.add(row)
                await session.flush()
                log_game_event(
                    "group_auto_created",
                    chat_id=chat_id,
                )
                return row
        if row.status != active:
            log_game_event(
                "group_inactive_skip",
                chat_id=chat_id,
                status=row.status,
            )
            return None
        return row

    async def get_group_state(
        self,
        chat_id: int,
    ) -> GameState:
        """Map Redis fields to PHP-equivalent state."""
        group = await self.ensure_group_active(chat_id)
        if group is None:
            raise GroupInactive()
        redis = await get_redis()
        key = self._keys.game_hash(chat_id)
        fields = self._keys
        data = await redis.hgetall(key)
        if not data:
            return GameState.NO_GAME
        state = data.get(fields.field("game_state"), "")
        timer_raw = data.get(fields.field("timer"), "0")
        try:
            timer = int(timer_raw)
        except ValueError:
            timer = 0
        phases = _phases()
        redis_phases = phases["redis_phases"]
        join_name = str(redis_phases["join"])
        challenge = str(redis_phases["challenge_join"])
        running = {
            str(item)
            for item in phases["running_phases"]
        }
        challenge_flag = data.get(
            fields.field("challenge"),
            "",
        )
        now = int(time())
        if state in running:
            return GameState.RUNNING
        if (
            state == challenge
            or challenge_flag
        ) and timer > now:
            return GameState.CHALLENGE_JOINING
        if state == join_name and timer > now:
            return GameState.JOINING
        if state == join_name and timer <= now:
            return GameState.JOINING
        return GameState.NO_GAME

    async def set_phase(
        self,
        chat_id: int,
        phase: str,
    ) -> None:
        """Set redis game_state field to phase name."""
        redis = await get_redis()
        key = self._keys.game_hash(chat_id)
        field = self._keys.field("game_state")
        await redis.hset(key, field, phase)
        log_game_event(
            "phase_change",
            chat_id=chat_id,
            phase=phase,
        )

    async def close_lobby(
        self,
        chat_id: int,
        reason: str,
    ) -> None:
        """Clear all live Redis lobby keys — no orphans."""
        redis = await get_redis()
        cid = str(chat_id)
        try:
            players_raw = await redis.get(self._keys.game_players(chat_id))
            players = json_loads(players_raw) if players_raw else []
            for item in players:
                uid = int(item["user_id"])
                await redis.delete(self._keys.join_user(uid))
                await redis.delete(self._keys.player_state(uid))
                await redis.delete(self._keys.player_role(uid))
        except Exception as e:
            log_game_event(
                "lobby_cleanup_err",
                chat_id=chat_id,
                detail=f"player_keys: {e}",
            )
        for method in (
            self._keys.game_hash,
            self._keys.game_players,
            self._keys.game_roles,
            self._keys.night_actions,
            self._keys.day_actions,
            self._keys.day_sent,
            self._keys.vote_ballots,
            self._keys.vote_sent,
            self._keys.night_sent,
            self._keys.role_intro_sent,
            self._keys.game_flags,
            self._keys.night_count,
            self._keys.day_count,
            self._keys.timer_end,
        ):
            try:
                await redis.delete(method(chat_id))
            except Exception as e:
                log_game_event(
                    "lobby_cleanup_err",
                    chat_id=chat_id,
                    detail=f"{method.__name__}: {e}",
                )
        for active in (
            self._keys.active_join_chats(),
            self._keys.active_night_chats(),
            self._keys.active_day_chats(),
            self._keys.active_vote_chats(),
        ):
            try:
                await redis.srem(active, cid)
            except Exception as e:
                log_game_event(
                    "lobby_cleanup_err",
                    chat_id=chat_id,
                    detail=f"active_set: {e}",
                )
        log_game_event(
            "lobby_closed",
            chat_id=chat_id,
            phase="NO_GAME",
            reason=reason,
        )
