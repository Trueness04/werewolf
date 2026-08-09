"""Shared night attack defense (wolf + SK)."""

from __future__ import annotations

from collections import Counter
from random import SystemRandom
from typing import Any

from app.config.paths import ROOT
from app.managers.json_loader import load_json
from app.managers.night_village import player

_CHANCES = ROOT / "data" / "config" / "field_chances.json"


def _chance(key: str) -> int:
    """Read percent chance from config."""
    data = load_json(_CHANCES)
    return int(data[key])


def angel_target(ctx: dict[str, Any]) -> int | None:
    """Who guardian protects tonight."""
    for item in ctx["players"]:
        if item.get("role") != "role_Fereshte":
            continue
        if not item.get("alive", True):
            continue
        raw = ctx["actions"].get(str(item["user_id"]))
        if raw:
            return int(raw)
    return None


def common_defense(
    ctx: dict[str, Any],
    target_id: int,
    *,
    attacker: str,
) -> bool:
    """True if attack blocked before role branch."""
    _ = attacker
    rng = SystemRandom()
    trap = ctx.get("huntsman_trap")
    if trap is not None and int(trap) == target_id:
        if rng.randrange(100) < _chance(
            "huntsman_trap_chance"
        ):
            last = ctx.get("last_wolf_voter")
            if last is not None:
                ctx["deaths"].add(int(last))
            ctx["messages"].append("HuntsmanTrap")
            return True
    heals = ctx.get("phoenix_heals") or set()
    if target_id in heals:
        ctx["messages"].append("PhoenixSaved")
        return True
    magic_heals = ctx.get("magic_heals") or set()
    if target_id in magic_heals:
        ctx["messages"].append("ActiveHealMajik")
        return True
    if str(target_id) in (ctx.get("franc_guard") or set()):
        ctx["messages"].append("FrancSaved")
        return True
    mummy = ctx.get("mummy_guard")
    if mummy is not None and int(mummy) == target_id:
        ctx["messages"].append("MummySaved")
        return True
    if str(target_id) in (
        ctx.get("princess_prison") or set()
    ):
        ctx["messages"].append("PrisonBlocked")
        return True
    return False


def preload_defense(ctx: dict[str, Any]) -> None:
    """Read same-night defense selections from actions."""
    guards: set[str] = set(ctx.get("franc_guard") or [])
    for item in ctx["players"]:
        if not item.get("alive", True):
            continue
        role = item.get("role")
        raw = ctx["actions"].get(str(item["user_id"]))
        if not raw:
            continue
        if role == "role_franc":
            guards.add(str(raw))
        if role == "role_Huntsman":
            ctx["huntsman_trap"] = int(raw)
        if role == "role_enchanter":
            from app.managers.enchanter_list import (
                append_uid,
                dumps,
            )

            marked = str(raw)
            ctx["enchanter_mark"] = marked
            cur = [
                str(x)
                for x in (ctx.get("enchanter_list") or [])
            ]
            cur = append_uid(cur, marked)
            ctx["enchanter_list"] = cur
            ctx.setdefault("flags_out", {})[
                "enchanter_mark"
            ] = marked
            ctx["flags_out"]["enchanter_list"] = dumps(
                cur
            )
        if role == "role_Mummy":
            ctx["mummy_guard"] = int(raw)
    ctx["franc_guard"] = guards


async def resolve_wolf_team(ctx: dict[str, Any]) -> None:
    """Full WolfTeam vote + defense + branch."""
    from app.managers.attack_branches import (
        wolf_role_branch,
    )

    if ctx.get("silver_active") or ctx.get("mast_block"):
        return
    preload_defense(ctx)
    votes: list[int] = []
    voters: dict[int, int] = {}
    for item in ctx["players"]:
        if item.get("team") != "wolf":
            continue
        if not item.get("alive", True):
            continue
        raw = ctx["actions"].get(str(item["user_id"]))
        if not raw:
            continue
        try:
            tid = int(raw)
        except ValueError:
            continue
        target = player(ctx, tid)
        if target is None:
            continue
        if (
            target.get("team") == "wolf"
            and item.get("role")
            not in {
                "role_WhiteWolf",
                "role_mighty_white_wolf",
            }
        ):
            continue
        votes.append(tid)
        voters[tid] = int(item["user_id"])
    if not votes:
        return
    target_id, _ = Counter(votes).most_common(1)[0]
    if ctx.get("bard_redirect") is not None:
        target_id = int(ctx["bard_redirect"])
    ctx["last_wolf_voter"] = voters.get(target_id)
    ctx["wolf_target"] = target_id
    if common_defense(ctx, target_id, attacker="wolf"):
        ctx["wolf_target"] = None
        return
    if ctx.get("natasha_id") == target_id:
        ctx["wolf_target"] = None
        ctx["messages"].append("EmptyHome")
        return
    outcome = wolf_role_branch(ctx, target_id)
    if outcome in {"blocked", "bitten", "elder"}:
        ctx["wolf_target"] = None


async def resolve_killer(ctx: dict[str, Any]) -> None:
    """Full GetKiller defense + branch."""
    from app.managers.attack_branches import (
        killer_role_branch,
    )

    preload_defense(ctx)
    for item in ctx["players"]:
        if item.get("role") != "role_Qatel":
            continue
        if not item.get("alive", True):
            continue
        raw = ctx["actions"].get(str(item["user_id"]))
        if not raw:
            continue
        target_id = int(raw)
        if ctx.get("bard_redirect") is not None:
            target_id = int(ctx["bard_redirect"])
        ctx["sk_target"] = target_id
        if common_defense(
            ctx,
            target_id,
            attacker="killer",
        ):
            ctx["sk_target"] = None
            return
        if ctx.get("natasha_id") == target_id:
            ctx["sk_target"] = None
            ctx["messages"].append("EmptyHome")
            return
        outcome = killer_role_branch(ctx, target_id)
        if outcome == "blocked":
            ctx["sk_target"] = None
        return
