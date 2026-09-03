"""Lucifer dodge day/vote keyboard helpers."""

from __future__ import annotations

from typing import Any

from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import CALLBACK_TEMPLATES
from app.managers.chat_bridge import ChatBridge
from app.managers.json_loader import load_json
from app.managers.special_teams import (
    alive_targets_hide_bride,
)
from app.managers.text_managers import TextManager

_DODGE_DAY_ROLES = {
    "role_tofangdar",
    "role_Spy",
    "role_karagah",
    "role_Princess",
    "role_dian",
    "role_dynamite",
    "role_BlackKnight",
}


async def dodge_day_owner(
    keys: RedisKeySpace,
    chat_id: int,
    victim_id: int,
) -> int | None:
    """Lucifer uid stealing this player's day UI."""
    redis = await get_redis()
    raw = await redis.hget(
        keys.game_flags(chat_id),
        keys.field(f"dodge_day:{victim_id}"),
    )
    if not raw:
        return None
    return int(raw)


async def dodge_vote_owner(
    keys: RedisKeySpace,
    chat_id: int,
    victim_id: int,
) -> int | None:
    """Lucifer uid stealing this player's vote UI."""
    redis = await get_redis()
    raw = await redis.hget(
        keys.game_flags(chat_id),
        keys.field(f"dodge_vote:{victim_id}"),
    )
    if not raw:
        return None
    return int(raw)


async def send_day_dodge(
    bridge: ChatBridge,
    texts: TextManager,
    chat_id: int,
    lucifer_id: int,
    victim_id: int,
    role_id: str,
    lang: str,
    players: list[dict[str, Any]],
) -> None:
    """PV DodgeYou to victim; day keyboard to lucifer."""
    if role_id not in _DODGE_DAY_ROLES:
        return
    await bridge.send_text(
        victim_id,
        texts.get("DodgeYou", lang, bundle="day"),
    )
    targets = alive_targets_hide_bride(
        players,
        victim_id,
    )
    tpl = load_json(CALLBACK_TEMPLATES)
    pattern = str(tpl["dodge_day_target"])
    rows: list[list[InlineKeyboardButton]] = []
    for tid, name in targets:
        data = pattern.format(
            chat_id=chat_id,
            lucifer=lucifer_id,
            victim=victim_id,
            target=tid,
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=name,
                    callback_data=data,
                )
            ]
        )
    markup = InlineKeyboardMarkup(rows) if rows else None
    await bridge.send_text(
        lucifer_id,
        texts.get(
            "DodgeDayPrompt",
            lang,
            bundle="day",
        ),
        reply_markup=markup,
    )


async def send_vote_dodge(
    bridge: ChatBridge,
    texts: TextManager,
    chat_id: int,
    lucifer_id: int,
    victim_id: int,
    lang: str,
    players: list[dict[str, Any]],
) -> None:
    """PV DodgeYou; vote keyboard to lucifer."""
    await bridge.send_text(
        victim_id,
        texts.get("DodgeYou", lang, bundle="vote"),
    )
    targets = alive_targets_hide_bride(
        players,
        victim_id,
    )
    tpl = load_json(CALLBACK_TEMPLATES)
    pattern = str(tpl["dodge_vote_target"])
    rows: list[list[InlineKeyboardButton]] = []
    for tid, name in targets:
        data = pattern.format(
            chat_id=chat_id,
            lucifer=lucifer_id,
            victim=victim_id,
            target=tid,
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=name,
                    callback_data=data,
                )
            ]
        )
    markup = InlineKeyboardMarkup(rows) if rows else None
    await bridge.send_text(
        lucifer_id,
        texts.get(
            "DodgehowVote",
            lang,
            bundle="vote",
        ),
        reply_markup=markup,
    )
