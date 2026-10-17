"""BeladMoon day announce → BloodMoon night lock (PN-10)."""

from __future__ import annotations

from typing import Any

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.managers.chat_bridge import ChatBridge
from app.managers.text_managers import TextManager

# Night resolution steps suppressed on blood moon.
BLOOD_MOON_BURN_STEPS: dict[str, str] = {
    "wolf_team": "BeladMoonWolfBurn",
    "check_beta_wolf": "BeladMoonWolfBurn",
    "check_ice_wolf": "BeladMoonWolfBurn",
    "check_white_wolf": "BeladMoonWolfBurn",
    "get_killer": "BeladMoonKillerBurn",
    "check_archer": "BeladMoonKillerBurn",
    "cult_hunter": "BeladMoonVillageBurn",
    "cult_invite": "BeladMoonCultBurn",
    "check_dar_neshan": "BeladMoonCultBurn",
    "check_firefighter": "BeladMoonFireBurn",
    "check_magento": "BeladMoonFireBurn",
    "check_ice_queen": "BeladMoonFireBurn",
    "check_lilis": "BeladMoonFireBurn",
    "check_bride": "BeladMoonBlackBurn",
    "get_angel": "BeladMoonVillageBurn",
    "check_honey": "BeladMoonWolfBurn",
    "check_enchanter": "BeladMoonWolfBurn",
    "check_sorcerer": "BeladMoonWolfBurn",
    "natasha_visit": "BeladMoonVillageBurn",
    "check_huntsman": "BeladMoonVillageBurn",
    "check_ghost": "BeladMoonVillageBurn",
    "check_mouse": "BeladMoonVillageBurn",
    "check_augur": "BeladMoonVillageBurn",
    "seer_result": "BeladMoonVillageBurn",
    "check_fool": "BeladMoonVillageBurn",
    "check_phoenix": "BeladMoonVillageBurn",
    "check_chemist": "BeladMoonVillageBurn",
    "check_cow": "BeladMoonVillageBurn",
    "check_babr": "BeladMoonVillageBurn",
    "check_negative": "BeladMoonVillageBurn",
    "check_knight": "BeladMoonVillageBurn",
    "check_franc": "BeladMoonCultBurn",
    "lucifer_team": "BeladMoonVillageBurn",
    "check_joker": "BeladMoonVillageBurn",
    "check_harley": "BeladMoonVillageBurn",
    "check_dynamite": "BeladMoonVillageBurn",
    "check_thief": "BeladMoonVillageBurn",
    "check_watermelon": "BeladMoonVillageBurn",
    "check_bard": "BeladMoonVillageBurn",
}

# Roles that still get night keyboards on blood moon.
BLOOD_MOON_ALLOWED_ROLES = {
    "role_vampire",
    "role_BeladMoon",
    "role_chiang",
    "role_Kent",
    "role_Bloodthirsty",
}


def blood_moon_active(ctx: dict[str, Any]) -> bool:
    """True when this night is the blood moon night."""
    return bool(ctx.get("blood_moon_active"))


def burn_if_blood_moon(
    ctx: dict[str, Any],
    step: str,
) -> bool:
    """If blood moon and step suppressed, queue burn DMs."""
    if not blood_moon_active(ctx):
        return False
    key = BLOOD_MOON_BURN_STEPS.get(step)
    if key is None:
        return False
    for item in ctx["players"]:
        if not item.get("alive", True):
            continue
        uid = int(item["user_id"])
        if uid in ctx["deaths"]:
            continue
        raw = ctx["actions"].get(str(uid))
        if not raw:
            continue
        ctx.setdefault("dm_messages", []).append(
            (uid, key)
        )
    return True


async def activate_blood_moon_night(
    bridge: ChatBridge,
    keys: RedisKeySpace,
    texts: TextManager,
    chat_id: int,
    lang: str,
    night_no: int,
    players: list[dict[str, Any]],
) -> bool:
    """Arm blood moon for this night if scheduled. True=on."""
    redis = await get_redis()
    flags = keys.game_flags(chat_id)
    nxt = await redis.hget(
        flags,
        keys.field("blood_moon_next_night"),
    )
    scheduled = await redis.hget(
        flags,
        keys.field("blood_moon_night"),
    )
    active = False
    if nxt:
        active = True
        await redis.hdel(
            flags,
            keys.field("blood_moon_next_night"),
        )
        await redis.hset(
            flags,
            mapping={
                keys.field("blood_moon_active"): "1",
                keys.field("blood_moon_night"): str(
                    night_no
                ),
            },
        )
    elif scheduled and str(scheduled) == str(night_no):
        active = True
        await redis.hset(
            flags,
            keys.field("blood_moon_active"),
            "1",
        )
    else:
        await redis.hdel(
            flags,
            keys.field("blood_moon_active"),
        )
    if not active:
        return False
    await bridge.send_text(
        chat_id,
        texts.get(
            "BeladMoonGroupNight",
            lang,
            bundle="night",
        ),
    )
    silver = await redis.hget(
        flags,
        keys.field("silver_active"),
    )
    if silver:
        for p in players:
            if p.get("role") != "role_Ahangar":
                continue
            if not p.get("alive", True):
                continue
            await bridge.send_text(
                int(p["user_id"]),
                texts.get(
                    "BeladMoonAhangarWaste",
                    lang,
                    bundle="day",
                ),
            )
    for p in players:
        if not p.get("alive", True):
            continue
        role = str(p.get("role") or "")
        if role not in BLOOD_MOON_ALLOWED_ROLES:
            continue
        await bridge.send_text(
            int(p["user_id"]),
            texts.get(
                "BeladMoonAnnouncedTeam",
                lang,
                bundle="day",
            ),
        )
    return True


async def clear_blood_moon_after_night(
    keys: RedisKeySpace,
    chat_id: int,
) -> None:
    """Drop active blood-moon flags after resolve."""
    redis = await get_redis()
    flags = keys.game_flags(chat_id)
    await redis.hdel(
        flags,
        keys.field("blood_moon_active"),
        keys.field("blood_moon_night"),
        keys.field("blood_moon_next_night"),
    )
