"""05e night slot wrappers (bride/lucifer/dynamite/…)."""

from __future__ import annotations

from typing import Any


class NightSpecialChecks:
    """Mixin for joker/harley/black/lucifer."""

    async def check_harley(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Harley night-2 free book bump."""
        from app.managers.joker_books import (
            resolve_harley_night2,
        )

        await resolve_harley_night2(ctx)

    async def check_bomber(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Removed MF-58; no-op if still ordered."""
        _ = ctx

    async def lucifer_team(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Night0 team lock / night≥1 deceive."""
        from app.managers.special_teams import (
            resolve_lucifer_team,
        )

        await resolve_lucifer_team(ctx)

    async def check_bride(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Bride of the dead night kill."""
        from app.managers.special_teams import (
            resolve_bride,
        )

        await resolve_bride(ctx)

    async def check_dynamite(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Dynamite night part search."""
        from app.managers.special_teams import (
            resolve_dynamite_night,
        )

        await resolve_dynamite_night(ctx)


    async def check_ice_wolf(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Freeze target; skip if same as ice_prev."""
        prev = str(
            ctx.get("ice_prev")
            or (ctx.get("flags") or {}).get("ice_prev")
            or ""
        )
        for item in ctx["players"]:
            if item.get("role") != "role_iceWolf":
                continue
            if not item.get("alive", True):
                continue
            raw = ctx["actions"].get(str(item["user_id"]))
            if not raw:
                continue
            target = str(raw)
            if target == prev:
                continue
            ctx["flags_out"]["player_iced"] = target
            ctx["flags_out"]["ice_prev"] = target

    async def check_enchanter(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Mark target and persist enchanter_list."""
        from app.managers.enchanter_list import (
            append_uid,
            dumps,
        )

        for item in ctx["players"]:
            if item.get("role") != "role_enchanter":
                continue
            if not item.get("alive", True):
                continue
            raw = ctx["actions"].get(str(item["user_id"]))
            if not raw:
                continue
            marked = str(raw)
            ctx["enchanter_mark"] = marked
            ctx["flags_out"]["enchanter_mark"] = marked
            cur = [
                str(x)
                for x in (ctx.get("enchanter_list") or [])
            ]
            cur = append_uid(cur, marked)
            ctx["enchanter_list"] = cur
            ctx["flags_out"]["enchanter_list"] = dumps(
                cur
            )


    async def check_white_wolf(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """White wolf guard / alone convert."""
        from app.managers.wolf_specials import (
            resolve_white_wolf,
        )

        await resolve_white_wolf(ctx)

    async def check_honey(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Honey mark with hunter resist."""
        from app.managers.wolf_specials import (
            resolve_honey,
        )

        await resolve_honey(ctx)

    async def check_sorcerer(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """WolfJadogar night peek."""
        from app.managers.wolf_specials import (
            resolve_sorcerer,
        )

        await resolve_sorcerer(ctx)

    async def check_beta_wolf(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Beta nightly non-wolf mask."""
        from app.managers.wolf_specials import (
            resolve_beta_wolf,
        )

        await resolve_beta_wolf(ctx)

    async def check_thief(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Dozd role-steal mark / swap."""
        from app.managers.wolf_specials import (
            resolve_thief,
        )

        await resolve_thief(ctx)

    async def check_franc(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Franc guard or kill mode."""
        from app.managers.cult_side_effects import (
            resolve_franc,
        )

        await resolve_franc(ctx)

