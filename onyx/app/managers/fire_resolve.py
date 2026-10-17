"""Sprint 5bcd night slots: fire / ice / archer."""

from __future__ import annotations

import json
from typing import Any

from app.managers.fire_extra import (
    burn_blocked,
    persist_ice_marks,
    refresh_die_fire_and_ice,
)
from app.managers.night_attack import angel_target
from app.managers.night_village import player
from app.managers.village_links import apply_sweetheart_love


async def resolve_firefighter(
    ctx: dict[str, Any],
) -> None:
    """Oil from night≥2; fight burns with defenses."""
    night = int(ctx.get("night_no") or 0)
    if night < 2:
        return
    for item in ctx["players"]:
        if item.get("role") != "role_firefighter":
            continue
        if not item.get("alive", True):
            continue
        raw = ctx["actions"].get(str(item["user_id"]))
        if not raw:
            continue
        if str(raw).lower() == "fight":
            oils = ctx.get("firefighter_oils") or []
            for tid in oils:
                tid_i = int(tid)
                if player(ctx, tid_i) is None:
                    continue
                if burn_blocked(ctx, tid_i):
                    continue
                ctx["deaths"].add(tid_i)
            ctx["messages"].append("FirefighterBurn")
            ctx["firefighter_oils"] = []
            ctx["flags_out"]["firefighter_list"] = "[]"
            return
        oils = list(ctx.get("firefighter_oils") or [])
        oils.append(int(raw))
        ctx["firefighter_oils"] = oils
        ctx["flags_out"]["firefighter_list"] = json.dumps(
            oils
        )


async def resolve_ice_queen(
    ctx: dict[str, Any],
) -> None:
    """First hit freeze; second hit kill."""
    iced = set(ctx.get("ice_marked") or set())
    for item in ctx["players"]:
        if item.get("role") != "role_IceQueen":
            continue
        if not item.get("alive", True):
            continue
        raw = ctx["actions"].get(str(item["user_id"]))
        if not raw:
            continue
        tid = int(raw)
        if burn_blocked(ctx, tid):
            ctx["messages"].append("IceQueenBlocked")
            continue
        if tid in iced:
            ctx["deaths"].add(tid)
            iced.discard(tid)
            ctx["messages"].append("IceQueenKill")
        else:
            iced.add(tid)
            ctx["flags_out"]["player_iced"] = str(tid)
            ctx["messages"].append("IceQueenFreeze")
        ctx["ice_marked"] = iced
    persist_ice_marks(ctx)
    refresh_die_fire_and_ice(ctx)


async def resolve_archer(ctx: dict[str, Any]) -> None:
    """Archer shot every other night; cannot hit SK."""
    from random import SystemRandom

    from app.config.paths import ROOT
    from app.managers.json_loader import load_json

    night = int(ctx.get("night_no") or 0)
    send_for = int(ctx.get("archer_send_for") or 0)
    if night < send_for:
        return
    chances = load_json(
        ROOT / "data" / "config" / "field_chances.json"
    )
    for item in ctx["players"]:
        if item.get("role") != "role_Archer":
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
        if target.get("role") == "role_Qatel":
            continue
        if target.get("role") == "role_Sweetheart":
            if apply_sweetheart_love(
                ctx,
                int(item["user_id"]),
                "qatel",
            ):
                continue
        if target.get("role") == "role_Lilis":
            if SystemRandom().randrange(100) < int(
                chances["lilis_block_chance"]
            ):
                ctx["deaths"].add(int(item["user_id"]))
                continue
        if burn_blocked(ctx, tid):
            continue
        if angel_target(ctx) == tid:
            continue
        ctx["deaths"].add(tid)
        ctx["flags_out"]["archer_send_for"] = str(
            night + 2
        )
        ctx["messages"].append("Archer_shot")
