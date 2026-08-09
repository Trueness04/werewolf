"""Create DB schema and seed test user."""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.config.paths import ROOT
from app.config.settings import get_settings
from app.database.base import Base
from app.database.models.ban import BanRow  # noqa: F401
from app.database.models.game import GameRow  # noqa: F401
from app.database.models.group import GroupRow  # noqa: F401
from app.database.models.player import PlayerRow  # noqa: F401
from app.database.models.social import (  # noqa: F401
    AchievementUnlockRow,
    ChallengeMemberRow,
    ChallengeRow,
    CoinLedgerRow,
    CommentRow,
    FeedEventRow,
    FollowRow,
    HeroRow,
    LikeRow,
    PostRow,
    ReportRow,
    ShopOwnedRow,
    TournamentMemberRow,
    TournamentRow,
)
from app.database.models.admin import (  # noqa: F401
    AdminAuditRow,
    ChargeOrderRow,
    SponsorRow,
)
from app.database.models.user import UserRow
from app.database.session import session_scope

_BOOTSTRAP = ROOT / "data" / "config" / "bootstrap.json"


def _cfg() -> dict[str, Any]:
    """Load bootstrap config from data."""
    return json.loads(_BOOTSTRAP.read_text(encoding="utf-8"))


def _parse_user_id(argv: list[str]) -> int:
    """Require Telegram user id as CLI arg."""
    if len(argv) < 2:
        print("usage: -m app.database.bootstrap <uid>")
        raise SystemExit(2)
    return int(argv[1])


async def _ensure_database() -> None:
    """Create onyx_db if missing (connect to postgres)."""
    settings = get_settings()
    cfg = _cfg()
    admin_url = (
        "postgresql+asyncpg://"
        f"{settings.db_user}:{settings.db_password}"
        f"@{settings.db_host}:{settings.db_port}/postgres"
    )
    engine = create_async_engine(
        admin_url,
        isolation_level="AUTOCOMMIT",
    )
    async with engine.connect() as conn:
        exists = await conn.execute(
            text(str(cfg["sql_db_exists"])),
            {"name": settings.db_name},
        )
        if exists.scalar() is None:
            stmt = str(cfg["sql_create_db"]).format(
                name=settings.db_name,
            )
            await conn.execute(text(stmt))
            print("created_db", settings.db_name)
        else:
            print("db_exists", settings.db_name)
    await engine.dispose()


async def _create_tables() -> None:
    """Create all ORM tables."""
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("tables_ok")


async def _seed_user(user_id: int) -> None:
    """Ensure test user exists with coins."""
    cfg = _cfg()
    fullname = str(cfg["seed_fullname"])
    coins = int(cfg["seed_coins"])
    async with session_scope() as session:
        row = await session.get(UserRow, user_id)
        if row is None:
            session.add(
                UserRow(
                    user_id=user_id,
                    fullname=fullname,
                    coins=coins,
                )
            )
            print("user_created", user_id)
        else:
            row.coins = max(int(row.coins), coins)
            print("user_updated", user_id)



async def _ensure_group_columns() -> None:
    """Add new group columns on existing DBs."""
    settings = get_settings()
    cfg = _cfg()
    engine = create_async_engine(settings.database_url)
    stmts = (
        str(cfg["sql_add_secret_vote"]),
        str(cfg["sql_add_mute_die"]),
        str(cfg["sql_add_text_mode"]),
        "ALTER TABLE groups ADD COLUMN IF NOT EXISTS "
        "sponsor_lock BOOLEAN DEFAULT FALSE",
    )
    async with engine.begin() as conn:
        for stmt in stmts:
            await conn.execute(text(stmt))
    await engine.dispose()
    print("group_columns_ok")


async def _ensure_user_columns() -> None:
    """Add rank/xp/stats columns on existing users table."""
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    stmts = (
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS xp INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS rank INTEGER DEFAULT 1",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS games_played INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS wins INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS bio TEXT",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS username VARCHAR(128)",
        "ALTER TABLE web_reports ADD COLUMN IF NOT EXISTS "
        "status VARCHAR(16) DEFAULT 'open'",
    )
    async with engine.begin() as conn:
        for stmt in stmts:
            await conn.execute(text(stmt))
    await engine.dispose()
    print("user_columns_ok")


async def ensure_schema(*, seed_user_id: int | None = None) -> None:
    """Create DB/tables/columns; optional seed user for tests."""
    get_settings.cache_clear()
    await _ensure_database()
    await _create_tables()
    await _ensure_group_columns()
    await _ensure_user_columns()
    if seed_user_id is not None:
        await _seed_user(seed_user_id)


async def main(user_id: int) -> None:
    """Bootstrap local DB for Telegram tests."""
    await ensure_schema(seed_user_id=user_id)


if __name__ == "__main__":
    uid = _parse_user_id(sys.argv)
    asyncio.run(main(uid))



