"""Mason/Nazer start links + lover helpers (05f)."""

from __future__ import annotations

import json
from typing import Any

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.managers.chat_bridge import ChatBridge
from app.managers.text_managers import TextManager


async def notify_mason_links(
    chat_id: int,
    players: list[dict[str, Any]],
    roles: dict[str, str],
    *,
    bridge: ChatBridge,
    texts: TextManager,
    lang: str,
) -> None:
    """PV mason teammates after role assign."""
    masons = [
        p
        for p in players
        if roles.get(str(p["user_id"])) == "role_feramason"
        and p.get("alive", True)
    ]
    if len(masons) < 2:
        if len(masons) == 1:
            uid = int(masons[0]["user_id"])
            await bridge.send_text(
                uid,
                texts.get(
                    "role_feramason",
                    lang,
                    bundle="roles",
                ),
            )
        return
    for me in masons:
        mates = ", ".join(
            str(o["fullname"])
            for o in masons
            if int(o["user_id"]) != int(me["user_id"])
        )
        await bridge.send_text(
            int(me["user_id"]),
            texts.get(
                "role_feramason_team",
                lang,
                mates,
                bundle="roles",
            ),
        )


async def notify_nazer_seer(
    chat_id: int,
    players: list[dict[str, Any]],
    roles: dict[str, str],
    *,
    bridge: ChatBridge,
    texts: TextManager,
    lang: str,
) -> None:
    """Tell beholder who the seer is."""
    seer_name = ""
    for p in players:
        if roles.get(str(p["user_id"])) == "role_pishgo":
            seer_name = str(p["fullname"])
            break
    for p in players:
        if roles.get(str(p["user_id"])) != "role_Nazer":
            continue
        key = "pishgo_not" if seer_name else "Not_pishgo"
        await bridge.send_text(
            int(p["user_id"]),
            texts.get(
                key,
                lang,
                seer_name,
                bundle="roles",
            ),
        )


async def set_lover_pair(
    chat_id: int,
    a: int,
    b: int,
    keys: RedisKeySpace | None = None,
) -> None:
    """Store bidirectional lover pair."""
    keys = keys or RedisKeySpace()
    redis = await get_redis()
    pair = f"{a}:{b}"
    await redis.hset(
        keys.game_flags(chat_id),
        keys.field("lover_pair"),
        pair,
    )


def parse_lover_pair(raw: str | None) -> tuple[int, int] | None:
    """Parse lover_pair flag."""
    if not raw or ":" not in raw:
        return None
    left, right = raw.split(":", 1)
    try:
        return int(left), int(right)
    except ValueError:
        return None


def follow_lover_deaths(ctx: dict[str, Any]) -> None:
    """If one lover dies, other dies too."""
    pair = ctx.get("lover_pair")
    if not pair:
        return
    parsed = parse_lover_pair(str(pair))
    if parsed is None:
        return
    a, b = parsed
    if a in ctx["deaths"] and b not in ctx["deaths"]:
        ctx["deaths"].add(b)
        ctx["messages"].append("LoverDied")
    elif b in ctx["deaths"] and a not in ctx["deaths"]:
        ctx["deaths"].add(a)
        ctx["messages"].append("LoverDied")


def apply_sweetheart_love(
    ctx: dict[str, Any],
    attacker_id: int,
    team: str,
) -> bool:
    """First attack on sweetheart → love; True if blocked."""
    for item in ctx["players"]:
        if item.get("role") != "role_Sweetheart":
            continue
        if not item.get("alive", True):
            continue
        sid = int(item["user_id"])
        love_team = ctx.get("sweetheart_love_team")
        if love_team == team:
            return False
        if ctx.get("lover_pair"):
            return False
        if attacker_id <= 0:
            return False
        pair = f"{attacker_id}:{sid}"
        ctx["flags_out"]["lover_pair"] = pair
        ctx["flags_out"]["sweetheart_love_team"] = team
        ctx["lover_pair"] = pair
        ctx["messages"].append("MsgLoveSweetHeart")
        return True
    return False
