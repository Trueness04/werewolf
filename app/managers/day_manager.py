"""Day phase entry, UI broadcast, timer (no early end)."""

from __future__ import annotations

from time import time
from typing import Any

from sqlalchemy import select

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import DAY_ROLES, GAME_PHASES
from app.config.settings import Settings, get_settings
from app.database.models.game import GameRow
from app.database.session import session_scope
from app.managers.chat_bridge import ChatBridge
from app.managers.day_role_ui import send_day_role_ui
from app.managers.game_event import log_game_event
from app.managers.game_state_manager import (
    GameStateManager,
)
from app.managers.json_loader import load_json
from app.managers.player_snapshot import (
    load_enriched_players,
)
from app.managers.text_managers import TextManager
from importlib import import_module

_Registry = import_module(
    "app.class.roles.registry"
).RoleRegistry


class DayManager:
    """Start and maintain the day discussion phase."""

    def __init__(
        self,
        bridge: ChatBridge,
        keys: RedisKeySpace | None = None,
        texts: TextManager | None = None,
        settings: Settings | None = None,
        state: GameStateManager | None = None,
    ) -> None:
        self._bridge = bridge
        self._keys = keys or RedisKeySpace()
        self._texts = texts or TextManager()
        self._settings = settings or get_settings()
        self._state = state or GameStateManager()
        self._registry = _Registry()
        self._day_roles = load_json(DAY_ROLES)

    async def start_day(self, chat_id: int) -> None:
        """Enter day without bumping day_count."""
        lang = self._settings.default_lang
        phases = load_json(GAME_PHASES)
        day = str(phases["redis_phases"]["day"])
        await self._state.set_phase(chat_id, day)
        from AI.talker import reset_day_chat_counts

        await reset_day_chat_counts(chat_id, self._keys)
        redis = await get_redis()
        key = self._keys.game_hash(chat_id)
        day_raw = await redis.get(
            self._keys.day_count(chat_id)
        )
        if not day_raw:
            await redis.set(
                self._keys.day_count(chat_id),
                "1",
            )
            await redis.hset(
                key,
                self._keys.field("day_count"),
                "1",
            )
            day_n = 1
        else:
            day_n = int(day_raw)
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
                if int(row.day_count or 0) < 1:
                    row.day_count = 1
                row.state = day
                row.status = day
                day_n = int(row.day_count)
        flags = self._keys.game_flags(chat_id)
        no_kill = await redis.hget(
            flags,
            self._keys.field("no_night_kill"),
        )
        davina_next = await redis.hget(
            flags,
            self._keys.field("davina_next"),
        )
        if davina_next and int(davina_next) == day_n:
            await redis.hset(
                flags,
                self._keys.field("not_send_day"),
                "1",
            )
            await redis.hdel(
                flags,
                self._keys.field("davina_next"),
            )
            await self._bridge.send_text(
                chat_id,
                self._texts.get(
                    "DavinaDayMute",
                    lang,
                    bundle="day",
                ),
            )
        # Clear previous peace/ruler at night→day
        await redis.hdel(
            flags,
            self._keys.field("peace_flag"),
            self._keys.field("ruler_ok"),
        )
        if no_kill:
            await self._bridge.send_text(
                chat_id,
                self._texts.get(
                    "NoAttakInDay",
                    lang,
                    bundle="day",
                ),
            )
        davina_mute = bool(
            await redis.hget(
                flags,
                self._keys.field("not_send_day"),
            )
        )
        duration = (
            30
            if davina_mute
            else int(self._settings.day_duration_seconds)
        )
        await self._bridge.send_text(
            chat_id,
            self._texts.get(
                "DayNumber",
                lang,
                day_n,
                bundle="day",
            ),
        )
        summary = self._texts.get(
            "MassgeFortypeSummery_day",
            lang,
            duration,
            bundle="day",
        )
        await self._bridge.send_text(chat_id, summary)
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
        await redis.hset(
            key,
            self._keys.field("timer_end"),
            str(end_at),
        )
        await redis.delete(self._keys.day_sent(chat_id))
        await redis.delete(self._keys.day_actions(chat_id))
        await redis.sadd(
            self._keys.active_day_chats(),
            str(chat_id),
        )
        await self.broadcast_day_roles(chat_id)
        # Clear one-day silence after applying
        if await redis.hget(
            flags,
            self._keys.field("not_send_day"),
        ):
            await redis.hdel(
                flags,
                self._keys.field("not_send_day"),
            )
        log_game_event(
            "day_started",
            chat_id=chat_id,
            game_id=game_id,
            phase=day,
            day_count=day_n,
        )

    async def tick_day(self, chat_id: int) -> bool:
        """True when day timer expired (never early)."""
        redis = await get_redis()
        raw = await redis.get(
            self._keys.timer_end(chat_id)
        )
        if not raw:
            return False
        return int(raw) <= int(time())

    async def broadcast_day_roles(
        self,
        chat_id: int,
    ) -> None:
        """Send day UI once per eligible living player."""
        lang = self._settings.default_lang
        redis = await get_redis()
        if await redis.hget(
            self._keys.game_flags(chat_id),
            self._keys.field("not_send_day"),
        ):
            return
        players = await self._load_players(chat_id)
        sent_key = self._keys.day_sent(chat_id)
        immediate = set(self._day_roles["immediate"])
        deferred = set(self._day_roles["deferred"])
        types = self._day_roles["target_type"]
        flags = self._keys.game_flags(chat_id)
        iced = await redis.hget(
            flags,
            self._keys.field("player_iced"),
        )
        prison = await redis.hget(
            flags,
            self._keys.field("princess_prison"),
        )
        night_n = int(
            await redis.get(
                self._keys.night_count(chat_id)
            )
            or "0"
        )
        for player in players:
            if not player.get("alive", True):
                continue
            uid = int(player["user_id"])
            if iced and str(uid) == str(iced):
                continue
            if prison and str(uid) == str(prison):
                continue
            role_id = str(player.get("role") or "")
            if (
                role_id == "role_Princess"
                and night_n <= 2
            ):
                continue
            if await redis.sismember(sent_key, str(uid)):
                continue
            if role_id not in immediate | deferred:
                continue
            if await self._already_used(chat_id, role_id):
                continue
            from app.managers.lucifer_dodge import (
                dodge_day_owner,
                send_day_dodge,
            )

            luci = await dodge_day_owner(
                self._keys,
                chat_id,
                uid,
            )
            if luci is not None:
                await send_day_dodge(
                    self._bridge,
                    self._texts,
                    chat_id,
                    luci,
                    uid,
                    role_id,
                    lang,
                    players,
                )
                await redis.sadd(sent_key, str(uid))
                continue
            await send_day_role_ui(
                self._bridge,
                self._texts,
                self._keys,
                chat_id,
                uid,
                role_id,
                str(types[role_id]),
                lang,
                players,
            )
            await redis.sadd(sent_key, str(uid))

    async def _already_used(
        self,
        chat_id: int,
        role_id: str,
    ) -> bool:
        """True if one-shot day power already spent."""
        used = {
            "role_Solh": "peace_used",
            "role_Ahangar": "silver_used",
            "role_KhabGozar": "sleep_used",
            "role_Kadkhoda": "mayor_revealed",
            "role_trouble": "trouble_used",
            "role_Ruler": "ruler_used",
            "role_davina": "davina_used",
            "role_BeladMoon": "belad_moon_used",
        }
        field = used.get(role_id)
        if not field:
            return False
        redis = await get_redis()
        return bool(
            await redis.hget(
                self._keys.game_flags(chat_id),
                self._keys.field(field),
            )
        )

    async def _load_players(
        self,
        chat_id: int,
    ) -> list[dict[str, Any]]:
        """Load enriched living/dead player list."""
        return await load_enriched_players(
            self._keys,
            chat_id,
        )
