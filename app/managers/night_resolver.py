"""Resolve night actions in fixed CheckNight order."""

from __future__ import annotations

from time import time
from typing import Any

from sqlalchemy import select

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import NIGHT_ORDER
from app.config.settings import Settings, get_settings
from app.database.models.player import PlayerRow
from app.database.session import session_scope
from app.managers.chat_bridge import ChatBridge
from app.managers.game_event import log_game_event
from app.managers.game_state_manager import (
    GameStateManager,
)
from app.managers.json_loader import load_json
from app.managers.logger_manager import get_logger
from app.managers.night_context import build_night_context
from app.managers.night_steps import NightSteps
from app.managers.night_resolve_mixin import (
    NightResolveMixin,
)
from app.managers.text_managers import TextManager
from importlib import import_module

_Registry = import_module(
    "app.class.roles.registry"
).RoleRegistry


class NightResolver(
    NightResolveMixin,
):
    """Ordered night resolution pipeline."""

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
        self._order = [
            str(item)
            for item in load_json(NIGHT_ORDER)["order"]
        ]
        self._steps = NightSteps(
            bridge,
            self._texts,
            self._settings.default_lang,
        )

    async def resolve(self, chat_id: int) -> bool:
        """Run CheckNight. True = day deferred."""
        lang = self._settings.default_lang
        redis = await get_redis()
        flags = self._keys.game_flags(chat_id)
        done = await redis.hget(
            flags,
            self._keys.field("check_night_done"),
        )
        L = get_logger()
        if done:
            L.debug("night_resolve SKIP chat={} (done=1)", chat_id)
            return await self._wait_interrupt(chat_id, lang)
        log_game_event(
            "night_resolve_start",
            chat_id=chat_id,
        )
        ctx = await build_night_context(chat_id, self._keys)
        from app.managers.bloodmoon import burn_if_blood_moon

        for step in self._order:
            L.debug(
                "night_step chat={c} step={s}",
                c=chat_id,
                s=step,
            )
            if burn_if_blood_moon(ctx, step):
                continue
            handler = getattr(self._steps, step, None)
            if handler is None:
                continue
            await handler(ctx)
            if ctx.get("stop_night") and str(step).startswith(
                "interrupt_"
            ):
                break
        await self._persist_flags(ctx)
        await self._apply_deaths(ctx)
        await self._announce(chat_id, lang, ctx)
        if not ctx["deaths"]:
            await redis.hset(
                flags,
                self._keys.field("no_night_kill"),
                "1",
            )
        if ctx.get("stop_night") or ctx.get("defer_day"):
            L.debug(
                "night_held chat={c}"
                " stop={s} defer={d}",
                c=chat_id,
                s=ctx.get("stop_night"),
                d=ctx.get("defer_day"),
            )
            await redis.hset(
                flags,
                self._keys.field("check_night_done"),
                "1",
            )
            await self._hold_night(chat_id, ctx)
            await self._maybe_open_sheriff(chat_id, ctx)
            return True
        await redis.hdel(
            flags,
            self._keys.field("check_night_done"),
        )
        await self._to_day(chat_id, lang)
        return False

    async def _wait_interrupt(
        self,
        chat_id: int,
        lang: str,
    ) -> bool:
        """After first resolve, wait for interrupt clear."""
        redis = await get_redis()
        flags = self._keys.game_flags(chat_id)
        hunter = await redis.hget(
            flags,
            self._keys.field("hunter_kill"),
        )
        royce = await redis.hget(
            flags,
            self._keys.field("royce_selectd2"),
        )
        cub = await redis.hget(
            flags,
            self._keys.field("send_wolf_cube_dead"),
        )
        if cub and not hunter and not royce:
            await redis.hdel(
                flags,
                self._keys.field("check_night_done"),
                self._keys.field("wolf_cube_dead"),
                self._keys.field("send_wolf_cube_dead"),
            )
            return await self.resolve(chat_id)
        if hunter or royce:
            await self._hold_night(
                chat_id,
                {"extend_seconds": 45},
            )
            return True
        await redis.hdel(
            flags,
            self._keys.field("check_night_done"),
        )
        await self._to_day(chat_id, lang)
        return False

    async def _maybe_open_sheriff(
        self,
        chat_id: int,
        ctx: dict[str, Any],
    ) -> None:
        """Open sheriff shot keyboard on HunterKill."""
        target = (ctx.get("flags_out") or {}).get(
            "hunter_kill"
        )
        if not target:
            return
        from app.managers.lynch_resolver import (
            LynchResolver,
        )

        redis = await get_redis()
        await redis.hset(
            self._keys.game_flags(chat_id),
            self._keys.field("hunter_kill_source"),
            "night",
        )
        await LynchResolver(self._bridge).open_sheriff_shot(
            chat_id,
            int(target),
        )

    async def _hold_night(
        self,
        chat_id: int,
        ctx: dict[str, Any],
    ) -> None:
        """Extend timer and keep chat in night set."""
        redis = await get_redis()
        secs = int(ctx.get("extend_seconds") or 45)
        end_at = int(time()) + secs
        await redis.set(
            self._keys.timer_end(chat_id),
            str(end_at),
        )
        await redis.hset(
            self._keys.game_hash(chat_id),
            self._keys.field("timer_end"),
            str(end_at),
        )
        await redis.sadd(
            self._keys.active_night_chats(),
            str(chat_id),
        )
        log_game_event(
            "night_interrupt",
            chat_id=chat_id,
            seconds=secs,
        )

    async def _persist_flags(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Write night-produced flags to Redis."""
        out = ctx.get("flags_out") or {}
        if not out:
            return
        redis = await get_redis()
        flags = self._keys.game_flags(int(ctx["chat_id"]))
        mapping = {}
        to_del: list[str] = []
        for k, v in out.items():
            field = self._keys.field(str(k))
            if str(v) == "":
                to_del.append(field)
            else:
                mapping[field] = str(v)
        if mapping:
            await redis.hset(flags, mapping=mapping)
        if to_del:
            await redis.hdel(flags, *to_del)
