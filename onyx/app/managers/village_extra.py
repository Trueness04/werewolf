"""Cupid night + bard/watermelon/babr resolvers."""

from __future__ import annotations

from random import SystemRandom
from typing import Any

from app.managers.night_village import player
from app.managers.village_links import set_lover_pair


async def resolve_cupid(ctx: dict[str, Any]) -> None:
    """Elahe: 'a:b' or single id + random partner."""
    for item in ctx["players"]:
        if item.get("role") != "role_elahe":
            continue
        if not item.get("alive", True):
            continue
        raw = ctx["actions"].get(str(item["user_id"]))
        if not raw:
            continue
        parts = str(raw).split(":")
        try:
            if len(parts) == 2:
                a, b = int(parts[0]), int(parts[1])
            else:
                a = int(parts[0])
                others = [
                    int(p["user_id"])
                    for p in ctx["players"]
                    if p.get("alive", True)
                    and int(p["user_id"])
                    not in {a, int(item["user_id"])}
                ]
                if not others:
                    continue
                b = SystemRandom().choice(others)
        except ValueError:
            continue
        if a == b:
            continue
        pair = f"{a}:{b}"
        ctx["flags_out"]["lover_pair"] = pair
        ctx["lover_pair"] = pair
        ctx["messages"].append("CupeDone")
        await set_lover_pair(int(ctx["chat_id"]), a, b)


def maybe_bard_reroute(ctx: dict[str, Any]) -> None:
    """Khenyager: randomly replace some night targets."""
    bard = None
    for item in ctx["players"]:
        if item.get("role") != "role_Khenyager":
            continue
        if item.get("alive", True):
            bard = item
            break
    if bard is None:
        return
    raw = ctx["actions"].get(str(bard["user_id"]))
    if not raw:
        return
    # Bard marks one action key to scramble: all votes
    alive = [
        int(p["user_id"])
        for p in ctx["players"]
        if p.get("alive", True)
    ]
    if len(alive) < 2:
        return
    rng = SystemRandom()
    pick = rng.choice(alive)
    ctx["bard_redirect"] = pick
    ctx.setdefault("flags_out", {})[
        "sweetheart_love_team"
    ] = "khenyager"
    # Scramble every other night action target
    for uid_s, raw in list(ctx["actions"].items()):
        if int(uid_s) == int(bard["user_id"]):
            continue
        alt = [u for u in alive if str(u) != str(raw)]
        if alt:
            ctx["actions"][uid_s] = str(rng.choice(alt))


async def resolve_watermelon(
    ctx: dict[str, Any],
) -> None:
    """Watermelon: inform only."""
    for item in ctx["players"]:
        if item.get("role") != "role_Watermelon":
            continue
        if not item.get("alive", True):
            continue
        raw = ctx["actions"].get(str(item["user_id"]))
        if not raw:
            continue
        tid = int(raw)
        ctx.setdefault("seer_notes", []).append(
            (
                int(item["user_id"]),
                "",
                "WatermelonChoseSuccess",
            )
        )
        ctx.setdefault("seer_notes", []).append(
            (tid, "", "WatermelonChoseUser")
        )


async def resolve_babr(ctx: dict[str, Any]) -> None:
    """Tiger night kill (like cow + angel block)."""
    for item in ctx["players"]:
        if item.get("role") != "role_babr":
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
        protected = ctx.get("protected")
        if protected == tid:
            ctx["messages"].append("CowAngel")
            continue
        ctx["deaths"].add(tid)
        ctx["messages"].append("BabrKillGroupMessage")
