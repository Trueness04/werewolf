"""Join-lobby timer extend rules (PHP ExtendToGame)."""

from __future__ import annotations

from time import time

from app.config.settings import Settings
from app.managers.lobby_manager import LobbyManager

# Whitelist-only extend amounts (Amin 0904).
ALLOWED_EXTENDS: tuple[int, ...] = (
    30,
    60,
    90,
    120,
    160,
    180,
    300,
)


def is_allowed_extend(delta: int) -> bool:
    """True only for whitelisted extend amounts."""
    return delta in ALLOWED_EXTENDS


def format_hms(seconds: int) -> str:
    """Render remaining seconds as HH:MM:SS."""
    seconds = max(0, int(seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def countdown_due(
    last_left: int | None,
    left: int,
) -> tuple[bool, int | None]:
    """Cadence rule for join countdown.

    x1 (>120s) every 60s, x2 (<=120s) every 30s,
    x4 (<=60s) every 15s (Amin 0904).

    Returns (announce, new_last); new_last None keeps old.
    """
    if last_left is None or left > last_left:
        return False, left
    if left <= 60:
        cadence = 15
    elif left <= 120:
        cadence = 30
    else:
        cadence = 60
    if last_left - left >= cadence:
        return True, left
    return False, None


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
