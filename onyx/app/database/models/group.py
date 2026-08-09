"""ORM model for Telegram groups."""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class GroupRow(Base):
    """Persisted group settings and status."""

    __tablename__ = "groups"

    chat_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )
    status: Mapped[str] = mapped_column(String(32))
    lang: Mapped[str] = mapped_column(String(8))
    text_mode: Mapped[str] = mapped_column(
        String(32),
        default="general",
    )
    pin_player_message: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    allow_extend: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )
    allow_flee: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )
    settext_start: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    vampire_role_on: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )
    bloodthirsty_role_on: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )
    max_players: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )
    secret_vote: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    mute_die: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
    start_gif: Mapped[str | None] = mapped_column(
        String(256),
        nullable=True,
    )
    sponsor_lock: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
    )
