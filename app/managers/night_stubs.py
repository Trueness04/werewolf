"""Sprint-01 stub night slots (order-preserving)."""

from __future__ import annotations

from typing import Any


class NightStubs:
    """No-op / minimal slots so CheckNight order holds."""

    async def forest_queen_curse(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: DeadforestQueen empty-home."""
        _ = ctx

    async def check_harley(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: Harley (override in NightSpecialChecks)."""
        _ = ctx

    async def check_knight(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: knight (override in NightSteps)."""
        _ = ctx

    async def check_chemist(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: chemist."""
        _ = ctx

    async def check_beta_wolf(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: beta wolf."""
        _ = ctx

    async def check_babr(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: babr."""
        _ = ctx

    async def check_ice_wolf(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub; NightSpecialChecks owns logic."""
        _ = ctx

    async def check_chemist(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: chemist."""
        _ = ctx

    async def check_bomber(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Removed MF-58; no-op."""
        _ = ctx

    async def check_firefighter(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Firefighter oil / burn."""
        from app.managers.fire_resolve import (
            resolve_firefighter,
        )

        await resolve_firefighter(ctx)

    async def check_ice_queen(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Ice queen freeze / kill."""
        from app.managers.fire_resolve import (
            resolve_ice_queen,
        )

        await resolve_ice_queen(ctx)

    async def check_archer(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Archer every-other-night shot."""
        from app.managers.fire_resolve import (
            resolve_archer,
        )

        await resolve_archer(ctx)

    async def check_magento(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Magento convert or kill."""
        from app.managers.fire_extra import (
            resolve_magento,
        )

        await resolve_magento(ctx)

    async def check_chiang(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Chiang intel ping before blood reveal."""
        from app.managers.vampire_resolve import (
            resolve_chiang,
        )

        await resolve_chiang(ctx)

    async def check_vampire(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Vampire team vote convert/kill."""
        from app.managers.vampire_resolve import (
            resolve_vampire,
        )

        await resolve_vampire(ctx)

    async def lucifer_team(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: lucifer team."""
        _ = ctx

    async def check_bride(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: bride of the dead."""
        _ = ctx

    async def check_lilis(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Lilis pre/post DieFireAndIc kill."""
        from app.managers.fire_extra import (
            resolve_lilis,
            refresh_die_fire_and_ice,
        )

        refresh_die_fire_and_ice(ctx)
        await resolve_lilis(ctx)

    async def check_honey(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Set HoneyUser from action if role present."""
        for item in ctx["players"]:
            if item.get("role") != "role_Honey":
                continue
            raw = ctx["actions"].get(str(item["user_id"]))
            if raw:
                ctx["flags_out"]["honey_user"] = str(raw)

    async def check_kent(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Kent spy / post-convert day flag."""
        from app.managers.vampire_resolve import (
            resolve_kent,
        )

        await resolve_kent(ctx)

    async def check_franc(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Franc house guard selection → defense set."""
        guards: set[str] = set(ctx.get("franc_guard") or [])
        for item in ctx["players"]:
            if item.get("role") != "role_franc":
                continue
            if not item.get("alive", True):
                continue
            raw = ctx["actions"].get(str(item["user_id"]))
            if raw:
                guards.add(str(raw))
        ctx["franc_guard"] = guards

    async def check_enchanter(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub; NightSpecialChecks owns logic."""
        _ = ctx

    async def check_cow(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: cow."""
        _ = ctx

    async def check_huntsman(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Huntsman trap target for wolf defense."""
        for item in ctx["players"]:
            if item.get("role") != "role_Huntsman":
                continue
            raw = ctx["actions"].get(str(item["user_id"]))
            if raw:
                ctx["huntsman_trap"] = int(raw)

    async def check_ghost(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: ghost."""
        _ = ctx

    async def check_mouse(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: mouse."""
        _ = ctx

    async def check_white_wolf(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: white wolf solo path handled in team."""
        _ = ctx

    async def check_augur(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: augur."""
        _ = ctx

    async def check_phoenix(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Prefer: PhoenixHealer on night 2/4."""
        night = int(ctx.get("night_no") or 0)
        if night not in {2, 4}:
            return
        heals: set[int] = set(ctx.get("phoenix_heals") or [])
        for item in ctx["players"]:
            if item.get("role") != "role_Phoenix":
                continue
            if not item.get("alive", True):
                continue
            raw = ctx["actions"].get(str(item["user_id"]))
            if raw:
                heals.add(int(raw))
                ctx["flags_out"]["phoenix_healer"] = str(
                    raw
                )
        ctx["phoenix_heals"] = heals

    async def check_thief(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: thief."""
        _ = ctx

    async def check_negative(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: negative."""
        _ = ctx

    async def check_sorcerer(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: sorcerer."""
        _ = ctx

    async def check_dynamite(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: dynamite."""
        _ = ctx

    async def check_watermelon(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: watermelon."""
        _ = ctx

    async def check_bard(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Stub: bard / khenyager."""
        _ = ctx
