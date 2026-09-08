"""AI chat-count reset (split of day_manager.py)."""

from __future__ import annotations

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace


async def reset_ai_day_counts(
    chat_id: int, keys: RedisKeySpace
) -> None:
    """Zero per-day AI chat counters via ai_gate."""
    from app.integrations.ai_gate import (
        maybe_run_ai,
    )

    await maybe_run_ai(
        "AI.talker",
        "reset_day_chat_counts",
        "day_reset.py:reset_ai_day_counts",
        chat_id,
        keys,
    )


_DAY_POWERS = {
    "role_Solh": "peace_used",
    "role_Ahangar": "silver_used",
    "role_KhabGozar": "sleep_used",
    "role_Kadkhoda": "mayor_revealed",
    "role_trouble": "trouble_used",
    "role_Ruler": "ruler_used",
    "role_davina": "davina_used",
    "role_BeladMoon": "belad_moon_used",
}


async def day_power_used(
    keys: RedisKeySpace,
    chat_id: int,
    role_id: str,
) -> bool:
    """True if one-shot day power already spent."""
    field = _DAY_POWERS.get(role_id)
    if not field:
        return False
    redis = await get_redis()
    return bool(
        await redis.hget(
            keys.game_flags(chat_id),
            keys.field(field),
        )
    )
