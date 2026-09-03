"""ORM model for game history records."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class GameRow(Base):
    """Persisted game row (not live state)."""

    __tablename__ = "games"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    chat_id: Mapped[int] = mapped_column(BigInteger)
    mode: Mapped[str] = mapped_column(String(32))
    starter_id: Mapped[int] = mapped_column(BigInteger)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
    )
    status: Mapped[str] = mapped_column(String(32))
    state: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    night_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )
    day_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )
    timer: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
