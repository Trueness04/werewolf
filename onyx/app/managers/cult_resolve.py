"""CheckCult night resolve (sprint 5a)."""

from __future__ import annotations

from random import SystemRandom
from typing import Any

from app.managers.cult_helpers import (
    convert_to_ferqe,
    cult_attempt_ok,
    cult_rules,
    ferqe_bucket,
    pick_cult_target,
)
from app.managers.night_village import player


async def resolve_cult(ctx: dict[str, Any]) -> None:
    """Full CheckCult after cult hunter."""
    if ctx.get("royce_selectd2") and ctx.get(
        "royce_pending"
    ):
        ctx["flags_out"]["royce_dead"] = ""
        ctx["flags_out"]["royce_selectd2"] = ""
        ctx["royce_pending"] = False
    bucket = ferqe_bucket(ctx)
    if not bucket:
        return
    target_id, visitor_id = pick_cult_target(ctx)
    if target_id is None or visitor_id is None:
        return
    victim = player(ctx, target_id)
    if victim is None or not victim.get("alive", True):
        ctx["messages"].append("CultVisitDead")
        return
    # Huntsman trap 50%
    trap = ctx.get("huntsman_trap")
    if trap is not None and int(trap) == target_id:
        if SystemRandom().randrange(100) < 50:
            ctx["deaths"].add(visitor_id)
            ctx["messages"].append("HuntsmanKill")
            return
    if str(target_id) in (
        ctx.get("princess_prison") or set()
    ):
        ctx["messages"].append(
            "PrincessPrisonerCultAttack"
        )
        return
    role = str(victim.get("role") or "")
    buff = bool(ctx.get("convert_cult"))
    mummy = 20 if buff else 0
    rules = cult_rules()
    rng = SystemRandom()
    # Special branches
    if role == "role_shekar":
        ctx["deaths"].add(visitor_id)
        ctx["messages"].append("CultConvertCultHunter")
        return
    if role == "role_Qatel":
        if rng.randrange(100) < (
            rules["cult_vs_killer_base"] - mummy
        ):
            ctx["deaths"].add(visitor_id)
            ctx["messages"].append(
                "CultConvertKillerPublic"
            )
        else:
            ctx["messages"].append("CultVisitEmpty")
        return
    if role == "role_vampire":
        if rng.randrange(100) < (
            rules["cult_vs_vamp_base"] - mummy
        ):
            ctx["deaths"].add(visitor_id)
            ctx["messages"].append("VampireDeadCult")
        else:
            ctx["messages"].append("CultVisitEmpty")
        return
    if role == "role_kalantar":
        if rng.randrange(100) < (
            rules["cult_vs_sheriff_convert"] + mummy
        ):
            convert_to_ferqe(ctx, target_id)
            return
        if rng.randrange(100) < (
            rules["cult_vs_sheriff_shot"] - mummy
        ):
            ctx["deaths"].add(visitor_id)
            ctx["messages"].append("CultConvertHunter")
            return
        ctx["messages"].append("CultAttempt")
        return
    if role in set(rules["base_wolves"]):
        if ctx.get("natasha_id") == target_id:
            ctx["messages"].append("CultVisitEmpty")
            return
        ctx["deaths"].add(visitor_id)
        ctx["messages"].append("CultConvertWolfPublic")
        return
    if role == "role_Sweetheart":
        convert_to_ferqe(ctx, target_id)
        return
    if role == "role_feramason":
        convert_to_ferqe(ctx, target_id)
        return
    # Default CultAttemp
    if ctx.get("natasha_id") == target_id:
        ctx["messages"].append("CultVisitEmpty")
        return
    if cult_attempt_ok(role, convert_buff=buff):
        convert_to_ferqe(ctx, target_id)
    else:
        ctx["messages"].append("CultAttempt")
