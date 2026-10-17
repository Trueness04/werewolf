"""Village night slot wrappers for NightSteps."""

from __future__ import annotations

from typing import Any


class NightVillageChecks:
    """Mixin: knight/chemist/cow/ghost/fillers."""

    async def forest_queen_curse(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Cupid + bard reroute early."""
        from app.managers.village_extra import (
            maybe_bard_reroute,
            resolve_cupid,
        )

        await resolve_cupid(ctx)
        maybe_bard_reroute(ctx)

    async def check_knight(self, ctx: dict[str, Any]) -> None:
        """Village knight night kill."""
        from app.managers.village_night import (
            resolve_knight,
        )

        await resolve_knight(ctx)

    async def check_chemist(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Chemist poison."""
        from app.managers.village_night import (
            resolve_chemist,
        )

        await resolve_chemist(ctx)

    async def check_cow(self, ctx: dict[str, Any]) -> None:
        """Cow night gore."""
        from app.managers.village_night import resolve_cow

        await resolve_cow(ctx)

    async def check_ghost(self, ctx: dict[str, Any]) -> None:
        """Ghost peek."""
        from app.managers.village_night import (
            resolve_ghost,
        )

        await resolve_ghost(ctx)

    async def check_mouse(self, ctx: dict[str, Any]) -> None:
        """Mouse detect."""
        from app.managers.village_night import (
            resolve_mouse,
        )

        await resolve_mouse(ctx)

    async def check_augur(self, ctx: dict[str, Any]) -> None:
        """Augur missing role."""
        from app.managers.village_night import (
            resolve_augur,
        )

        await resolve_augur(ctx)

    async def check_negative(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Negative false seer."""
        from app.managers.village_night import (
            resolve_negative,
        )

        await resolve_negative(ctx)

    async def check_babr(self, ctx: dict[str, Any]) -> None:
        """Tiger night kill."""
        from app.managers.village_extra import (
            resolve_babr,
        )

        await resolve_babr(ctx)

    async def check_watermelon(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Watermelon inform."""
        from app.managers.village_extra import (
            resolve_watermelon,
        )

        await resolve_watermelon(ctx)

    async def check_bard(self, ctx: dict[str, Any]) -> None:
        """Clear bard redirect after night."""
        ctx.pop("bard_redirect", None)
        ctx.setdefault("flags_out", {})["kenyager"] = ""
