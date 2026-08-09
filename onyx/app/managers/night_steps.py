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
from app.managers.night_village import NightVillage, player
from app.managers.text_managers import TextManager

_CHANCES = ROOT / "data" / "config" / "field_chances.json"


class NightSteps(NightStubs):
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
        """Cult hunter night kill."""
        await self._v.cult_hunter(ctx)

    async def cult_invite(self, ctx: dict[str, Any]) -> None:
        """Record cult invite target."""
        for item in ctx["players"]:
            if item.get("role") != "role_ferqe":
                continue
            raw = ctx["actions"].get(str(item["user_id"]))
            if raw:
                ctx["cult_target"] = int(raw)

    async def get_angel(self, ctx: dict[str, Any]) -> None:
        """Report angel protection for cleanup."""
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

    async def seer_result(self, ctx: dict[str, Any]) -> None:
        """DM seer investigation result."""
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
            label = self._v.seer_label(role_id)
            await self._v.dm_role_result(
                int(item["user_id"]),
                label,
            )

    async def check_fool(self, ctx: dict[str, Any]) -> None:
        """Fool night investigate (random role)."""
        from random import SystemRandom

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
        """Collect leftover kills + converts."""
        for key in ("wolf_target", "sk_target"):
            target = ctx.get(key)
            if target is not None:
                ctx["deaths"].add(int(target))
        self._v.follow_natasha_death(ctx)
        self._v.convert_wild_child(ctx)
        self._v.promote_apprentice(ctx)
        cult = ctx.get("cult_target")
        if cult is None:
            return
        tid = int(cult)
        if tid in ctx["deaths"]:
            return
        victim = player(ctx, tid)
        if victim is None or not victim.get("alive", True):
            return
        if victim.get("team") in {"wolf", "cult"}:
            return
        if victim.get("role") == "role_shekar":
            for p in ctx["players"]:
                if p.get("role") == "role_ferqe" and p.get(
                    "alive", True
                ):
                    ctx["deaths"].add(int(p["user_id"]))
                    return
        victim["role"] = "role_ferqe"
        victim["team"] = "cult"
        ctx["roles"][str(tid)] = "role_ferqe"

    async def night_cleanup(
        self,
        ctx: dict[str, Any],
    ) -> None:
        """Clear ephemeral home/angel defense keys."""
        ctx["protected"] = None
        ctx["franc_guard"] = set()
        ctx["phoenix_heals"] = set()
        ctx["huntsman_trap"] = None
