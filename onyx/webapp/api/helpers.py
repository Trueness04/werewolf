"""Shared helpers for webapp routes."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select

from app.config.paths import CONFIG_DATA
from app.database.models.user import UserRow
from app.database.session import session_scope


SHOP_PATH = CONFIG_DATA / "webapp_shop.json"
ICONS_PATH = CONFIG_DATA / "webapp_icons.json"
META_PATH = CONFIG_DATA / "webapp_meta.json"
ACHIEVEMENTS_PATH = (
    CONFIG_DATA / "webapp_achievements.json"
)


def load_shop() -> dict:
    return json.loads(
        Path(SHOP_PATH).read_text(encoding="utf-8")
    )


def load_icons() -> dict:
    return json.loads(
        Path(ICONS_PATH).read_text(encoding="utf-8")
    )


def load_meta() -> dict:
    return json.loads(
        Path(META_PATH).read_text(encoding="utf-8")
    )


def load_achievements() -> dict:
    return json.loads(
        Path(ACHIEVEMENTS_PATH).read_text(
            encoding="utf-8"
        )
    )


async def ensure_user(tg: dict) -> UserRow:
    """Upsert user from Telegram WebApp payload."""
    uid = int(tg["id"])
    name = str(
        tg.get("first_name")
        or tg.get("username")
        or uid
    )
    uname = tg.get("username")
    async with session_scope() as session:
        row = await session.get(UserRow, uid)
        if row is None:
            row = UserRow(
                user_id=uid,
                fullname=name,
                coins=0,
                xp=0,
                rank=1,
                username=uname,
            )
            session.add(row)
            await session.flush()
        else:
            row.fullname = name
            if uname:
                row.username = str(uname)
        await session.refresh(row)
        return row


def public_profile(row: UserRow) -> dict:
    """Public profile fields (coins+stats visible)."""
    return {
        "user_id": int(row.user_id),
        "fullname": row.fullname,
        "username": row.username,
        "coins": int(row.coins),
        "xp": int(row.xp),
        "rank": int(row.rank),
        "games_played": int(row.games_played),
        "wins": int(row.wins),
        "bio": row.bio or "",
    }


async def get_user(uid: int) -> UserRow | None:
    async with session_scope() as session:
        return await session.get(UserRow, uid)


async def list_users_by_rank(
    limit: int = 50,
) -> list[UserRow]:
    async with session_scope() as session:
        stmt = (
            select(UserRow)
            .order_by(
                UserRow.rank.desc(),
                UserRow.xp.desc(),
            )
            .limit(limit)
        )
        return list(
            (await session.execute(stmt)).scalars()
        )
