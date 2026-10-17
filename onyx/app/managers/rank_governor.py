"""Rank list + Onyx royal governor (PN-11)."""

from __future__ import annotations

from sqlalchemy import select

from app.database.models.user import UserRow
from app.database.session import session_scope


async def get_governor() -> UserRow | None:
    """Top ranked user = حکمران (rank desc, xp desc)."""
    async with session_scope() as session:
        stmt = (
            select(UserRow)
            .order_by(
                UserRow.rank.desc(),
                UserRow.xp.desc(),
            )
            .limit(1)
        )
        return (
            await session.execute(stmt)
        ).scalar_one_or_none()


async def governor_display_name() -> str:
    """Name for NewLevel announcements."""
    row = await get_governor()
    if row is None:
        return "اونیکس"
    return str(row.fullname or row.user_id)


def format_new_level(
    template: str,
    old_rank: int,
    new_rank: int,
    governor_name: str,
) -> str:
    """Fill NewLevel with ranks + live governor name."""
    text = template
    try:
        text = text.format(
            old_rank,
            new_rank,
            governor_name,
        )
    except (IndexError, KeyError, ValueError):
        text = (
            f"{template}\n"
            f"از درجه {old_rank} به {new_rank} — "
            f"به دستور {governor_name} اونیکس 👑"
        )
    return text


async def royal_family(
    limit: int = 3,
) -> list[UserRow]:
    """Top 1–3 = خاندان سلطنتی اونیکس."""
    async with session_scope() as session:
        stmt = (
            select(UserRow)
            .order_by(
                UserRow.rank.desc(),
                UserRow.xp.desc(),
            )
            .limit(limit)
        )
        rows = (
            await session.execute(stmt)
        ).scalars().all()
    return list(rows)
