"""Magento + Lilis + fire/ice helpers (05bcd)."""

from __future__ import annotations

import json
from random import SystemRandom
from typing import Any

from app.config.paths import ROOT
from app.managers.json_loader import load_json
from app.managers.night_attack import angel_target
from app.managers.night_village import player

_CHANCES = ROOT / "data" / "config" / "field_chances.json"


def _chance(key: str) -> int:
    """Percent from field_chances."""
    return int(load_json(_CHANCES)[key])


def burn_blocked(ctx: dict[str, Any], tid: int) -> bool:
    """True if magic/white/angel/franc/phoenix saves."""
    if tid in (ctx.get("phoenix_heals") or set()):
        return True
    if angel_target(ctx) == tid:
        return True
    if str(tid) in (ctx.get("franc_guard") or set()):
        return True
    target = player(ctx, tid)
    if target and target.get("role") == "role_WhiteWolf":
        return True
    return False


def refresh_die_fire_and_ice(ctx: dict[str, Any]) -> None:
    """Set flag when both Fire and Ice are gone."""
    fire_alive = False
    ice_alive = False
    for p in ctx["players"]:
        if not p.get("alive", True):
            continue
        if int(p["user_id"]) in ctx["deaths"]:
            continue
        role = p.get("role")
        if role == "role_firefighter":
            fire_alive = True
        if role == "role_IceQueen":
            ice_alive = True
    if not fire_alive and not ice_alive:
        # Only if at least one existed this game
        had = any(
            p.get("role")
            in {"role_firefighter", "role_IceQueen"}
            for p in ctx["players"]
        )
        if had:
            ctx["die_fire_and_ice"] = True
            ctx["flags_out"]["die_fire_and_ice"] = "1"


async def resolve_magento(ctx: dict[str, Any]) -> None:
    """~50% convert to Magento else kill (angel blocks)."""
    votes: list[int] = []
    for item in ctx["players"]:
        if item.get("role") != "role_Magento":
            continue
        if not item.get("alive", True):
            continue
        raw = ctx["actions"].get(str(item["user_id"]))
        if not raw:
            continue
        votes.append(int(raw))
    if not votes:
        return
    from collections import Counter

    tid, _ = Counter(votes).most_common(1)[0]
    if ctx.get("bard_redirect") is not None:
        tid = int(ctx["bard_redirect"])
    target = player(ctx, tid)
    if target is None:
        return
    rng = SystemRandom()
    if rng.randrange(100) < _chance("magento_convert"):
        target["role"] = "role_Magento"
        target["team"] = "solo"
        ctx["roles"][str(tid)] = "role_Magento"
        ctx["messages"].append("MagentoConvert")
        return
    if angel_target(ctx) == tid:
        ctx["messages"].append("GuardSaved")
        return
    ctx["deaths"].add(tid)
    ctx["messages"].append("MagentoKill")


async def resolve_lilis(ctx: dict[str, Any]) -> None:
    """Pre-flag: only Lucifer; post: free kill."""
    free = bool(
        ctx.get("die_fire_and_ice")
        or (ctx.get("flags") or {}).get("die_fire_and_ice")
    )
    for item in ctx["players"]:
        if item.get("role") != "role_Lilis":
            continue
        if not item.get("alive", True):
            continue
        raw = ctx["actions"].get(str(item["user_id"]))
        if not raw:
            continue
        tid = int(raw)
        if ctx.get("bard_redirect") is not None:
            tid = int(ctx["bard_redirect"])
        target = player(ctx, tid)
        if target is None:
            continue
        role = str(target.get("role") or "")
        if not free and role != "role_lucifer":
            ctx["messages"].append("LilisMiss")
            continue
        ctx["deaths"].add(tid)
        ctx["messages"].append("LilisKill")


def persist_ice_marks(ctx: dict[str, Any]) -> None:
    """Write ice_marked set into flags_out."""
    iced = ctx.get("ice_marked") or set()
    if iced:
        ctx["flags_out"]["ice_marked"] = json.dumps(
            [int(x) for x in iced]
        )
