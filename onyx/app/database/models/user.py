"""ORM model for bot users (coins, rank, stats)."""

from __future__ import annotations

from sqlalchemy import BigInteger, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class UserRow(Base):
    """Persisted user profile (bot + webapp)."""

    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )
    fullname: Mapped[str] = mapped_column(String(256))
    coins: Mapped[int] = mapped_column(Integer, default=0)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    rank: Mapped[int] = mapped_column(Integer, default=1)
    games_played: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )
    wins: Mapped[int] = mapped_column(Integer, default=0)
    bio: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    username: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
