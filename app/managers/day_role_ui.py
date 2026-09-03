"""Day role DM prompt + keyboard helpers."""

from __future__ import annotations

from typing import Any

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.keyboards.inline.day_keyboard import (
    build_day_target_keyboard,
    build_day_yes_no,
)
from app.managers.chat_bridge import ChatBridge
from app.managers.special_teams import (
    alive_targets_hide_bride,
)
from app.managers.text_managers import TextManager

_PROMPT_MAP = {
    "role_Solh": ("solh_L", "solh_btnY", "solh_btnN"),
    "role_Kadkhoda": (
        "Kadkhoda_l",
        "Kadkhoda_btn",
        "Kadkhoda_cancel",
    ),
    "role_Ahangar": (
        "ahangar_L",
        "ahangar_btnY",
        "ahangar_btn",
    ),
    "role_KhabGozar": (
        "KHABGOZAR_l",
        "KHABGOZAR_BTN",
        "KHABGOZAR_BTN_N",
    ),
    "role_trouble": (
        "Asktrouble",
        "trouble_yes",
        "trouble_no",
    ),
    "role_Ruler": (
        "RulerAsk",
        "Ruler_btnY",
        "Ruler_btnN",
    ),
    "role_davina": (
        "DavinaAsk",
        "Davina_btnY",
        "Davina_btnN",
    ),
    "role_BeladMoon": (
        "AskBeladMoon",
        "BeladMoon_btnY",
        "BeladMoon_btnN",
    ),
}


async def send_day_role_ui(
    bridge: ChatBridge,
    texts: TextManager,
    keys: RedisKeySpace,
    chat_id: int,
    uid: int,
    role_id: str,
    ttype: str,
    lang: str,
    players: list[dict[str, Any]],
) -> None:
    """DM day prompt + keyboard for one role."""
    if ttype == "yes_no" and role_id in _PROMPT_MAP:
        pkey, ykey, nkey = _PROMPT_MAP[role_id]
        prompt = texts.get(pkey, lang, bundle="day")
        markup = build_day_yes_no(
            texts,
            lang,
            chat_id,
            uid,
            ykey,
            nkey,
        )
        await bridge.send_text(
            uid,
            prompt,
            reply_markup=markup,
        )
        return
    if ttype != "single_target":
        return
    if role_id == "role_tofangdar":
        bullets = await _gunner_bullets(keys, chat_id)
        prompt = texts.get(
            "gunner_prompt",
            lang,
            bullets,
            bundle="day",
        )
    elif role_id == "role_BlackKnight":
        prompt = texts.get(
            "BlackKnightAsk",
            lang,
            bundle="day",
        )
    elif role_id == "role_dian":
        prompt = texts.get(
            "AskDianDay",
            lang,
            bundle="day",
        )
    else:
        prompt = texts.get(
            "spy_prompt",
            lang,
            bundle="day",
        )
    targets = alive_targets_hide_bride(players, uid)
    from app.managers.magic_targets import (
        without_magic_ghosts,
    )

    targets = await without_magic_ghosts(
        chat_id,
        targets,
        keys,
    )
    if role_id == "role_dian":
        targets = [
            t
            for t in targets
            if not any(
                int(p["user_id"]) == t[0]
                and p.get("role")
                in {
                    "role_BlackKnight",
                    "role_BrideTheDead",
                    "role_dian",
                }
                for p in players
            )
        ]
    markup = build_day_target_keyboard(
        chat_id,
        uid,
        targets,
    )
    await bridge.send_text(
        uid,
        prompt,
        reply_markup=markup,
    )


async def _gunner_bullets(
    keys: RedisKeySpace,
    chat_id: int,
) -> int:
    """Read remaining gunner bullets from flags."""
    redis = await get_redis()
    raw = await redis.hget(
        keys.game_flags(chat_id),
        keys.field("gunner_bullets"),
    )
    try:
        return int(raw or "2")
    except ValueError:
        return 2
