"""Sudo admin / sponsor / charge-order tables."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ChargeOrderRow(Base):
    """Rial charge order — gateway or sudo manual grant."""

    __tablename__ = "web_charge_orders"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(BigInteger)
    package_id: Mapped[str] = mapped_column(String(64))
    coins: Mapped[int] = mapped_column(Integer)
    price_toman: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
    )
    # pending | paid | failed | manual | reversed
    gateway_ref: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    actor_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class SponsorRow(Base):
    """Active sponsors (donators / packages)."""

    __tablename__ = "web_sponsors"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            name="uq_sponsor_user",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(
        String(128),
        default="اسپانسر",
    )
    amount_toman: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )
    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class AdminAuditRow(Base):
    """Audit log for sudo actions."""

    __tablename__ = "web_admin_audit"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    actor_id: Mapped[int] = mapped_column(BigInteger)
    action: Mapped[str] = mapped_column(String(64))
    target_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    detail: Mapped[str] = mapped_column(
        Text,
        default="{}",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
