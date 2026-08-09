"""Resolve night actions in fixed CheckNight order."""

from __future__ import annotations

import json
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
from app.managers.night_village import player
from app.managers.text_managers import TextManager
from importlib import import_module

_Registry = import_module(
    "app.class.roles.registry"
).RoleRegistry


class NightResolver:
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
        if done:
            return await self._wait_interrupt(chat_id, lang)
        log = get_logger()
        log_game_event(
            "night_resolve_start",
            chat_id=chat_id,
        )
        ctx = await build_night_context(chat_id, self._keys)
        for step in self._order:
            log.debug(
                "night_step chat={c} step={s}",
                c=chat_id,
                s=step,
            )
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
        mapping = {
            self._keys.field(str(k)): str(v)
            for k, v in out.items()
            if str(v) != ""
        }
        if mapping:
            await redis.hset(flags, mapping=mapping)

    async def _apply_deaths(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Persist deaths and role conversions."""
        redis = await get_redis()
        chat_id = int(ctx["chat_id"])
        key = self._keys.game_hash(chat_id)
        game_id = int(
            await redis.hget(
                key,
                self._keys.field("game_id"),
            )
            or "0"
        )
        async with session_scope() as session:
            for prow in ctx["players"]:
                uid = int(prow["user_id"])
                stmt = select(PlayerRow).where(
                    PlayerRow.game_id == game_id,
                    PlayerRow.user_id == uid,
                )
                row = (
                    await session.execute(stmt)
                ).scalar_one_or_none()
                if row is None:
                    continue
                row.role = prow.get("role")
                row.team = prow.get("team")
                was_dead = not bool(prow.get("alive", True))
                dead = was_dead or uid in ctx["deaths"]
                row.alive = not dead
                row.state = "dead" if dead else "alive"
                # Alpha death unlocks forest-queen bite.
                if dead and not was_dead:
                    if str(prow.get("role")) == (
                        "role_Alpha"
                    ):
                        ctx.setdefault("flags_out", {})[
                            "alpha_dead"
                        ] = "1"
                await redis.set(
                    self._keys.player_state(uid),
                    row.state,
                )
                await redis.set(
                    self._keys.player_role(uid),
                    str(prow.get("role") or ""),
                )
        await redis.set(
            self._keys.game_roles(chat_id),
            json.dumps(ctx["roles"]),
        )

    async def _announce(
        self,
        chat_id: int,
        lang: str,
        ctx: dict[str, Any],
    ) -> None:
        """Send night result messages to group."""
        for msg in ctx["messages"]:
            text = self._texts.get(
                str(msg),
                lang,
                bundle="results",
            )
            await self._bridge.send_text(chat_id, text)
        if not ctx["deaths"]:
            text = self._texts.get(
                "NoAttakInDay",
                lang,
                bundle="results",
            )
            await self._bridge.send_text(chat_id, text)
            return
        for uid in ctx["deaths"]:
            prow = player(ctx, int(uid))
            from app.managers.player_format import (
                mention_html,
            )

            raw_name = str(prow["fullname"]) if prow else str(uid)
            name = mention_html(int(uid), raw_name)
            role_id = str(prow.get("role")) if prow else ""
            role_name = ""
            if role_id:
                role_name = self._texts.get(
                    str(
                        self._registry.definition(role_id)[
                            "message_keys"
                        ]["name"]
                    ),
                    lang,
                    bundle="roles",
                )
            text = self._texts.get(
                "DefaultKilled",
                lang,
                name,
                role_name,
                bundle="results",
            )
            await self._bridge.send_text(chat_id, text)
            await self._bridge.send_text(
                int(uid),
                self._texts.get(
                    "you_died_night",
                    lang,
                    role_name or name,
                    bundle="results",
                ),
            )

    async def _to_day(
        self,
        chat_id: int,
        lang: str,
    ) -> None:
        """Enter day without bumping day_count."""
        _ = lang
        redis = await get_redis()
        flags = self._keys.game_flags(chat_id)
        from app.managers.day_manager import DayManager

        await DayManager(self._bridge).start_day(chat_id)
        await redis.hdel(
            flags,
            self._keys.field("no_night_kill"),
            self._keys.field("hunter_kill"),
            self._keys.field("send_wolf_cube_dead"),
            self._keys.field("royce_selectd2"),
            self._keys.field("check_night_done"),
        )
