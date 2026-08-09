"""ORM model for bot users (coins, etc.)."""

from __future__ import annotations

from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class UserRow(Base):
    """Persisted user profile."""

    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )
    fullname: Mapped[str] = mapped_column(String(256))
    coins: Mapped[int] = mapped_column(Integer, default=0)
