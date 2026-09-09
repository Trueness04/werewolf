"""Death/cleanup steps mixin for NightSteps."""

from __future__ import annotations

from typing import Any


class NightStepsDeaths:
    """Mixin: final deaths + night cleanup (uses self attrs)."""

    async def final_deaths(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Collect leftover kills + cult death effects."""
        causes = (
            ("wolf_target", "wolf"),
            ("sk_target", "sk"),
        )
        for key, cause in causes:
            target = ctx.get(key)
            if target is None:
                continue
            uid = int(target)
            ctx["deaths"].add(uid)
            ctx.setdefault(
                "death_cause",
                {},
            )[uid] = cause
        self._v.follow_natasha_death(ctx)
        self._v.convert_wild_child(ctx)
        self._v.promote_apprentice(ctx)
        from app.managers.cult_side_effects import (
            apply_cult_deaths,
        )

        apply_cult_deaths(ctx)
        from app.managers.special_resolve import (
            convert_hamzad,
        )
        from app.managers.village_links import (
            follow_lover_deaths,
        )

        convert_hamzad(ctx)
        follow_lover_deaths(ctx)
        from app.managers.fire_extra import (
            refresh_die_fire_and_ice,
        )
        from app.managers.vampire_resolve import (
            notify_hilda_sk_dead,
        )

        refresh_die_fire_and_ice(ctx)
        notify_hilda_sk_dead(ctx)
        from app.managers.special_teams import (
            follow_black_knight_death,
        )

        follow_black_knight_death(ctx)
        for p in ctx["players"]:
            if p.get("role") != "role_Bloodthirsty":
                continue
            uid = int(p["user_id"])
            if uid not in ctx["deaths"]:
                continue
            ctx["flags_out"]["dead_bloodthirsty"] = "1"
            ctx["flags_out"]["vampire_convert"] = "20"
            ctx["messages"].append("DeadBloodthirsty")

    async def night_cleanup(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Clear ephemeral home/angel defense keys."""
        from app.managers.darneshan_resolve import (
            burn_mark_if_target_dead,
        )

        burn_mark_if_target_dead(ctx)
        if ctx.get("blood_moon_active"):
            ctx["flags_out"]["blood_moon_active"] = ""
            ctx["flags_out"]["blood_moon_night"] = ""
            ctx["flags_out"]["blood_moon_next_night"] = ""
        ctx["protected"] = None
        ctx["franc_guard"] = set()
        ctx["phoenix_heals"] = set()
        ctx["huntsman_trap"] = None
