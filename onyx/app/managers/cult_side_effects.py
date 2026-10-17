"""Cult-related death side effects (sprint 5a)."""

from __future__ import annotations

from typing import Any

from app.managers.cult_helpers import ferqe_bucket
from app.managers.night_village import player


def apply_cult_deaths(ctx: dict[str, Any]) -> None:
    """DieCult / Royce / Franc / Huntsman←shekar."""
    deaths = set(ctx.get("deaths") or set())
    newly = []
    for uid in deaths:
        prow = player(ctx, int(uid))
        if prow is None:
            continue
        # Skip already-dead before this night
        if not prow.get("alive", True) and int(
            uid
        ) not in deaths:
            continue
        newly.append(prow)
    for prow in newly:
        role = str(prow.get("role") or "")
        uid = int(prow["user_id"])
        if role == "role_ferqe" and uid in deaths:
            # First ferqe death unlocks mummy keyboard
            if not ctx.get("die_cult"):
                for p in ctx["players"]:
                    if p.get("role") == "role_Mummy":
                        if p.get("alive", True):
                            ctx["flags_out"][
                                "die_cult"
                            ] = "1"
                            ctx["messages"].append(
                                "MummyMessageWhenKillCult"
                            )
                            break
        if role == "role_Royce" and uid in deaths:
            ctx["flags_out"]["royce_dead"] = str(
                int(ctx.get("night_no") or 0) + 1
            )
            ctx["royce_pending"] = True
            ctx["messages"].append("RoyceDead")
            if not ctx.get("convert_cult"):
                for p in ctx["players"]:
                    if p.get("role") == "role_Mummy":
                        if p.get("alive", True):
                            ctx["flags_out"][
                                "convert_cult"
                            ] = "20"
                            ctx["messages"].append(
                                "AfterDieRoyce"
                            )
                            break
        if role == "role_shekar" and uid in deaths:
            for p in ctx["players"]:
                if p.get("role") != "role_Huntsman":
                    continue
                if not p.get("alive", True):
                    continue
                p["role"] = "role_shekar"
                p["team"] = "villager"
                ctx["roles"][str(p["user_id"])] = (
                    "role_shekar"
                )
                ctx["messages"].append(
                    "HuntsmanDeadCultHulter"
                )
                break
    # Franc → killer if ferqe bucket empty
    bucket = ferqe_bucket(ctx)
    alive_bucket = [
        p
        for p in bucket
        if int(p["user_id"]) not in deaths
        and p.get("alive", True)
    ]
    if not alive_bucket:
        for p in ctx["players"]:
            if p.get("role") != "role_franc":
                continue
            if not p.get("alive", True):
                continue
            if int(p["user_id"]) in deaths:
                continue
            ctx["flags_out"]["franc_night_ok"] = "1"
            ctx["messages"].append("FrancDeadCult")


async def resolve_franc(ctx: dict[str, Any]) -> None:
    """GetFranc: guard report or kill mode."""
    for item in ctx["players"]:
        if item.get("role") != "role_franc":
            continue
        if not item.get("alive", True):
            continue
        raw = ctx["actions"].get(str(item["user_id"]))
        if not raw:
            continue
        tid = int(raw)
        if ctx.get("franc_night_ok") or ctx.get(
            "flags_out", {}
        ).get("franc_night_ok"):
            target = player(ctx, tid)
            if target and target.get("alive", True):
                ctx["deaths"].add(tid)
                ctx["messages"].append(
                    "FrancKillGroupMessage"
                )
            return
        # Guard mode: mark for attack defense
        guards = set(ctx.get("franc_guard") or set())
        guards.add(str(tid))
        ctx["franc_guard"] = guards
        ctx["flags_out"]["angel_in"] = str(tid)
