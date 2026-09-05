"""Join-phase countdown warning messages."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.config.paths import WARNING_SECONDS
from app.keyboards.inline.lobby_keyboard import (
    build_join_keyboard,
)
from app.managers.chat_bridge import ChatBridge
from app.managers.json_loader import load_json
from app.managers.lobby_extend import countdown_due
from app.managers.text_managers import TextManager

TrackFn = Callable[[int, int], Awaitable[None]]
JoinUrlFn = Callable[[int], Awaitable[str]]


async def emit_join_countdown(
    bridge: ChatBridge,
    texts: TextManager,
    chat_id: int,
    left: int,
    lang: str,
    join_url: JoinUrlFn,
    track_delete: TrackFn,
    last_left: int | None = None,
) -> int | None:
    """Send cadenced join countdown with keyboard.

    Returns the new last_left to persist, or None when
    nothing was announced (keep previous state).
    """
    announce, new_last = countdown_due(last_left, left)
    if new_last is None:
        return None
    if not announce:
        # Timer baseline reset (extend bumped left): persist
        # without announcing.
        return new_last
    url = await join_url(chat_id)
    keyboard = build_join_keyboard(texts, lang, url)
    text = texts.get(
        "JoinCountdown",
        lang,
        _fmt_mmss(new_last),
    )
    mid = await bridge.send_text(
        chat_id,
        text,
        reply_markup=keyboard,
    )
    await track_delete(chat_id, mid)
    return new_last


def _fmt_mmss(seconds: int) -> str:
    """Render seconds as MM:SS."""
    seconds = max(0, int(seconds))
    minutes, secs = divmod(seconds, 60)
    return f"{minutes:02d}:{secs:02d}"


async def emit_join_warnings(
    bridge: ChatBridge,
    texts: TextManager,
    chat_id: int,
    left: int,
    lang: str,
    join_url: JoinUrlFn,
    track_delete: TrackFn,
) -> None:
    """Emit join time warnings in config windows."""
    raw = load_json(WARNING_SECONDS)
    url = await join_url(chat_id)
    keyboard = build_join_keyboard(texts, lang, url)
    for item in raw["warnings"]:
        low = int(item["min_left"])
        high = int(item["max_left"])
        if left < low or left > high:
            continue
        unit_key = str(item["unit_key"])
        seconds = int(item["seconds"])
        if bool(item["include_number"]):
            unit = texts.get(unit_key, lang, seconds)
        else:
            unit = texts.get(unit_key, lang)
        text = texts.get(
            "OnlyJoinTheGameTime",
            lang,
            unit,
        )
        mid = await bridge.send_text(
            chat_id,
            text,
            reply_markup=keyboard,
        )
        await track_delete(chat_id, mid)
