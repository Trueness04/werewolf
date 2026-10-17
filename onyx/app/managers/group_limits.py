"""Resolve max players for a group."""

from __future__ import annotations

from app.config.settings import Settings

_ABS_MIN = 6
_ABS_MAX = 60


def max_players_of(
    group: object,
    settings: Settings,
) -> int:
    """Group override or env MAX_PLAYERS (6…60)."""
    raw = getattr(group, "max_players", None)
    try:
        value = int(raw or 0)
    except (TypeError, ValueError):
        value = 0
    if value <= 0:
        value = int(settings.max_players)
    return max(_ABS_MIN, min(_ABS_MAX, value))


def clamp_max_players(value: int) -> int:
    """Clamp a configured ceiling into 6…60."""
    return max(_ABS_MIN, min(_ABS_MAX, int(value)))
