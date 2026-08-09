"""Shared night attack defense (wolf + SK)."""

from __future__ import annotations

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
    """True if attack blocked before role branch.

    Order: huntsman → magic → phoenix → franc → prison.
    """
    _ = attacker
    rng = SystemRandom()
    # Huntsman trap (stub role: flag only)
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
    # Phoenix heal flag
    heals = ctx.get("phoenix_heals") or set()
    if target_id in heals:
        ctx["messages"].append("PhoenixSaved")
        return True
    # Franc guard (stub flag)
    if str(target_id) in (ctx.get("franc_guard") or set()):
        ctx["messages"].append("FrancSaved")
        return True
    # Princess prison (stub flag)
    if str(target_id) in (
        ctx.get("princess_prison") or set()
    ):
        ctx["messages"].append("PrisonBlocked")
        return True
    return False


def wolf_role_branch(
    ctx: dict[str, Any],
    target_id: int,
) -> str:
    """Return outcome: blocked|bitten|eaten|elder|mast.

    Bite only sets convert flags (sprint 2 applies).
    """
    victim = player(ctx, target_id)
    if victim is None:
        return "blocked"
    role = str(victim.get("role") or "")
    rng = SystemRandom()
    # Cursed → live + become wolf now (classic PHP)
    if role == "role_NefrinShode":
        victim["role"] = "role_wolf"
        victim["team"] = "wolf"
        ctx["roles"][str(target_id)] = "role_wolf"
        ctx["messages"].append("eat_nefrin")
        return "blocked"
    # Elder first save
    if role == "role_rishSefid" and not ctx.get(
        "elder_used"
    ):
        ctx["flags_out"]["elder_saved"] = "1"
        ctx["messages"].append("EatRishSefid")
        return "elder"
    # Drunk → eat + mast block next
    if role == "role_Mast":
        ctx["flags_out"]["mast_block_next"] = "1"
        ctx["deaths"].add(target_id)
        ctx["messages"].append("mastEatWolfGR")
        return "mast"
    # SK: 80% kill last wolf voter
    if role == "role_Qatel":
        if rng.randrange(100) < _chance(
            "sk_vs_wolf_kill_chance"
        ):
            last = ctx.get("last_wolf_voter")
            if last is not None:
                ctx["deaths"].add(int(last))
            return "blocked"
    # Sheriff may open HunterKill
    if role == "role_kalantar":
        wolves = sum(
            1
            for p in ctx["players"]
            if p.get("team") == "wolf"
            and p.get("alive", True)
        )
        chance = _chance("hunter_kill_wolf_base") + (
            max(wolves - 1, 0)
            * _chance("hunter_kill_wolf_per_extra")
        )
        if rng.randrange(100) < chance:
            ctx["flags_out"]["hunter_kill"] = str(
                target_id
            )
            ctx["stop_night"] = True
            ctx["deaths"].add(target_id)
            return "eaten"
    # Angel protect
    protected = angel_target(ctx)
    if protected == target_id:
        ctx["messages"].append("GuardSaved")
        return "blocked"
    # Bite chain before eat (flags only; sprint 2 applies).
    marked = str(
        ctx.get("enchanter_mark")
        or (ctx.get("flags") or {}).get("enchanter_mark")
        or ""
    )
    if marked == str(target_id):
        if rng.randrange(100) < _chance(
            "enchanter_convert"
        ):
            ctx["flags_out"]["convert_enchanter"] = str(
                target_id
            )
            ctx["messages"].append("PlayerBitten")
            return "bitten"
    alpha_dead = bool(
        ctx.get("alpha_dead")
        or (ctx.get("flags") or {}).get("alpha_dead")
    )
    if alpha_dead:
        if rng.randrange(100) < _chance(
            "forest_queen_convert"
        ):
            ctx["flags_out"]["convert_wolf"] = str(
                target_id
            )
            ctx["messages"].append("PlayerBitten")
            return "bitten"
    if rng.randrange(100) < _chance("alpha_convert"):
        ctx["flags_out"]["convert_wolf"] = str(target_id)
        ctx["messages"].append("PlayerBitten")
        return "bitten"
    ctx["deaths"].add(target_id)
    return "eaten"


def killer_role_branch(
    ctx: dict[str, Any],
    target_id: int,
) -> str:
    """SK role branch; return blocked|killed."""
    victim = player(ctx, target_id)
    if victim is None:
        return "blocked"
    role = str(victim.get("role") or "")
    # Black knight kills SK (stub role check)
    if role == "role_BlackKnight":
        for item in ctx["players"]:
            if item.get("role") == "role_Qatel":
                ctx["deaths"].add(int(item["user_id"]))
        return "blocked"
    protected = angel_target(ctx)
    if protected == target_id:
        ctx["messages"].append("GuardBlockedKiller")
        return "blocked"
    if role == "role_kalantar":
        ctx["flags_out"]["hunter_kill"] = str(target_id)
        ctx["stop_night"] = True
    ctx["deaths"].add(target_id)
    return "killed"


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
        if role == "role_Franc":
            guards.add(str(raw))
        if role == "role_Huntsman":
            ctx["huntsman_trap"] = int(raw)
        if role == "role_enchanter":
            ctx["enchanter_mark"] = str(raw)
    ctx["franc_guard"] = guards


async def resolve_wolf_team(ctx: dict[str, Any]) -> None:
    """Full WolfTeam vote + defense + branch."""
    if ctx.get("silver_active") or ctx.get("mast_block"):
        return
    preload_defense(ctx)
    from collections import Counter

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
            and item.get("role") != "role_WhiteWolf"
        ):
            continue
        votes.append(tid)
        voters[tid] = int(item["user_id"])
    if not votes:
        return
    target_id, _ = Counter(votes).most_common(1)[0]
    ctx["last_wolf_voter"] = voters.get(target_id)
    ctx["wolf_target"] = target_id
    if common_defense(ctx, target_id, attacker="wolf"):
        ctx["wolf_target"] = None
        return
    # Natasha empty home
    if ctx.get("natasha_id") == target_id:
        ctx["wolf_target"] = None
        ctx["messages"].append("EmptyHome")
        return
    outcome = wolf_role_branch(ctx, target_id)
    if outcome in {"blocked", "bitten", "elder"}:
        ctx["wolf_target"] = None


async def resolve_killer(ctx: dict[str, Any]) -> None:
    """Full GetKiller defense + branch."""
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
