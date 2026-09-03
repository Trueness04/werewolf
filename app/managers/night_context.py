"""Build night resolution context from Redis."""

from __future__ import annotations

import json
from typing import Any

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from importlib import import_module

_Registry = import_module(
    "app.class.roles.registry"
).RoleRegistry


async def build_night_context(
    chat_id: int,
    keys: RedisKeySpace,
) -> dict[str, Any]:
    """Load players, roles, actions, flags into ctx."""
    redis = await get_redis()
    registry = _Registry()
    players = json.loads(
        await redis.get(keys.game_players(chat_id))
        or "[]"
    )
    roles = json.loads(
        await redis.get(keys.game_roles(chat_id)) or "{}"
    )
    actions = await redis.hgetall(
        keys.night_actions(chat_id)
    )
    flags = keys.game_flags(chat_id)
    enriched: list[dict[str, Any]] = []
    for item in players:
        uid = str(item["user_id"])
        rid = roles.get(uid)
        state = await redis.get(
            keys.player_state(int(uid))
        )
        alive = state != "dead"
        info = registry.definition(rid) if rid else {}
        enriched.append(
            {
                **item,
                "role": rid,
                "team": info.get("team"),
                "alive": alive,
            }
        )

    async def flag(name: str) -> str | None:
        return await redis.hget(flags, keys.field(name))

    night_raw = await redis.get(keys.night_count(chat_id))
    phoenix = await flag("phoenix_healer")
    heals: set[int] = set()
    if phoenix:
        try:
            heals.add(int(phoenix))
        except ValueError:
            pass
    return {
        "chat_id": chat_id,
        "players": enriched,
        "roles": roles,
        "actions": actions,
        "night_no": int(night_raw or "0"),
        "wolf_target": None,
        "sk_target": None,
        "protected": None,
        "cult_target": None,
        "natasha_host": None,
        "natasha_id": None,
        "silver_active": bool(
            await flag("silver_active")
        ),
        "mast_block": bool(await flag("mast_block")),
        "elder_used": bool(await flag("elder_saved")),
        "wild_child_model": await flag("wild_child_model"),
        "wild_child_id": await flag("wild_child_id"),
        "wolf_cube_pending": bool(
            await flag("wolf_cube_dead")
        ),
        "send_wolf_cube_dead": bool(
            await flag("send_wolf_cube_dead")
        ),
        "hunter_kill_pending": bool(
            await flag("hunter_kill")
        ),
        "royce_pending": bool(await flag("royce_dead")),
        "check_night_done": bool(
            await flag("check_night_done")
        ),
        "phoenix_heals": heals,
        "magic_heals": await _magic_heals(
            chat_id,
            keys,
            enriched,
        ),
        "magic_ghosts": await _magic_ghosts(
            chat_id,
            keys,
            enriched,
        ),
        "franc_guard": set(),
        "huntsman_trap": None,
        "alpha_dead": bool(await flag("alpha_dead")),
        "enchanter_mark": await flag("enchanter_mark"),
        "honey_user": await flag("honey_user"),
        "beta_masks": _load_str_map(
            await flag("beta_masks")
        ),
        "dozd_target": await flag("dozd_target"),
        "dozd_alpha_hit": await flag("dozd_alpha_hit"),
        "darneshan_mark_target": await flag(
            "darneshan_mark_target"
        ),
        "darneshan_mark_by": await flag(
            "darneshan_mark_by"
        ),
        "blood_moon_active": bool(
            await flag("blood_moon_active")
        ),
        "enchanter_list": _load_str_list(
            await flag("enchanter_list")
        ),
        "ice_prev": await flag("ice_prev"),
        "vampire_convert": await flag("vampire_convert"),
        "die_cult": bool(await flag("die_cult")),
        "convert_cult": bool(await flag("convert_cult")),
        "franc_night_ok": bool(
            await flag("franc_night_ok")
        ),
        "royce_selectd2": bool(
            await flag("royce_selectd2")
        ),
        "princess_prison": (
            {str(p)}
            if (p := await flag("princess_prison"))
            else set()
        ),
        "find_ghost": bool(await flag("find_ghost")),
        "firefighter_oils": _load_oils(
            await flag("firefighter_list")
        ),
        "ice_marked": _load_int_set(
            await flag("ice_marked")
        ),
        "die_fire_and_ice": bool(
            await flag("die_fire_and_ice")
        ),
        "blood_revealed": bool(
            await flag("blood_revealed")
        ),
        "dead_bloodthirsty": bool(
            await flag("dead_bloodthirsty")
        ),
        "archer_send_for": int(
            (await flag("archer_send_for")) or "0"
        ),
        "bomber_parts": _load_int_set(
            await flag("bomber_parts")
        ),
        "dinamit_finds": int(
            (await flag("dinamit_finds")) or "0"
        ),
        "joker_books": int(
            (await flag("joker_books")) or "0"
        ),
        "harley_free_book": bool(
            await flag("harley_free_book")
        ),
        "hamzad_model": (
            int(m)
            if (m := await flag("hamzad_model"))
            else None
        ),
        "lover_pair": await flag("lover_pair"),
        "sweetheart_love_team": await flag(
            "sweetheart_love_team"
        ),
        "flags_out": {},
        "deaths": set(),
        "seer_notes": [],
        "messages": [],
        "dm_messages": [],
        "death_pvs": {},
        "stop_night": False,
        "defer_day": False,
        "extend_seconds": 0,
    }


def _load_oils(raw: str | None) -> list[int]:
    """Parse firefighter oil list from Redis."""
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return [int(x) for x in data]


def _load_int_set(raw: str | None) -> set[int]:
    """Parse JSON int list into a set."""
    if not raw:
        return set()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return set()
    return {int(x) for x in data}


def _load_str_map(raw: str | None) -> dict[str, Any]:
    """Parse JSON object into a str-keyed map."""
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): v for k, v in data.items()}


def _load_str_list(raw: str | None) -> list[str]:
    """Parse JSON array into a list of strings."""
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return [str(x) for x in data]


async def _magic_heals(
    chat_id: int,
    keys: RedisKeySpace,
    players: list[dict],
) -> set[int]:
    """Users with MajikHil active tonight."""
    from app.managers.magic_effects import heal_field

    redis = await get_redis()
    flags = keys.game_flags(chat_id)
    out: set[int] = set()
    for p in players:
        uid = int(p["user_id"])
        if await redis.hget(flags, heal_field(uid)):
            out.add(uid)
    return out


async def _magic_ghosts(
    chat_id: int,
    keys: RedisKeySpace,
    players: list[dict],
) -> set[int]:
    """Users hidden by MajikGhost."""
    from app.managers.magic_effects import ghost_field

    redis = await get_redis()
    flags = keys.game_flags(chat_id)
    out: set[int] = set()
    for p in players:
        uid = int(p["user_id"])
        if await redis.hget(flags, ghost_field(uid)):
            out.add(uid)
    return out
