"""Wire day/vote/lynch/night phase callables."""

from __future__ import annotations

from app.managers.chat_bridge import ChatBridge
from app.managers.day_manager import DayManager
from app.managers.day_resolver import DayResolver
from app.managers.lynch_resolver import LynchResolver
from app.managers.night_manager import NightManager
from app.managers.vote_manager import VoteManager


def build_day_pipeline(
    bridge: ChatBridge,
) -> tuple[DayManager, DayResolver, VoteManager]:
    """Create linked day -> vote -> lynch -> night."""
    day = DayManager(bridge)
    vote = VoteManager(bridge)
    lynch = LynchResolver(bridge)
    night = NightManager(bridge)
    resolver = DayResolver(bridge)

    async def start_vote(chat_id: int) -> None:
        await vote.start_vote(chat_id)

    async def do_lynch(
        chat_id: int,
        winner_id: int | None,
        peace: bool = False,
    ) -> None:
        await lynch.resolve(
            chat_id,
            winner_id=winner_id,
            peace=peace,
        )

    async def start_next_night(chat_id: int) -> None:
        await night.start_night(chat_id)

    resolver.set_vote_starter(start_vote)
    vote.set_lynch(do_lynch)
    lynch.set_night_starter(start_next_night)
    return day, resolver, vote
