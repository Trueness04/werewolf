"""Wolf specials: white/honey/jadogar/beta/thief."""

from __future__ import annotations

import json
from random import SystemRandom
from typing import Any

from app.managers.night_village import player

_BASE_WOLVES = {
    "role_wolf",
    "role_WolfGorgine",
    "role_Tolle",
    "role_Wolfx",
    "role_Alpha",
}

_SENSITIVE = {
    "role_pishgo",
    "role_Fool",
    "role_Augur",
    "role_ngativ",
    "role_karagah",
    "role_Spy",
    "role_qhost",
    "role_Nazer",
}


def _alive_wolves(ctx: dict[str, Any]) -> list[dict]:
    return [
        p
        for p in ctx["players"]
        if p.get("alive", True)
        and str(p.get("role") or "") in _BASE_WOLVES
    ]


async def resolve_white_wolf(
    ctx: dict[str, Any],
) -> None:
    """Guard like angel; alone → become role_wolf."""
    for item in ctx["players"]:
        role = str(item.get("role") or "")
        if role not in {
            "role_WhiteWolf",
            "role_mighty_white_wolf",
        }:
            continue
        if not item.get("alive", True):
            continue
        uid = int(item["user_id"])
        if not _alive_wolves(ctx):
            item["role"] = "role_wolf"
            item["team"] = "wolf"
            ctx["roles"][str(uid)] = "role_wolf"
            ctx["messages"].append("WhiteWolfBecome")
            continue
        raw = ctx["actions"].get(str(uid))
        if not raw:
            continue
        tid = str(raw)
        guards = set(ctx.get("franc_guard") or set())
        guards.add(tid)
        ctx["franc_guard"] = guards
        ctx.setdefault("flags_out", {})["angel_in"] = tid
        ctx["messages"].append("WhiteWolfGuard")


async def resolve_honey(ctx: dict[str, Any]) -> None:
    """Mark HoneyUser; 50% fail vs cult hunter."""
    rng = SystemRandom()
    for item in ctx["players"]:
        if item.get("role") != "role_Honey":
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
        if target.get("role") == "role_shekar":
            if rng.randrange(100) < 50:
                ctx["messages"].append("HoneyFailHunter")
                continue
        ctx["honey_user"] = str(tid)
        ctx.setdefault("flags_out", {})[
            "honey_user"
        ] = str(tid)
        ctx["messages"].append("HoneyMark")


async def resolve_sorcerer(
    ctx: dict[str, Any],
) -> None:
    """WolfJadogar: sensitive role or other."""
    for item in ctx["players"]:
        if item.get("role") != "role_WolfJadogar":
            continue
        if not item.get("alive", True):
            continue
        raw = ctx["actions"].get(str(item["user_id"]))
        if not raw:
            continue
        tid = int(raw)
        role = str(ctx["roles"].get(str(tid), ""))
        if role in _SENSITIVE:
            note = (int(item["user_id"]), role, "JadogarSee")
        else:
            note = (
                int(item["user_id"]),
                "",
                "JadogarOther",
            )
        ctx.setdefault("seer_notes", []).append(note)


async def resolve_beta_wolf(
    ctx: dict[str, Any],
) -> None:
    """Each night mask beta as random non-wolf."""
    rng = SystemRandom()
    pool = [
        str(r)
        for r in set(ctx["roles"].values())
        if r
        and str(r) not in _BASE_WOLVES
        and str(r)
        not in {
            "role_betaWolf",
            "role_WhiteWolf",
            "role_iceWolf",
            "role_enchanter",
            "role_Honey",
        }
    ]
    if not pool:
        pool = ["role_villager"]
    for item in ctx["players"]:
        if item.get("role") != "role_betaWolf":
            continue
        if not item.get("alive", True):
            continue
        mask = rng.choice(pool)
        uid = str(item["user_id"])
        masks = dict(ctx.get("beta_masks") or {})
        masks[uid] = mask
        ctx["beta_masks"] = masks
        ctx.setdefault("flags_out", {})[
            "beta_masks"
        ] = json.dumps(masks)


async def resolve_thief(ctx: dict[str, Any]) -> None:
    """PN-12: Dozd removed — night slot is a no-op."""
    _ = ctx
