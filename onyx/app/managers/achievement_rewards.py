"""Unlock achievements + bump user stats on game end."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.database.models.social import AchievementUnlockRow
from app.database.models.user import UserRow
from app.database.session import session_scope
from app.managers.chat_bridge import ChatBridge
from app.managers.text_managers import TextManager

_WOLF_CODES = frozenset({"wolf"})
_VILLAGE_CODES = frozenset(
    {"rosta", "Firefighter"}
)


async def apply_end_stats(
    chat_id: int,
    winner: str,
    *,
    keys: RedisKeySpace | None = None,
    bridge: ChatBridge | None = None,
    texts: TextManager | None = None,
    lang: str = "fa",
) -> None:
    """Increment games/wins and unlock end-game medals."""
    if winner in ("killed", ""):
        return
    keys = keys or RedisKeySpace()
    redis = await get_redis()
    raw = await redis.get(keys.game_players(chat_id))
    players: list[dict[str, Any]] = (
        json.loads(raw) if raw else []
    )
    roles = json.loads(
        await redis.get(keys.game_roles(chat_id)) or "{}"
    )
    if not players:
        return
    texts = texts or TextManager()
    for item in players:
        uid = int(item["user_id"])
        role = str(roles.get(str(uid)) or "")
        won = _player_won(winner, role)
        unlocked = await _bump_and_unlock(uid, won, winner)
        if bridge and unlocked:
            for aid in unlocked:
                await bridge.send_text(
                    uid,
                    texts.get("AchioUnlock", lang)
                    + f"\n🏅 {aid}",
                )


def _player_won(winner: str, role: str) -> bool:
    """Best-effort team win from winner code + role id."""
    from importlib import import_module

    registry = import_module(
        "app.class.roles.registry"
    ).RoleRegistry()
    info = registry.definition(role) if role else {}
    team = str(info.get("team") or "")

    if winner in _WOLF_CODES:
        return team == "wolf"
    if winner in _VILLAGE_CODES:
        return team == "villager"
    if winner == "vampire":
        return team == "vampire"
    if winner == "ferqeTeem":
        return team == "cult"
    if winner == "monafeq":
        return role in {"role_monafeq", "role_Monafeq"}
    if winner == "qatel":
        return team == "solo" or role in {
            "role_Qatel",
            "role_Archer",
        }
    if winner == "black":
        return role == "role_BlackKnight"
    if winner == "joker":
        return role in {"role_joker", "role_harley"}
    if winner == "dinamit":
        return role == "role_dinamit"
    if winner == "lover":
        return True
    if winner == "Firefighter":
        return role in {
            "role_Firefighter",
            "role_forestQueen",
        }
    return False


async def _bump_and_unlock(
    user_id: int,
    won: bool,
    winner: str,
) -> list[str]:
    """Update UserRow counters; return new achievement ids."""
    new_ids: list[str] = []
    async with session_scope() as session:
        row = await session.get(UserRow, user_id)
        if row is None:
            row = UserRow(
                user_id=user_id,
                fullname=str(user_id),
                coins=0,
            )
            session.add(row)
            await session.flush()
        row.games_played = int(row.games_played or 0) + 1
        if won:
            row.wins = int(row.wins or 0) + 1

        async def unlock(aid: str) -> None:
            exists = (
                await session.execute(
                    select(AchievementUnlockRow).where(
                        AchievementUnlockRow.user_id
                        == user_id,
                        AchievementUnlockRow.achievement_id
                        == aid,
                    )
                )
            ).scalar_one_or_none()
            if exists:
                return
            session.add(
                AchievementUnlockRow(
                    user_id=user_id,
                    achievement_id=aid,
                )
            )
            new_ids.append(aid)

        if won and int(row.wins) == 1:
            await unlock("first_win")
        if int(row.games_played) >= 10:
            await unlock("ten_games")
        if won and winner == "wolf":
            await unlock("wolf_win")
        if won and winner in _VILLAGE_CODES and int(row.wins) >= 5:
            await unlock("loyal_villager")
    return new_ids
