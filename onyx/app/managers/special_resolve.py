"""Sprint 5e helpers: hamzad + black knight day."""

from __future__ import annotations

from typing import Any

from app.managers.night_village import player


def hamzad_pick(ctx: dict[str, Any]) -> None:
    """Night-1 model pick for doppelganger."""
    for item in ctx["players"]:
        if item.get("role") != "role_Hamzad":
            continue
        raw = ctx["actions"].get(str(item["user_id"]))
        if not raw:
            continue
        ctx["flags_out"]["hamzad_model"] = str(raw)
        ctx["hamzad_id"] = int(item["user_id"])
        ctx["hamzad_model"] = int(raw)


def convert_hamzad(ctx: dict[str, Any]) -> None:
    """On model death, copy victim role/team."""
    model = ctx.get("hamzad_model")
    hid = ctx.get("hamzad_id")
    if model is None:
        return
    if hid is None:
        for p in ctx["players"]:
            if p.get("role") == "role_Hamzad":
                hid = int(p["user_id"])
                break
    if hid is None:
        return
    if int(model) not in ctx["deaths"]:
        return
    twin = player(ctx, int(hid))
    victim = player(ctx, int(model))
    if twin is None or victim is None:
        return
    if int(hid) in ctx["deaths"]:
        return
    twin["role"] = victim.get("role")
    twin["team"] = victim.get("team")
    ctx["roles"][str(hid)] = str(victim.get("role"))
    ctx["messages"].append("HamzadConverted")


async def resolve_black_knight_day(
    ctx: dict[str, Any],
) -> None:
    """Day kill from BlackKnight selection."""
    roles = ctx.get("roles") or {}
    actions = ctx.get("actions") or {}
    deaths = ctx.setdefault("deaths", set())
    for uid, role in roles.items():
        if role != "role_BlackKnight":
            continue
        raw = actions.get(str(uid))
        if not raw:
            continue
        tid = int(raw)
        deaths.add(tid)
        from app.cache.redis_client import get_redis
        from app.cache.redis_keys import RedisKeySpace

        keys = RedisKeySpace()
        redis = await get_redis()
        await redis.set(
            keys.player_state(tid),
            "dead",
        )
        ctx.setdefault("messages", []).append(
            "BlackKnightKill"
        )


async def resolve_dynamite_find(
    ctx: dict[str, Any],
) -> None:
    """Day dynamite search (same rules as night)."""
    from app.managers.special_teams import (
        resolve_dynamite_night,
    )

    await resolve_dynamite_night(ctx)
