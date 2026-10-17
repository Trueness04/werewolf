"""ORM model for user bans."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class BanRow(Base):
    """Persisted ban record."""

    __tablename__ = "bans"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(BigInteger)
    forever: Mapped[bool] = mapped_column(Boolean)
    expire_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
