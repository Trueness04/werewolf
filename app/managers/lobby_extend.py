"""Join-lobby timer extend rules (PHP ExtendToGame)."""

from __future__ import annotations

from time import time

from app.config.settings import Settings
from app.managers.lobby_manager import LobbyManager


async def apply_extend(
    lobby: LobbyManager,
    chat_id: int,
    settings: Settings,
    delta: int,
) -> int:
    """Apply extend with min-10 and join_timer cap.

    Returns seconds left after change (0 if aborted).
    """
    now = int(time())
    timer = await lobby.get_timer(chat_id)
    max_ext = int(settings.max_extend_seconds)
    if delta > max_ext:
        delta = max_ext
    if delta < -max_ext:
        delta = -max_ext
    new_timer = timer + delta
    left = new_timer - now
    if left < 10:
        new_timer = now + 10
        left = 10
    join_cap = int(settings.join_duration_seconds)
    if left > join_cap:
        new_timer = now + join_cap
        left = join_cap
    await lobby.set_timer(chat_id, new_timer)
    return left


async def bump_if_late_join(
    lobby: LobbyManager,
    chat_id: int,
    settings: Settings,
) -> int | None:
    """If ≤10s left, request +30s emergency extend."""
    now = int(time())
    timer = await lobby.get_timer(chat_id)
    left = timer - now
    if left > 10:
        return None
    return await apply_extend(
        lobby,
        chat_id,
        settings,
        30,
    )
