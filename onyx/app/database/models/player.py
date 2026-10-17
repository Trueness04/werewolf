"""ORM model for lobby/game players."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class PlayerRow(Base):
    """Persisted player participation row."""

    __tablename__ = "players"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    game_id: Mapped[int] = mapped_column(Integer)
    user_id: Mapped[int] = mapped_column(BigInteger)
    fullname: Mapped[str] = mapped_column(String(256))
    role: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    team: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    alive: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )
    state: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    night_action: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    join_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
