"""DayResolver step mixins (sprint 05/07)."""

from __future__ import annotations

import json
from typing import Any

from app.cache.redis_client import get_redis
from app.managers.game_event import log_game_event


class DaySteps:
    """Deferred day action handlers."""

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
        """Spy danger yes/no."""
        from app.managers.day_specials import step_spy

        await step_spy(
            ctx,
            lang,
            bridge=self._bridge,
            texts=self._texts,
        )

    async def _step_black_knight(
        self,
        ctx: dict[str, Any],
        lang: str,
    ) -> None:
        """Black knight day kill."""
        _ = lang
        from app.managers.special_resolve import (
            resolve_black_knight_day,
        )

        await resolve_black_knight_day(ctx)

    async def _step_dynamite(
        self,
        ctx: dict[str, Any],
        lang: str,
    ) -> None:
        """Dynamite piece search."""
        _ = lang
        from app.managers.special_resolve import (
            resolve_dynamite_find,
        )

        await resolve_dynamite_find(ctx)

    async def _step_detective(
        self,
        ctx: dict[str, Any],
        lang: str,
    ) -> None:
        """Detective day snoop."""
        from app.managers.day_specials import (
            step_detective,
        )

        await step_detective(
            ctx,
            lang,
            bridge=self._bridge,
            keys=self._keys,
            texts=self._texts,
            registry=self._registry,
        )

    async def _step_princess(
        self,
        ctx: dict[str, Any],
        lang: str,
    ) -> None:
        """Princess prison after night > 2."""
        from app.managers.day_specials import (
            step_princess,
        )

        await step_princess(
            ctx,
            lang,
            keys=self._keys,
        )

    async def _step_diane(
        self,
        ctx: dict[str, Any],
        lang: str,
    ) -> None:
        """Diane +4 day mark → direct black win."""
        from app.managers.day_specials import step_diane

        await step_diane(
            ctx,
            lang,
            bridge=self._bridge,
            keys=self._keys,
            texts=self._texts,
        )

    async def _step_botanist(
        self,
        ctx: dict[str, Any],
        lang: str,
    ) -> None:
        """Botanist day cure clears gas flags."""
        from app.managers.day_specials import (
            step_botanist,
        )

        await step_botanist(
            ctx,
            lang,
            bridge=self._bridge,
            keys=self._keys,
            texts=self._texts,
        )

    async def _step_vampire_count(
        self,
        ctx: dict[str, Any],
        lang: str,
    ) -> None:
        """Kent day kill when vampires gone."""
        from app.managers.vampire_day import (
            resolve_kent_day,
        )

        await resolve_kent_day(
            ctx,
            lang,
            bridge=self._bridge,
            keys=self._keys,
            texts=self._texts,
        )
