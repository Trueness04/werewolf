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

_Registry = import_module(
    "app.class.roles.registry"
).RoleRegistry


class DayResolver:
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
        }

    async def _step_gunner(
        self,
        ctx: dict[str, Any],
        lang: str,
    ) -> None:
        """Apply gunner deferred shot if present."""
        redis = await get_redis()
        chat_id = int(ctx["chat_id"])
        for uid_s, role_id in ctx["roles"].items():
            if role_id != "role_tofangdar":
                continue
            raw = ctx["actions"].get(uid_s)
            if not raw:
                return
            target = int(raw)
            target_role = ctx["roles"].get(str(target))
            flags = self._keys.game_flags(chat_id)
            bullets = int(
                await redis.hget(
                    flags,
                    self._keys.field("gunner_bullets"),
                )
                or "2"
            )
            if bullets <= 0:
                return
            await redis.hset(
                flags,
                self._keys.field("gunner_bullets"),
                str(bullets - 1),
            )
            if target_role == "role_rishSefid":
                ctx["roles"][uid_s] = "role_villager"
                await redis.set(
                    self._keys.game_roles(chat_id),
                    json.dumps(ctx["roles"]),
                )
                await redis.set(
                    self._keys.player_role(int(uid_s)),
                    "role_villager",
                )
                return
            if target_role == "role_kalantar":
                ctx["sheriff_interrupt"] = True
                await redis.hset(
                    flags,
                    self._keys.field(
                        "sheriff_shot_pending"
                    ),
                    str(target),
                )
                return
            await redis.set(
                self._keys.player_state(target),
                "dead",
            )
            log_game_event(
                "gunner_kill",
                chat_id=chat_id,
                target=target,
            )

    async def _step_spy(
        self,
        ctx: dict[str, Any],
        lang: str,
    ) -> None:
        """Private spy check for deferred target."""
        danger_teams = {"wolf", "cult", "solo"}
        for uid_s, role_id in ctx["roles"].items():
            if role_id != "role_Spy":
                continue
            raw = ctx["actions"].get(uid_s)
            if not raw:
                return
            target = str(raw)
            t_role = ctx["roles"].get(target)
            team = ""
            if t_role:
                team = str(
                    self._registry.definition(t_role)[
                        "team"
                    ]
                )
            key = (
                "spy_danger"
                if team in danger_teams
                else "spy_safe"
            )
            await self._bridge.send_text(
                int(uid_s),
                self._texts.get(
                    key,
                    lang,
                    bundle="day",
                ),
            )

    async def _step_black_knight(
        self,
        ctx: dict[str, Any],
        lang: str,
    ) -> None:
        """Mighty stub placeholder."""
        _ = (ctx, lang)

    async def _step_dynamite(
        self,
        ctx: dict[str, Any],
        lang: str,
    ) -> None:
        """Mighty stub placeholder."""
        _ = (ctx, lang)

    async def _step_detective(
        self,
        ctx: dict[str, Any],
        lang: str,
    ) -> None:
        """Detective stub (day inquire later)."""
        _ = (ctx, lang)

    async def _step_princess(
        self,
        ctx: dict[str, Any],
        lang: str,
    ) -> None:
        """Princess stub."""
        _ = (ctx, lang)

    async def _step_diane(
        self,
        ctx: dict[str, Any],
        lang: str,
    ) -> None:
        """Diane +4 day mark → direct black win."""
        _ = lang
        redis = await get_redis()
        chat_id = int(ctx["chat_id"])
        flags = self._keys.game_flags(chat_id)
        due = await redis.hget(
            flags,
            self._keys.field("diane_due_day"),
        )
        target = await redis.hget(
            flags,
            self._keys.field("diane_target"),
        )
        if not due or not target:
            # Arm from day action if diane picked.
            raw = ctx.get("actions", {}).get("diane")
            if not raw:
                for uid, val in (
                    ctx.get("actions") or {}
                ).items():
                    role = (
                        ctx.get("roles") or {}
                    ).get(str(uid))
                    if role == "role_dian":
                        raw = val
                        break
            if raw:
                day_n = int(
                    await redis.get(
                        self._keys.day_count(chat_id)
                    )
                    or "1"
                )
                await redis.hset(
                    flags,
                    mapping={
                        self._keys.field(
                            "diane_target"
                        ): str(raw),
                        self._keys.field(
                            "diane_due_day"
                        ): str(day_n + 4),
                    },
                )
            return
        day_n = int(
            await redis.get(
                self._keys.day_count(chat_id)
            )
            or "1"
        )
        if day_n < int(due):
            return
        state = await redis.get(
            self._keys.player_state(int(target))
        )
        if state == "dead":
            return
        from app.managers.end_game_manager import (
            EndGameManager,
        )

        await EndGameManager(self._bridge).end(
            chat_id,
            "black",
        )

    async def _step_botanist(
        self,
        ctx: dict[str, Any],
        lang: str,
    ) -> None:
        """Botanist day cure clears gas flags."""
        from app.managers.bittan_check import (
            clear_gas_flag,
        )

        chat_id = int(ctx["chat_id"])
        actions = ctx.get("actions") or {}
        roles = ctx.get("roles") or {}
        for uid, target in actions.items():
            if roles.get(str(uid)) != "role_Botanist":
                continue
            try:
                tid = int(target)
            except (TypeError, ValueError):
                continue
            if await clear_gas_flag(chat_id, tid):
                await self._bridge.send_text(
                    tid,
                    self._texts.get(
                        "BotanistCured",
                        lang,
                        bundle="results",
                    ),
                )

    async def _step_vampire_count(
        self,
        ctx: dict[str, Any],
        lang: str,
    ) -> None:
        """Vampire count stub."""
        _ = (ctx, lang)
