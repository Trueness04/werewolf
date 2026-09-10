"""Nix algorithm — Onyx medal tiering (Amin 0904 spec).

Medals are awarded purely on games_played (and wins for the
top tiers). Rendered inline in player lists; also used to
block users from picking reserved emojis as custom emoji.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.database.models.user import UserRow
from app.database.session import session_scope

# Reserved emoji: role emojis + medal emojis are NOT
# custom-emoji candidates — the picker must refuse them.
RESERVED_EMOJI: frozenset[str] = frozenset(
    (
        "1st.place",
        "smile.face",
        "skull",
        "dagger6",
        "tomb6",
        "scroll7",
        "swords7",
        "shield7",
        "crown7",
        "trophy7",
        "amphora7",
        "mirror7",
        "fire7",
        "moon7",
        "sun7",
        "eagle7",
        "hamsa8",
    )
)


# Tier ladder: min games → medal emoji + label key.
# Games-only tiers: نذار | شمشیر | کتیبه | طلا | ستون.
# Win-capped tiers: نثرنگار | تندیس — need wins too.
MEDAL_TIERS: tuple[dict[str, Any], ...] = (
    {
        "key": "medal_none",
        "emoji": ".",
        "min_games": 0,
        "min_wins": 0,
    },
    {
        "key": "medal_sword",
        "emoji": "d",
        "min_games": 10,
        "min_wins": 0,
    },
    {
        "key": "medal_tablet",
        "emoji": "tomb",
        "min_games": 30,
        "min_wins": 0,
    },
    {
        "key": "medal_gold",
        "emoji": "scroll.msg",
        "min_games": 60,
        "min_wins": 5,
    },
    {
        "key": "medal_pillar",
        "emoji": "hall",
        "min_games": 100,
        "min_wins": 10,
    },
    {
        "key": "medal_scribe",
        "emoji": "crown.msg",
        "min_games": 150,
        "min_wins": 25,
    },
    {
        "key": "medal_statue",
        "emoji": "trophy.msg",
        "min_games": 250,
        "min_wins": 50,
    },
)


async def user_medal(
    user_id: int,
) -> tuple[str, str]:
    """Return (emoji, label_key) for a user's games/wins.

    DB-missing users get the empty medal (medal_none).
    """
    games = 0
    wins = 0
    async with session_scope() as session:
        row = (
            await session.execute(
                select(UserRow).where(
                    UserRow.user_id == user_id
                )
            )
        ).scalar_one_or_none()
        if row is not None:
            games = int(row.games_played or 0)
            wins = int(row.wins or 0)
    return medal_for(games, wins)


def medal_for(
    games: int,
    wins: int,
) -> tuple[str, str]:
    """Pure tier resolution (testable without DB)."""
    best = MEDAL_TIERS[0]
    for tier in MEDAL_TIERS:
        if games >= int(tier["min_games"]) and wins >= int(
            tier["min_wins"]
        ):
            best = tier
    return str(best["emoji"]), str(best["key"])


def is_reserved_emoji(text: str) -> bool:
    """True if any char is a reserved role/medal emoji."""
    reserved_codepoints = frozenset(
        chr(0x1F947)
        + chr(0x26AB)
        + chr(0x1F642)
        + chr(0x2620)
    )
    return any(
        ch in RESERVED_EMOJI or ch in reserved_codepoints
        for ch in text
    )
