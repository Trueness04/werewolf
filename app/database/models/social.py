"""Social / economy tables for webapp (PN-06…08, 11)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class PostRow(Base):
    """User post on profile + feed."""

    __tablename__ = "web_posts"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(BigInteger)
    body: Mapped[str] = mapped_column(Text)
    media_url: Mapped[str | None] = mapped_column(
        String(512),
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


class LikeRow(Base):
    """One like per user per post."""

    __tablename__ = "web_likes"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "post_id",
            name="uq_like_user_post",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(BigInteger)
    post_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("web_posts.id"),
    )


class CommentRow(Base):
    """Comment on a post."""

    __tablename__ = "web_comments"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    post_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("web_posts.id"),
    )
    user_id: Mapped[int] = mapped_column(BigInteger)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class FollowRow(Base):
    """Follow graph."""

    __tablename__ = "web_follows"
    __table_args__ = (
        UniqueConstraint(
            "follower_id",
            "followee_id",
            name="uq_follow",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    follower_id: Mapped[int] = mapped_column(BigInteger)
    followee_id: Mapped[int] = mapped_column(BigInteger)


class ReportRow(Base):
    """User report on post/comment."""

    __tablename__ = "web_reports"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    reporter_id: Mapped[int] = mapped_column(BigInteger)
    target_type: Mapped[str] = mapped_column(String(16))
    target_id: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(
        String(16),
        default="open",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class FeedEventRow(Base):
    """System feed items (rank_up, medal, …)."""

    __tablename__ = "web_feed_events"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    event_type: Mapped[str] = mapped_column(String(32))
    user_id: Mapped[int] = mapped_column(BigInteger)
    payload: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class CoinLedgerRow(Base):
    """Coin transfer / shop ledger (MF-51 product-new)."""

    __tablename__ = "web_coin_ledger"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(BigInteger)
    delta: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(64))
    ref_user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class ChallengeRow(Base):
    """Web-only challenge session."""

    __tablename__ = "web_challenges"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    title: Mapped[str] = mapped_column(String(128))
    creator_id: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(
        String(32),
        default="open",
    )
    stake: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class ChallengeMemberRow(Base):
    """Challenge membership."""

    __tablename__ = "web_challenge_members"
    __table_args__ = (
        UniqueConstraint(
            "challenge_id",
            "user_id",
            name="uq_chal_member",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    challenge_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("web_challenges.id"),
    )
    user_id: Mapped[int] = mapped_column(BigInteger)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class ShopOwnedRow(Base):
    """Owned shop items (magic packs, titles, …)."""

    __tablename__ = "web_shop_owned"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "item_id",
            name="uq_shop_owned",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(BigInteger)
    item_id: Mapped[str] = mapped_column(String(64))
    qty: Mapped[int] = mapped_column(Integer, default=1)


class HeroRow(Base):
    """Player hero profile (one per user)."""

    __tablename__ = "web_heroes"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
    )
    name: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(
        String(32),
        default="all",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class AchievementUnlockRow(Base):
    """Unlocked achievement per user."""

    __tablename__ = "web_achievement_unlocks"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "achievement_id",
            name="uq_ach_unlock",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(BigInteger)
    achievement_id: Mapped[str] = mapped_column(
        String(64),
    )
    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class TournamentRow(Base):
    """Simple coin-stake tournament lobby."""

    __tablename__ = "web_tournaments"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    title: Mapped[str] = mapped_column(String(128))
    creator_id: Mapped[int] = mapped_column(BigInteger)
    stake: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(
        String(32),
        default="open",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class TournamentMemberRow(Base):
    """Tournament membership."""

    __tablename__ = "web_tournament_members"
    __table_args__ = (
        UniqueConstraint(
            "tournament_id",
            "user_id",
            name="uq_tour_member",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    tournament_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("web_tournaments.id"),
    )
    user_id: Mapped[int] = mapped_column(BigInteger)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
