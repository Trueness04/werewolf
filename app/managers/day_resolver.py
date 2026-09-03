"""End-of-day deferred resolution then vote."""

from __future__ import annotations

import json
from typing import Any

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import DAY_ORDER
from app.config.settings import Settings, get_settings
from app.managers.chat_bridge import ChatBridge
from app.managers.game_event import log_game_event
from app.managers.json_loader import load_json
from app.managers.logger_manager import get_logger
from app.managers.text_managers import TextManager
from importlib import import_module

from app.managers.day_steps import DaySteps

_Registry = import_module(
    "app.class.roles.registry"
).RoleRegistry


class DayResolver(DaySteps):
    """Resolve deferred day actions in fixed order."""

    def __init__(
        self,
        bridge: ChatBridge,
        keys: RedisKeySpace | None = None,
        texts: TextManager | None = None,
        settings: Settings | None = None,
        vote_starter: Any | None = None,
    ) -> None:
        self._bridge = bridge
        self._keys = keys or RedisKeySpace()
        self._texts = texts or TextManager()
        self._settings = settings or get_settings()
        self._registry = _Registry()
        self._order = [
            str(item)
            for item in load_json(DAY_ORDER)["order"]
        ]
        self._vote_starter = vote_starter

    def set_vote_starter(self, starter: Any) -> None:
        """Inject vote_manager.start_vote callable."""
        self._vote_starter = starter

    async def resolve(self, chat_id: int) -> None:
        """Run end-of-day pipeline then open vote."""
        log = get_logger()
        lang = self._settings.default_lang
        log_game_event(
            "day_resolve_start",
            chat_id=chat_id,
        )
        redis = await get_redis()
        await redis.srem(
            self._keys.active_day_chats(),
            str(chat_id),
        )
        ctx = await self._context(chat_id)
        interrupt = False
        for step in self._order:
            log.debug(
                "day_step chat={c} step={s}",
                c=chat_id,
                s=step,
            )
            if step == "sheriff_interrupt_check":
                if ctx.get("sheriff_interrupt"):
                    interrupt = True
                    break
                continue
            handler = getattr(self, f"_step_{step}", None)
            if handler is None:
                continue
            await handler(ctx, lang)
        if interrupt:
            log_game_event(
                "day_sheriff_interrupt",
                chat_id=chat_id,
            )
            from time import time

            from app.config.paths import ROOT
            from app.managers.json_loader import load_json

            secs = int(
                load_json(
                    ROOT
                    / "data"
                    / "config"
                    / "field_chances.json"
                )["sheriff_shot_seconds"]
            )
            await redis.set(
                self._keys.timer_end(chat_id),
                str(int(time()) + secs),
            )
            await redis.sadd(
                self._keys.active_day_chats(),
                str(chat_id),
            )
            await redis.hset(
                self._keys.game_flags(chat_id),
                mapping={
                    self._keys.field(
                        "hunter_kill_source"
                    ): "day",
                    self._keys.field("hunter_kill"): "1",
                },
            )
            pending = await redis.hget(
                self._keys.game_flags(chat_id),
                self._keys.field(
                    "sheriff_shot_pending"
                ),
            )
            if pending:
                from app.managers.lynch_resolver import (
                    LynchResolver,
                )

                lynch = LynchResolver(self._bridge)
                await lynch.open_sheriff_shot(
                    chat_id,
                    int(pending),
                )
            return
        if self._vote_starter is None:
            return
        await self._vote_starter(chat_id)

    async def _context(
        self,
        chat_id: int,
    ) -> dict[str, Any]:
        """Build resolver context from Redis."""
        redis = await get_redis()
        players = json.loads(
            await redis.get(
                self._keys.game_players(chat_id)
            )
            or "[]"
        )
        roles = json.loads(
            await redis.get(
                self._keys.game_roles(chat_id)
            )
            or "{}"
        )
        actions = await redis.hgetall(
            self._keys.day_actions(chat_id)
        )
        return {
            "chat_id": chat_id,
            "players": players,
            "roles": roles,
            "actions": actions,
            "sheriff_interrupt": False,
            "flags_out": {},
        }

