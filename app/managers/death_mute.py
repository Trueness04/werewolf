"""Optional mute-on-death for groups."""

from __future__ import annotations

from app.managers.chat_bridge import ChatBridge
from app.managers.group_flags import group_mute_die


async def maybe_mute_on_death(
    bridge: ChatBridge,
    chat_id: int,
    user_id: int,
) -> None:
    """Restrict dead player if mute_die is on."""
    if not await group_mute_die(chat_id):
        return
    await bridge.mute_member(chat_id, user_id)
