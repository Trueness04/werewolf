"""Ban checks (PHP GR::CheckUserInBan)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import jdatetime
from sqlalchemy import select

from app.database.models.ban import BanRow
from app.database.session import session_scope
from app.managers.game_event import log_game_event
from app.managers.text_managers import TextManager


@dataclass(frozen=True)
class BanResult:
    """Outcome of a ban check."""

    blocked: bool
    forever: bool = False
    message_key: str | None = None
    message_args: tuple[object, ...] = ()


class BanManager:
    """Loads ban rows and formats ban messages."""

    def __init__(
        self,
        texts: TextManager | None = None,
    ) -> None:
        self._texts = texts or TextManager()

    async def check_ban(
        self,
        user_id: int,
        lang: str,
    ) -> BanResult:
        """Return ban status for a user."""
        async with session_scope() as session:
            stmt = select(BanRow).where(
                BanRow.user_id == user_id
            )
            row = (
                await session.execute(stmt)
            ).scalar_one_or_none()
        if row is None:
            return BanResult(blocked=False)
        if row.forever:
            log_game_event(
                "ban_forever",
                user_id=user_id,
            )
            return BanResult(
                blocked=True,
                forever=True,
                message_key="ban_ever",
            )
        if row.expire_at is None:
            return BanResult(blocked=False)
        now = datetime.now(timezone.utc)
        expire = row.expire_at
        if expire.tzinfo is None:
            expire = expire.replace(tzinfo=timezone.utc)
        if expire <= now:
            return BanResult(blocked=False)
        shamsi = jdatetime.datetime.fromgregorian(
            datetime=expire,
        ).strftime("%Y/%m/%d %H:%M")
        log_game_event(
            "ban_temporary",
            user_id=user_id,
        )
        return BanResult(
            blocked=True,
            forever=False,
            message_key="ban_to",
            message_args=(shamsi,),
        )

    def format_message(
        self,
        result: BanResult,
        lang: str,
    ) -> str | None:
        """Build localized ban message if blocked."""
        if not result.blocked or not result.message_key:
            return None
        return self._texts.get(
            result.message_key,
            lang,
            *result.message_args,
        )
