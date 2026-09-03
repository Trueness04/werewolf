"""User wallet helpers (bot; shop on webapp)."""

from __future__ import annotations

from sqlalchemy import select

from app.database.models.user import UserRow
from app.database.session import session_scope


async def get_user_coins(user_id: int) -> int:
    """Read user coin balance from PostgreSQL."""
    async with session_scope() as session:
        stmt = select(UserRow).where(
            UserRow.user_id == user_id
        )
        row = (
            await session.execute(stmt)
        ).scalar_one_or_none()
    if row is None:
        return 0
    return int(row.coins)


async def deduct_coins(
    user_id: int,
    amount: int,
) -> bool:
    """Deduct coins; False if insufficient."""
    async with session_scope() as session:
        stmt = select(UserRow).where(
            UserRow.user_id == user_id
        )
        row = (
            await session.execute(stmt)
        ).scalar_one_or_none()
        if row is None or row.coins < amount:
            return False
        row.coins = int(row.coins) - amount
    return True


async def add_coins(user_id: int, amount: int) -> None:
    """Add coins to user balance."""
    async with session_scope() as session:
        stmt = select(UserRow).where(
            UserRow.user_id == user_id
        )
        row = (
            await session.execute(stmt)
        ).scalar_one_or_none()
        if row is None:
            return
        row.coins = int(row.coins) + int(amount)

