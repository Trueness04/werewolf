"""Two-player win branches (sprint 4)."""

from __future__ import annotations

from collections import Counter
from random import SystemRandom
from typing import Any

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace

_NO_WIN_SOLO = {
    "role_WolfJadogar",
    "role_monafeq",
    "role_Honey",
    "role_enchanter",
    "role_Chiang",
    "role_Mummy",
    "role_dinamit",
    "role_dynamite",
    "role_joker",
    "role_harley",
}


def solo_winner(player: dict[str, Any]) -> str:
    """Single survivor: nothing for no-win roles."""
    role = str(player.get("role") or "")
    if role in _NO_WIN_SOLO:
        return "nothing"
    team = str(player.get("win_team") or "rosta")
    if team in {"monafeq", "dinamit", "joker"}:
        return "nothing"
    return team


async def two_winner(
    chat_id: int,
    alive: list[dict[str, Any]],
    counts: Counter[str],
    keys: RedisKeySpace,
) -> str | None:
    """Sprint-4 ordered 2-player branch."""
    _ = counts
    redis = await get_redis()
    lovers = await redis.hget(
        keys.game_flags(chat_id),
        keys.field("lover_pair"),
    )
    if lovers:
        return "lover"
    roles = {str(p.get("role") or "") for p in alive}
    teams = {str(p["win_team"]) for p in alive}
    # Black team wipes the other
    if "black" in teams:
        return "black"
    # Fire or IceQueen lock→Firefighter if only those
    if "Firefighter" in teams and len(teams) == 1:
        return "Firefighter"
    if "Firefighter" in teams:
        return "Firefighter"
    # Kalantar + Qatel → nothing
    if "role_kalantar" in roles and "role_Qatel" in roles:
        return "nothing"
    # shekar + ferqe → village
    if "role_shekar" in roles and "role_ferqe" in roles:
        return "rosta"
    # qatel alone-ish
    if "qatel" in teams and len(teams) == 1:
        return "qatel"
    if "qatel" in teams and "role_Archer" in roles:
        return "qatel"
    if "wolf" in teams:
        return "wolf"
    if "ferqeTeem" in teams:
        return "ferqeTeem"
    if "vampire" in teams:
        # duel kalantar 30%
        if "role_kalantar" in roles:
            if SystemRandom().randrange(100) < 30:
                return "rosta"
            return "vampire"
        return "vampire"
    if len(teams) == 1:
        return next(iter(teams))
    return None

