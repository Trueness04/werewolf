"""Individual night resolution step helpers."""

from __future__ import annotations

from typing import Any

from app.config.paths import ROOT
from app.managers.chat_bridge import ChatBridge
from app.managers.json_loader import load_json
from app.managers.night_attack import (
    resolve_killer,
    resolve_wolf_team,
)
from app.managers.night_stubs import NightStubs
from app.managers.night_village import NightVillage
from app.managers.night_village_checks import (
    NightVillageChecks,
)
from app.managers.night_special_checks import (
    NightSpecialChecks,
)
from app.managers.text_managers import TextManager

_CHANCES = ROOT / "data" / "config" / "field_chances.json"


class NightSteps(
    NightSpecialChecks,
    NightVillageChecks,
    NightStubs,
):
    """Stateful helpers used by NightResolver."""

    def __init__(
        self,
        bridge: ChatBridge,
        texts: TextManager,
        lang: str,
    ) -> None:
        self._bridge = bridge
        self._texts = texts
        self._lang = lang
        self._v = NightVillage(bridge, texts, lang)

    async def check_joker(self, ctx: dict[str, Any]) -> None:
        """Joker/Harley search for hidden books."""
        from app.managers.joker_books import (
            resolve_joker_search,
        )

        await resolve_joker_search(
            ctx,
            self._bridge,
            self._texts,
            self._lang,
        )

    async def wolf_team(self, ctx: dict[str, Any]) -> None:
        """Full WolfTeam vote + defense + bite/eat."""
        from app.managers.bloodmoon import burn_if_blood_moon

        if burn_if_blood_moon(ctx, "wolf_team"):
            return
        await resolve_wolf_team(ctx)

    async def interrupt_cub(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Cub death: +45s, unlock wolves, stop night."""
        pending = ctx.get("wolf_cube_pending")
        already = ctx.get("send_wolf_cube_dead")
        if not pending or already:
            return
        secs = int(load_json(_CHANCES)["cub_extend_seconds"])
        ctx["stop_night"] = True
        ctx["extend_seconds"] = secs
        ctx["flags_out"]["send_wolf_cube_dead"] = "1"
        ctx["messages"].append("WolfCubRevenge")

    async def get_killer(self, ctx: dict[str, Any]) -> None:
        """Full GetKiller defense + kill branch."""
        from app.managers.bloodmoon import burn_if_blood_moon

        if burn_if_blood_moon(ctx, "get_killer"):
            return
        await resolve_killer(ctx)

    async def interrupt_sheriff(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """HunterKill: hold day until sheriff shot."""
        if not ctx.get("flags_out", {}).get("hunter_kill"):
            if not ctx.get("hunter_kill_pending"):
                return
        secs = int(
            load_json(_CHANCES)["sheriff_shot_seconds"]
        )
        ctx["stop_night"] = True
        ctx["extend_seconds"] = secs
        ctx["defer_day"] = True

    async def cult_hunter(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """GetCultHunter before CheckCult."""
        from app.managers.bloodmoon import burn_if_blood_moon
        from app.managers.cult_hunter_resolve import (
            resolve_cult_hunter,
        )

        if burn_if_blood_moon(ctx, "cult_hunter"):
            return
        await resolve_cult_hunter(ctx)

    async def cult_invite(self, ctx: dict[str, Any]) -> None:
        """CheckCult invite / convert resolve."""
        from app.managers.bloodmoon import burn_if_blood_moon
        from app.managers.cult_resolve import (
            resolve_cult,
        )

        if burn_if_blood_moon(ctx, "cult_invite"):
            return
        await resolve_cult(ctx)

    async def check_dar_neshan(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """DarNeshan gallows mark after CheckCult."""
        from app.managers.bloodmoon import burn_if_blood_moon
        from app.managers.darneshan_resolve import (
            resolve_dar_neshan_mark,
        )

        if burn_if_blood_moon(ctx, "check_dar_neshan"):
            return
        await resolve_dar_neshan_mark(ctx)

    async def check_franc(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """GetFranc guard or kill mode."""
        from app.managers.cult_side_effects import (
            resolve_franc,
        )

        await resolve_franc(ctx)

    async def get_angel(self, ctx: dict[str, Any]) -> None:
        """Report angel protection for cleanup."""
        from app.managers.bloodmoon import burn_if_blood_moon

        if burn_if_blood_moon(ctx, "get_angel"):
            return
        for item in ctx["players"]:
            if item.get("role") != "role_Fereshte":
                continue
            if not item.get("alive", True):
                continue
            raw = ctx["actions"].get(str(item["user_id"]))
            if raw:
                ctx["protected"] = int(raw)
                ctx["flags_out"]["angel_in"] = str(raw)

    async def natasha_visit(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Natasha night visit + wild child model."""
        await self._v.natasha_visit(ctx)
        self._v.wild_child_pick(ctx)
        from app.managers.special_resolve import (
            hamzad_pick,
        )

        hamzad_pick(ctx)

    async def seer_result(self, ctx: dict[str, Any]) -> None:
        """DM seer investigation result."""
        from app.managers.bloodmoon import burn_if_blood_moon

        if burn_if_blood_moon(ctx, "seer_result"):
            return
        for item in ctx["players"]:
            if item.get("role") != "role_pishgo":
                continue
            if not item.get("alive", True):
                continue
            raw = ctx["actions"].get(str(item["user_id"]))
            if not raw:
                continue
            target = int(raw)
            role_id = str(ctx["roles"].get(str(target), ""))
            label = self._v.seer_label(
                role_id,
                target_id=target,
                ctx=ctx,
            )
            await self._v.dm_role_result(
                int(item["user_id"]),
                label,
            )
        from app.managers.village_night import (
            deliver_seer_notes,
        )

        await deliver_seer_notes(
            ctx,
            self._bridge,
            self._texts,
            self._lang,
            self._v.seer_label,
        )

    async def check_fool(self, ctx: dict[str, Any]) -> None:
        """Fool night investigate (random role)."""
        from random import SystemRandom

        from app.managers.bloodmoon import burn_if_blood_moon

        if burn_if_blood_moon(ctx, "check_fool"):
            return
        for item in ctx["players"]:
            if item.get("role") != "role_Fool":
                continue
            if not item.get("alive", True):
                continue
            raw = ctx["actions"].get(str(item["user_id"]))
            if not raw:
                continue
            pool = [
                str(r) for r in ctx["roles"].values() if r
            ]
            role_id = (
                SystemRandom().choice(pool) if pool else ""
            )
            label = self._v.seer_label(role_id)
            await self._v.dm_role_result(
                int(item["user_id"]),
                label,
            )

    async def interrupt_royce(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Royce death: +30s, defer day, continue cleanup."""
        if not ctx.get("royce_pending"):
            return
        secs = int(
            load_json(_CHANCES)["royce_extend_seconds"]
        )
        ctx["defer_day"] = True
        ctx["extend_seconds"] = max(
            int(ctx.get("extend_seconds") or 0),
            secs,
        )
        ctx["flags_out"]["royce_selectd2"] = "1"

    async def special_reactions(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Guardian die-on-evil + traitor convert."""
        self._v.guardian_dies_on_evil(ctx)
        alive_wolves = [
            p
            for p in ctx["players"]
            if p.get("team") == "wolf"
            and p.get("alive", True)
            and int(p["user_id"]) not in ctx["deaths"]
        ]
        if alive_wolves:
            return
        for p in ctx["players"]:
            if p.get("role") != "role_Khaen":
                continue
            p["role"] = "role_wolf"
            p["team"] = "wolf"
            ctx["roles"][str(p["user_id"])] = "role_wolf"
            ctx["messages"].append(
                self._texts.get(
                    "TraitorTurnWolf",
                    self._lang,
                    bundle="results",
                )
            )

    async def final_deaths(self, ctx: dict[str, Any]) -> None:
        """Collect leftover kills + cult death effects."""
        causes = (
            ("wolf_target", "wolf"),
            ("sk_target", "sk"),
        )
        for key, cause in causes:
            target = ctx.get(key)
            if target is not None:
                uid = int(target)
                ctx["deaths"].add(uid)
                ctx.setdefault("death_cause", {})[
                    uid
                ] = cause
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
        # Blood death unlocks convert + chiang
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
