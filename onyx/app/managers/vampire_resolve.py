"""Vampire / Chiang / Kent night resolve (05bcd)."""

from __future__ import annotations

from collections import Counter
from random import SystemRandom
from typing import Any

from app.config.paths import ROOT
from app.managers.json_loader import load_json
from app.managers.night_attack import (
    angel_target,
    common_defense,
)
from app.managers.night_village import player

_CHANCES = ROOT / "data" / "config" / "field_chances.json"


def _chance(key: str) -> int:
    """Percent from field_chances."""
    return int(load_json(_CHANCES)[key])


def blood_revealed(ctx: dict[str, Any]) -> bool:
    """True after Bloodthirsty is exposed."""
    return bool(
        ctx.get("blood_revealed")
        or (ctx.get("flags") or {}).get("blood_revealed")
    )


def reveal_blood(ctx: dict[str, Any]) -> None:
    """Expose Bloodthirsty + set convert chance."""
    if blood_revealed(ctx):
        return
    ctx["blood_revealed"] = True
    ctx["flags_out"]["blood_revealed"] = "1"
    ctx["flags_out"]["vampire_convert"] = str(
        _chance("blood_convert")
    )
    ctx["flags_out"]["dead_bloodthirsty"] = ""
    ctx["messages"].append("VampireFinded")


def notify_hilda_sk_dead(ctx: dict[str, Any]) -> None:
    """PV note when serial killer dies."""
    sk_dead = False
    for p in ctx["players"]:
        if p.get("role") != "role_Qatel":
            continue
        uid = int(p["user_id"])
        if not p.get("alive", True) or uid in ctx["deaths"]:
            sk_dead = True
    if not sk_dead:
        return
    for p in ctx["players"]:
        if p.get("role") != "role_Hilda":
            continue
        if not p.get("alive", True):
            continue
        ctx.setdefault("seer_notes", []).append(
            (
                int(p["user_id"]),
                "",
                "HildaSkDead",
            )
        )


async def resolve_chiang(ctx: dict[str, Any]) -> None:
    """Before blood death: ping a random enemy role."""
    if blood_revealed(ctx) or ctx.get("dead_bloodthirsty"):
        return
    for item in ctx["players"]:
        if item.get("role") != "role_chiang":
            continue
        if not item.get("alive", True):
            continue
        enemies = [
            p
            for p in ctx["players"]
            if p.get("alive", True)
            and p.get("team")
            not in {"villager", None}
            and p.get("role") != "role_chiang"
        ]
        if not enemies:
            continue
        pick = SystemRandom().choice(enemies)
        label = str(pick.get("role") or "")
        ctx.setdefault("seer_notes", []).append(
            (
                int(item["user_id"]),
                label,
                "ChiangPing",
            )
        )


async def resolve_kent(ctx: dict[str, Any]) -> None:
    """Spy until all action vampires dead, then arm."""
    vamp_alive = any(
        p.get("alive", True)
        and p.get("role") == "role_vampire"
        for p in ctx["players"]
    )
    if not vamp_alive:
        kent_alive = any(
            p.get("alive", True)
            and p.get("role") == "role_Kent"
            for p in ctx["players"]
        )
        if kent_alive:
            ctx["flags_out"]["kent_day_kill"] = "1"
            ctx["messages"].append(
                "KentVampireKillAllVampire"
            )
        return
    for item in ctx["players"]:
        if item.get("role") != "role_Kent":
            continue
        if not item.get("alive", True):
            continue
        raw = ctx["actions"].get(str(item["user_id"]))
        if not raw:
            continue
        tid = int(raw)
        target = player(ctx, tid)
        if target is None:
            continue
        ctx.setdefault("seer_notes", []).append(
            (
                int(item["user_id"]),
                str(target.get("role") or ""),
                "KentSee",
            )
        )


async def resolve_vampire(ctx: dict[str, Any]) -> None:
    """Team vamp vote: convert / kill / special branches."""
    voters = _vamp_voters(ctx)
    votes: list[int] = []
    last: dict[int, int] = {}
    for item in voters:
        raw = ctx["actions"].get(str(item["user_id"]))
        if not raw:
            continue
        try:
            tid = int(raw)
        except ValueError:
            continue
        if player(ctx, tid) is None:
            continue
        votes.append(tid)
        last[tid] = int(item["user_id"])
    if not votes:
        return
    tid, _ = Counter(votes).most_common(1)[0]
    if ctx.get("bard_redirect") is not None:
        tid = int(ctx["bard_redirect"])
    ctx["last_vamp_voter"] = last.get(tid)
    if common_defense(ctx, tid, attacker="vampire"):
        return
    if angel_target(ctx) == tid:
        ctx["messages"].append("GuardSaved")
        return
    outcome = _vamp_branch(ctx, tid)
    if outcome == "bitten":
        ctx["flags_out"]["convert_vampire"] = str(tid)
        ctx["messages"].append("PlayerBitten")
    elif outcome == "killed":
        ctx["deaths"].add(tid)
        ctx["messages"].append("VampireKill")


def _vamp_voters(ctx: dict[str, Any]) -> list[dict]:
    """Vampires + post-blood Chiang."""
    out: list[dict] = []
    post = blood_revealed(ctx) or ctx.get(
        "dead_bloodthirsty"
    )
    for p in ctx["players"]:
        if not p.get("alive", True):
            continue
        role = p.get("role")
        if role == "role_vampire":
            out.append(p)
        elif role == "role_BeladMoon":
            out.append(p)
        elif role == "role_chiang" and post:
            out.append(p)
    return out


def _vamp_branch(ctx: dict[str, Any], tid: int) -> str:
    """Return bitten|killed|blocked."""
    target = player(ctx, tid)
    if target is None:
        return "blocked"
    role = str(target.get("role") or "")
    rng = SystemRandom()
    if role == "role_joker":
        from app.managers.joker_books import (
            check_attack_joker,
        )

        if check_attack_joker(
            ctx,
            tid,
            attacker_id=ctx.get("last_vamp_voter"),
            team_attack=True,
        ):
            return "blocked"
    # Attacker dies vs SK / hunter
    if role in {"role_Qatel", "role_shekar"}:
        attacker = ctx.get("last_vamp_voter")
        if attacker is not None:
            ctx["deaths"].add(int(attacker))
        ctx["messages"].append("VampireVsKiller")
        return "blocked"
    # Lilis 60%
    if role == "role_Lilis":
        if rng.randrange(100) < _chance(
            "lilis_block_chance"
        ):
            attacker = ctx.get("last_vamp_voter")
            if attacker is not None:
                ctx["deaths"].add(int(attacker))
            return "blocked"
    # Black knight 50%
    if role == "role_BlackKnight":
        if rng.randrange(100) < 50:
            attacker = ctx.get("last_vamp_voter")
            if attacker is not None:
                ctx["deaths"].add(int(attacker))
            return "blocked"
        ctx["deaths"].add(tid)
        return "killed"
    # Base wolf 50% vamp dies
    if target.get("team") == "wolf":
        if rng.randrange(100) < _chance("vamp_vs_wolf"):
            attacker = ctx.get("last_vamp_voter")
            if attacker is not None:
                ctx["deaths"].add(int(attacker))
            return "blocked"
    # Sheriff without convert → reveal blood
    convert_on = bool(ctx.get("vampire_convert"))
    if role == "role_kalantar" and not convert_on:
        reveal_blood(ctx)
        ctx["deaths"].add(tid)
        return "killed"
    # Convert path
    if convert_on:
        try:
            chance = int(ctx.get("vampire_convert") or 40)
        except (TypeError, ValueError):
            chance = 40
        if rng.randrange(100) < chance:
            return "bitten"
        if blood_revealed(ctx):
            return "killed"
        if rng.randrange(100) < _chance("vamp_not_kill"):
            ctx["messages"].append("VampireDrink")
            return "blocked"
        return "killed"
    # No convert key: drink or kill
    if blood_revealed(ctx):
        return "killed"
    if rng.randrange(100) < _chance("vamp_not_kill"):
        ctx["messages"].append("VampireDrink")
        return "blocked"
    return "killed"
