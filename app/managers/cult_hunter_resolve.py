"""GetCultHunter night resolve (sprint 5a)."""

from __future__ import annotations

from random import SystemRandom
from typing import Any

from app.managers.cult_helpers import cult_rules
from app.managers.night_village import player


async def resolve_cult_hunter(
    ctx: dict[str, Any],
) -> None:
    """Deepened hunter visit vs cult/franc/SK."""
    rules = cult_rules()
    for item in ctx["players"]:
        if item.get("role") != "role_shekar":
            continue
        if not item.get("alive", True):
            continue
        raw = ctx["actions"].get(str(item["user_id"]))
        if not raw:
            continue
        hunter_id = int(item["user_id"])
        tid = int(raw)
        target = player(ctx, tid)
        if target is None or not target.get(
            "alive",
            True,
        ):
            ctx["messages"].append("HunterVisitDead")
            continue
        trap = ctx.get("huntsman_trap")
        if trap is not None and int(trap) == tid:
            if SystemRandom().randrange(100) < 50:
                ctx["deaths"].add(hunter_id)
                ctx["messages"].append("HuntsmanKill")
                continue
        role = str(target.get("role") or "")
        if role == "role_Qatel":
            ctx["deaths"].add(hunter_id)
            ctx["messages"].append(
                "SerialKillerKilledCH"
            )
            continue
        if role == "role_franc":
            if SystemRandom().randrange(100) <= int(
                rules["hunter_vs_franc_pct"]
            ):
                ctx["deaths"].add(hunter_id)
                ctx["messages"].append(
                    "CultHunterFrancMessage"
                )
            else:
                ctx["deaths"].add(tid)
                ctx["messages"].append(
                    "CultHunterKillFrancGroup"
                )
            continue
        if role in {"role_ferqe", "role_Royce", "role_DarNeshan"}:
            ctx["deaths"].add(tid)
            ctx["messages"].append("HunterKilledCultist")
            if role == "role_DarNeshan":
                ctx.setdefault("death_pvs", {})[tid] = (
                    "DarNeshanKilledByShekar"
                )
            # Mummy guarding victim dies too
            guard = ctx.get("mummy_guard")
            if guard is not None and int(guard) == tid:
                for p in ctx["players"]:
                    if p.get("role") == "role_Mummy":
                        if p.get("alive", True):
                            ctx["deaths"].add(
                                int(p["user_id"])
                            )
                            ctx["messages"].append(
                                "MummyCultHunterKill"
                            )
            continue
        ctx["messages"].append("HunterFailedToFind")
