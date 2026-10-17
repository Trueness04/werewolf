"""Activate and apply in-game magic effects."""

from __future__ import annotations

import json
from random import SystemRandom
from typing import Any

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.managers.chat_bridge import ChatBridge
from app.managers.magic_inventory import (
    consume_effect,
    inventory_counts,
)
from app.managers.text_managers import TextManager
from importlib import import_module

_Registry = import_module(
    "app.class.roles.registry"
).RoleRegistry

_rng = SystemRandom()


def used_field(user_id: int) -> str:
    """Per-game one-magic lock field name."""
    return f"UseMajik:{user_id}"


def heal_field(user_id: int) -> str:
    return f"MajikHeal:{user_id}"


def ghost_field(user_id: int) -> str:
    return f"MajikGhost:{user_id}"


def pending_field(user_id: int) -> str:
    """Pending activate type waiting apply tick."""
    return f"MajikPending:{user_id}"


async def magic_allowed(
    chat_id: int,
    keys: RedisKeySpace | None = None,
) -> bool:
    """Session senior may veto magic (default allow)."""
    keys = keys or RedisKeySpace()
    redis = await get_redis()
    raw = await redis.hget(
        keys.game_flags(chat_id),
        keys.field("magic_allowed"),
    )
    if raw is None:
        return True
    return str(raw) not in ("0", "false", "no")


async def already_used(
    chat_id: int,
    user_id: int,
    keys: RedisKeySpace | None = None,
) -> bool:
    keys = keys or RedisKeySpace()
    redis = await get_redis()
    return bool(
        await redis.hget(
            keys.game_flags(chat_id),
            used_field(user_id),
        )
    )


async def activate_magic(
    *,
    chat_id: int,
    user_id: int,
    effect_type: str,
    bridge: ChatBridge,
    texts: TextManager,
    lang: str,
    keys: RedisKeySpace | None = None,
) -> str:
    """
    Consume inventory + mark used.
    Returns ok | not_buy | not_in_game | already | veto | bad.
    """
    keys = keys or RedisKeySpace()
    redis = await get_redis()
    role = await redis.get(keys.player_role(user_id))
    if not role:
        return "not_in_game"
    state = await redis.get(keys.player_state(user_id))
    if state == "dead":
        return "dead"
    if not await magic_allowed(chat_id, keys):
        return "veto"
    if await already_used(chat_id, user_id, keys):
        return "already"
    counts = await inventory_counts(user_id)
    if int(counts.get(effect_type, 0)) < 1:
        return "not_buy"
    if not await consume_effect(user_id, effect_type):
        return "not_buy"
    flags = keys.game_flags(chat_id)
    await redis.hset(flags, used_field(user_id), effect_type)
    # Immediate effects
    if effect_type == "MajiKhabar":
        await _apply_khabar(
            chat_id,
            user_id,
            bridge,
            texts,
            lang,
            keys,
        )
    elif effect_type == "MajikSear":
        await _apply_sear(
            chat_id,
            user_id,
            bridge,
            texts,
            lang,
            keys,
        )
    elif effect_type == "MajiKHil":
        await redis.hset(flags, heal_field(user_id), "1")
        await bridge.send_text(
            user_id,
            texts.get("ActiveHealMajik", lang),
        )
    elif effect_type == "MajiKGhost":
        await redis.hset(flags, ghost_field(user_id), "1")
        await bridge.send_text(
            user_id,
            texts.get("GhostActive", lang),
        )
    else:
        return "bad"
    ok_key = f"SuccessActive_{effect_type}"
    await bridge.send_text(
        user_id,
        texts.get(ok_key, lang),
    )
    return "ok"


async def _alive_others(
    chat_id: int,
    user_id: int,
    keys: RedisKeySpace,
) -> list[dict[str, Any]]:
    redis = await get_redis()
    players = json.loads(
        await redis.get(keys.game_players(chat_id)) or "[]"
    )
    roles = json.loads(
        await redis.get(keys.game_roles(chat_id)) or "{}"
    )
    out: list[dict[str, Any]] = []
    registry = _Registry()
    my_team = None
    my_role = roles.get(str(user_id))
    if my_role:
        my_team = registry.definition(my_role).get("team")
    for p in players:
        uid = int(p["user_id"])
        if uid == user_id:
            continue
        st = await redis.get(keys.player_state(uid))
        if st == "dead":
            continue
        rid = roles.get(str(uid))
        info = registry.definition(rid) if rid else {}
        out.append(
            {
                **p,
                "role": rid,
                "team": info.get("team"),
                "alive": True,
            }
        )
    # prefer non-teammates for khabar
    enemies = [
        x for x in out if x.get("team") != my_team
    ]
    return enemies or out


async def _role_name(
    role_id: str | None,
    texts: TextManager,
    lang: str,
) -> str:
    if not role_id:
        return "?"
    info = _Registry().definition(role_id)
    mk = info.get("message_keys") or {}
    key = mk.get("name") or role_id
    return texts.get(str(key), lang, bundle="roles")


async def _apply_khabar(
    chat_id: int,
    user_id: int,
    bridge: ChatBridge,
    texts: TextManager,
    lang: str,
    keys: RedisKeySpace,
) -> None:
    others = await _alive_others(chat_id, user_id, keys)
    if not others:
        return
    pick = _rng.choice(others)
    rname = await _role_name(
        pick.get("role"),
        texts,
        lang,
    )
    msg = texts.get(
        "MajikKhabarChinSee",
        lang,
        pick.get("fullname") or pick["user_id"],
        rname,
    )
    await bridge.send_text(user_id, msg)


async def _apply_sear(
    chat_id: int,
    user_id: int,
    bridge: ChatBridge,
    texts: TextManager,
    lang: str,
    keys: RedisKeySpace,
) -> None:
    """Full Sear (MF-41): accurate role reveal to caster."""
    others = await _alive_others(chat_id, user_id, keys)
    if not others:
        return
    pick = _rng.choice(others)
    rname = await _role_name(
        pick.get("role"),
        texts,
        lang,
    )
    # Prefer Searsee from flavor; fallback main
    msg = texts.get(
        "Searsee",
        lang,
        pick.get("fullname") or pick["user_id"],
        rname,
        bundle="general",
    )
    if msg == "Searsee" or msg.startswith("TODO"):
        msg = texts.get(
            "MajikKhabarChinSee",
            lang,
            pick.get("fullname") or pick["user_id"],
            rname,
        )
    await bridge.send_text(user_id, msg)


async def is_magic_healed(
    chat_id: int,
    user_id: int,
    keys: RedisKeySpace | None = None,
) -> bool:
    keys = keys or RedisKeySpace()
    redis = await get_redis()
    return bool(
        await redis.hget(
            keys.game_flags(chat_id),
            heal_field(user_id),
        )
    )


async def is_magic_ghost(
    chat_id: int,
    user_id: int,
    keys: RedisKeySpace | None = None,
) -> bool:
    keys = keys or RedisKeySpace()
    redis = await get_redis()
    return bool(
        await redis.hget(
            keys.game_flags(chat_id),
            ghost_field(user_id),
        )
    )


async def refund_unused_on_death(
    chat_id: int,
    user_id: int,
    bridge: ChatBridge,
    texts: TextManager,
    lang: str,
    keys: RedisKeySpace | None = None,
) -> None:
    """
    If player died after activating Hil/Ghost without
    'consuming' the use-lock incorrectly — PHP refunds
    when death before effect. We refund if they had
    activated Hil/Ghost and still hold the flag, OR
    if they never used but we consumed — already consumed
    on activate.

    Product (MF-52): refund the activated magic type
    back to inventory on death (PlayerDie).
    """
    from app.managers.magic_inventory import refund_effect

    keys = keys or RedisKeySpace()
    redis = await get_redis()
    flags = keys.game_flags(chat_id)
    used = await redis.hget(flags, used_field(user_id))
    if not used:
        return
    effect = str(used)
    # Clear protect/ghost flags
    await redis.hdel(flags, heal_field(user_id))
    await redis.hdel(flags, ghost_field(user_id))
    await refund_effect(user_id, effect)
    await redis.hdel(flags, used_field(user_id))
    await bridge.send_text(
        user_id,
        texts.get("PlayerDie", lang),
    )
