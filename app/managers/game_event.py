"""Structured game event logging via loguru."""

from __future__ import annotations

from typing import Any

from app.config.paths import LOG_MESSAGES
from app.managers.json_loader import load_json
from app.managers.logger_manager import get_logger


def _msg(key: str) -> str:
    """Load a log message template from JSON."""
    data = load_json(LOG_MESSAGES)
    return str(data[key])


def log_game_event(
    event: str,
    *,
    chat_id: int | None = None,
    user_id: int | None = None,
    game_id: int | None = None,
    phase: str | None = None,
    **extra: Any,
) -> None:
    """Write a game-tagged info log line."""
    log = get_logger().bind(game_event=True)
    log.info(
        _msg("game_event"),
        event=event,
        chat=chat_id,
        user=user_id,
        game=game_id,
        phase=phase,
        extra=extra,
    )


async def log_to_group(
    bridge: Any,
    text: str,
) -> None:
    """Send debug text to LOG_GROUP_ID if set."""
    from app.config.settings import get_settings

    gid = get_settings().log_group_id
    if not gid:
        return
    try:
        await bridge.send_text(int(gid), text)
    except Exception:
        pass


def log_debug_tick(
    chat_id: int,
    left_time: int,
    **extra: Any,
) -> None:
    """Debug-level timer tick log."""
    get_logger().debug(
        _msg("timer_tick"),
        chat=chat_id,
        left=left_time,
        extra=extra,
    )
