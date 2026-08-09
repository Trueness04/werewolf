"""Joker/Harley book seeding, search, CheckAttack."""

from __future__ import annotations

import json
from random import SystemRandom
from typing import Any

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.managers.chat_bridge import ChatBridge
from app.managers.night_village import player
from app.managers.text_managers import TextManager

_rng = SystemRandom()
_BOOK_ROLES = {"role_joker", "role_harley"}
_ENEMY_KILL = {
    "role_wolf",
    "role_Alpha",
    "role_WhiteWolf",
    "role_Qatel",
    "role_Hilda",
    "role_Archer",
    "role_vampire",
    "role_Bloodthirsty",
}


async def seed_joker_books(
    chat_id: int,
    players: list[dict[str, Any]],
    roles: dict[str, str],
    keys: RedisKeySpace | None = None,
) -> int:
    """Hide books on up to 7 non-joker players."""
    keys = keys or RedisKeySpace()
    pool = [
        int(p["user_id"])
        for p in players
        if roles.get(str(p["user_id"]), "")
        not in _BOOK_ROLES
    ]
    _rng.shuffle(pool)
    holders = pool[: min(7, len(pool))]
    redis = await get_redis()
    flags = keys.game_flags(chat_id)
    await redis.hset(
        flags,
        mapping={
            keys.field("joker_book_holders"): json.dumps(
                holders
            ),
            keys.field("joker_books"): "0",
        },
    )
    return len(holders)


def harley_alive(ctx: dict[str, Any]) -> bool:
    """True if living Harley not already dying."""
    for p in ctx["players"]:
        if p.get("role") != "role_harley":
            continue
        if not p.get("alive", True):
            continue
        if int(p["user_id"]) in ctx["deaths"]:
            continue
        return True
    return False


def check_attack_joker(
    ctx: dict[str, Any],
    target_id: int,
    *,
    attacker_id: int | None,
    team_attack: bool = False,
) -> bool:
    """True if attack on Joker blocked by Harley."""
    victim = player(ctx, target_id)
    if victim is None or victim.get("role") != "role_joker":
        return False
    if not harley_alive(ctx):
        return False
    ctx["messages"].append("HarleyShield")
    if team_attack and attacker_id is not None:
        if _rng.randrange(100) < 50:
            ctx["deaths"].add(int(attacker_id))
    return True


async def resolve_harley_night2(
    ctx: dict[str, Any],
) -> None:
    """Night_no==2: free FindedBook++ once."""
    night = int(ctx.get("night_no") or 0)
    if night != 2:
        return
    if ctx.get("harley_free_book"):
        return
    if not harley_alive(ctx):
        return
    found = int(ctx.get("joker_books") or 0) + 1
    ctx["joker_books"] = found
    ctx["flags_out"]["joker_books"] = str(found)
    ctx["flags_out"]["harley_free_book"] = "1"
    ctx["messages"].append("Harly3DayFind")


async def resolve_joker_search(
    ctx: dict[str, Any],
    bridge: ChatBridge,
    texts: TextManager,
    lang: str,
    keys: RedisKeySpace | None = None,
) -> None:
    """Joker/Harley search; joker may kill enemies."""
    keys = keys or RedisKeySpace()
    chat_id = int(ctx["chat_id"])
    redis = await get_redis()
    flags = keys.game_flags(chat_id)
    raw = await redis.hget(
        flags,
        keys.field("joker_book_holders"),
    )
    try:
        holders = {
            int(x) for x in json.loads(raw or "[]")
        }
    except (TypeError, json.JSONDecodeError, ValueError):
        holders = set()
    found = int(
        await redis.hget(
            flags,
            keys.field("joker_books"),
        )
        or "0"
    )
    found_in = set(ctx.get("joker_found_in") or set())
    raw_fi = await redis.hget(
        flags,
        keys.field("joker_found_in"),
    )
    if raw_fi:
        try:
            found_in |= {
                int(x) for x in json.loads(raw_fi)
            }
        except (TypeError, json.JSONDecodeError, ValueError):
            pass
    for prow in ctx["players"]:
        role = prow.get("role")
        if role not in _BOOK_ROLES:
            continue
        if not prow.get("alive", True):
            continue
        uid = str(prow["user_id"])
        raw_t = ctx["actions"].get(uid)
        if not raw_t:
            continue
        try:
            target = int(raw_t)
        except ValueError:
            continue
        if ctx.get("bard_redirect") is not None:
            target = int(ctx["bard_redirect"])
        victim = player(ctx, target)
        if (
            role == "role_joker"
            and victim
            and victim.get("role") in _ENEMY_KILL
        ):
            if not harley_alive(ctx):
                ctx["deaths"].add(target)
                ctx["messages"].append("JokerKillEnemy")
            if target in holders:
                holders.discard(target)
                found += 1
                found_in.add(target)
                await bridge.send_text(
                    int(prow["user_id"]),
                    texts.get(
                        "SuccessFindJoker",
                        lang,
                        found,
                        bundle="roles",
                    ),
                )
            else:
                await bridge.send_text(
                    int(prow["user_id"]),
                    texts.get(
                        "FiledFindJoker",
                        lang,
                        bundle="roles",
                    ),
                )
            continue
        if target in found_in and role == "role_joker":
            await bridge.send_text(
                int(prow["user_id"]),
                texts.get(
                    "FiledFindJoker",
                    lang,
                    bundle="roles",
                ),
            )
            continue
        if target in holders:
            holders.discard(target)
            found += 1
            found_in.add(target)
            await bridge.send_text(
                int(prow["user_id"]),
                texts.get(
                    "SuccessFindJoker",
                    lang,
                    found,
                    bundle="roles",
                ),
            )
        else:
            await bridge.send_text(
                int(prow["user_id"]),
                texts.get(
                    "FiledFindJoker",
                    lang,
                    bundle="roles",
                ),
            )
    ctx["joker_books"] = found
    await redis.hset(
        flags,
        mapping={
            keys.field("joker_book_holders"): json.dumps(
                sorted(holders)
            ),
            keys.field("joker_books"): str(found),
            keys.field("joker_found_in"): json.dumps(
                sorted(found_in)
            ),
        },
    )


def transfer_book_on_death(ctx: dict[str, Any]) -> None:
    """Move book from dead holder to random living."""
    holders = set(ctx.get("joker_holders_live") or [])
    # Prefer flags list rebuilt by caller; noop if empty
    if not holders:
        return
    dead_holders = [
        h for h in holders if h in ctx["deaths"]
    ]
    if not dead_holders:
        return
    pool = [
        int(p["user_id"])
        for p in ctx["players"]
        if p.get("alive", True)
        and int(p["user_id"]) not in ctx["deaths"]
        and p.get("role") not in _BOOK_ROLES
        and int(p["user_id"]) not in holders
    ]
    for hid in dead_holders:
        holders.discard(hid)
        if pool:
            pick = _rng.choice(pool)
            holders.add(pick)
            pool.remove(pick)
    ctx["flags_out"]["joker_book_holders"] = json.dumps(
        sorted(holders)
    )
