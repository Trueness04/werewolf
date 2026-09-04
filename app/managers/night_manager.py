"""First night flow (SendNightRole + timer)."""

from __future__ import annotations

import asyncio
import json
from time import time
from typing import Any

from sqlalchemy import select

from app.managers.logger_manager import get_logger

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import GAME_PHASES
from app.config.settings import Settings, get_settings
from app.database.models.game import GameRow
from app.database.session import session_scope
from app.managers.chat_bridge import ChatBridge
from app.managers.game_event import log_game_event
from app.managers.game_state_manager import (
    GameStateManager,
)
from app.managers.json_loader import load_json
from app.managers.night_dm import NightDmSender
from app.managers.text_managers import TextManager
from importlib import import_module

_Registry = import_module(
    "app.class.roles.registry"
).RoleRegistry

class NightManager:
    """Start first night and deliver role DMs."""

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
        self._dm = NightDmSender(
            bridge,
            self._keys,
            self._texts,
        )

    async def start_first_night(
        self,
        chat_id: int,
    ) -> None:
        """Init counters then start first night.

        Doc: day_count=1, night_count=0 at game start.
        """
        redis = await get_redis()
        key = self._keys.game_hash(chat_id)
        await redis.set(self._keys.day_count(chat_id), "1")
        await redis.set(
            self._keys.night_count(chat_id),
            "0",
        )
        await redis.hset(
            key,
            mapping={
                self._keys.field("day_count"): "1",
                self._keys.field("night_count"): "0",
            },
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
                row.day_count = 1
                row.night_count = 0
        await redis.hset(
            self._keys.game_flags(chat_id),
            self._keys.field("gunner_bullets"),
            "2",
        )
        await self.start_night(chat_id)

    async def start_night(self, chat_id: int) -> None:
        """Phase night + DM roles + arm timer."""
        log = get_logger()
        log.info(
            "start_night_ENTER chat={c}",
            c=chat_id,
        )
        redis = await get_redis()
        # Lock: prevent duplicate start_night calls
        lock = await redis.set(
            f"night_lock:{chat_id}",
            "1",
            nx=True,
            ex=30,
        )
        if not lock:
            log.warning(
                "start_night_LOCKED chat={c} SKIP",
                c=chat_id,
            )
            return
        log.info(
            "start_night_LOCKED chat={c}",
            c=chat_id,
        )
        lang = self._settings.default_lang
        phases = load_json(GAME_PHASES)
        night = str(phases["redis_phases"]["night"])
        await self._state.set_phase(chat_id, night)
        redis = await get_redis()
        key = self._keys.game_hash(chat_id)
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
                row.state = night
                row.status = night
        flags = self._keys.game_flags(chat_id)
        sleep = await redis.hget(
            flags,
            self._keys.field("sleep_next_night"),
        )
        blood_pending = await redis.hget(
            flags,
            self._keys.field("blood_moon_next_night"),
        )
        blood_sched = await redis.hget(
            flags,
            self._keys.field("blood_moon_night"),
        )
        night_n = int(
            await redis.get(self._keys.night_count(chat_id))
            or "0"
        )
        # G17: blood moon overrides sleep for vamp hunt
        blood_tonight = bool(blood_pending) or (
            blood_sched and str(blood_sched) == str(night_n)
        )
        if sleep and not blood_tonight:
            duration = 0
            await redis.hdel(
                flags,
                self._keys.field("sleep_next_night"),
            )
        else:
            if sleep and blood_tonight:
                await redis.hdel(
                    flags,
                    self._keys.field("sleep_next_night"),
                )
            duration = int(
                self._settings.night_duration_seconds
            )
        silver = await redis.hget(
            flags,
            self._keys.field("silver_next_night"),
        )
        if silver:
            await redis.hdel(
                flags,
                self._keys.field("silver_next_night"),
            )
            await redis.hset(
                flags,
                self._keys.field("silver_active"),
                "1",
            )
        else:
            await redis.hdel(
                flags,
                self._keys.field("silver_active"),
            )
        mast_next = await redis.hget(
            flags,
            self._keys.field("mast_block_next"),
        )
        if mast_next:
            await redis.hdel(
                flags,
                self._keys.field("mast_block_next"),
            )
            await redis.hset(
                flags,
                self._keys.field("mast_block"),
                "1",
            )
        else:
            await redis.hdel(
                flags,
                self._keys.field("mast_block"),
            )
        summary = self._texts.get(
            "MassgeFortypeSummery_night",
            lang,
            duration,
            bundle="night",
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
        await redis.delete(
            self._keys.night_actions(chat_id)
        )
        players = await self._load_players(chat_id)
        from app.managers.bloodmoon import (
            activate_blood_moon_night,
        )

        await activate_blood_moon_night(
            self._bridge,
            self._keys,
            self._texts,
            chat_id,
            lang,
            night_n,
            players,
        )
        if not sleep or blood_tonight:
            await asyncio.gather(
                *[
                    self._dm.send_role_dm(
                        chat_id,
                        p,
                        lang,
                        players,
                    )
                    for p in players
                    if bool(p.get("alive", True))
                ]
            )
            pending = await redis.hget(
                flags,
                self._keys.field("village_links_pending"),
            )
            if pending:
                roles = {
                    str(p["user_id"]): str(p.get("role"))
                    for p in players
                }
                from app.managers.village_links import (
                    notify_mason_links,
                    notify_nazer_seer,
                )

                await notify_mason_links(
                    chat_id,
                    players,
                    roles,
                    bridge=self._bridge,
                    texts=self._texts,
                    lang=lang,
                )
                await notify_nazer_seer(
                    chat_id,
                    players,
                    roles,
                    bridge=self._bridge,
                    texts=self._texts,
                    lang=lang,
                )
                await redis.hdel(
                    flags,
                    self._keys.field(
                        "village_links_pending"
                    ),
                )
        end_at = int(time()) + max(duration, 0)
        await redis.set(
            self._keys.timer_end(chat_id),
            str(end_at),
        )
        await redis.hset(
            key,
            self._keys.field("timer_end"),
            str(end_at),
        )
        await redis.sadd(
            self._keys.active_night_chats(),
            str(chat_id),
        )
        log_game_event(
            "night_started",
            chat_id=chat_id,
            game_id=game_id,
            phase=night,
        )

    async def tick_night(self, chat_id: int) -> bool:
        """Return True if night timer expired."""
        redis = await get_redis()
        raw = await redis.get(
            self._keys.timer_end(chat_id)
        )
        if not raw:
            return False
        return int(raw) <= int(time())

    async def _load_players(
        self,
        chat_id: int,
    ) -> list[dict[str, Any]]:
        """Load players list from Redis."""
        redis = await get_redis()
        raw = await redis.get(
            self._keys.game_players(chat_id)
        )
        roles_raw = await redis.get(
            self._keys.game_roles(chat_id)
        )
        players = json.loads(raw) if raw else []
        roles = json.loads(roles_raw) if roles_raw else {}
        out: list[dict[str, Any]] = []
        for item in players:
            uid = str(item["user_id"])
            role_id = roles.get(uid)
            state = await redis.get(
                self._keys.player_state(int(uid))
            )
            alive = state != "dead"
            info = (
                self._registry.definition(role_id)
                if role_id
                else {}
            )
            out.append(
                {
                    **item,
                    "role": role_id,
                    "team": info.get("team"),
                    "alive": alive,
                }
            )
        return out
