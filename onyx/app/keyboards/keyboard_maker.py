"""Generic keyboard builder + button style map."""

from __future__ import annotations

from typing import Any

from telegram import InlineKeyboardButton
from telegram import KeyboardButton

# Bot API 9.4 style values. Keys not listed → no style.
# PTB 21.x has no native style=; pass via api_kwargs.
BUTTON_STYLES: dict[str, str] = {
    "join_lobby": "success",
    "leave_lobby": "danger",
    "start_new_game": "primary",
    "force_start_confirm": "success",
    "force_start_cancel": "danger",
    "cancel_nextgame": "danger",
    "config_done": "success",
    "config_entry": "primary",
    "yes_confirm": "success",
    "no_decline": "danger",
    # Magic panel — user asked every button colored.
    "majik_khabar": "primary",
    "majik_sear": "primary",
    "majik_hil": "success",
    "majik_ghost": "success",
}


def style_api_kwargs(style_key: str) -> dict[str, Any] | None:
    """Build api_kwargs for a BUTTON_STYLES key, or None."""
    style = BUTTON_STYLES.get(style_key)
    if not style:
        return None
    return {"style": style}


def inline_button(
    text: str,
    *,
    style_key: str | None = None,
    url: str | None = None,
    callback_data: str | None = None,
) -> InlineKeyboardButton:
    """InlineKeyboardButton with optional Bot API style."""
    api_kwargs = None
    if style_key:
        api_kwargs = style_api_kwargs(style_key)
    return InlineKeyboardButton(
        text=text,
        url=url,
        callback_data=callback_data,
        api_kwargs=api_kwargs,
    )


def reply_button(
    text: str,
    *,
    style_key: str | None = None,
) -> KeyboardButton:
    """KeyboardButton with optional Bot API style."""
    api_kwargs = None
    if style_key:
        api_kwargs = style_api_kwargs(style_key)
    return KeyboardButton(
        text=text,
        api_kwargs=api_kwargs,
    )


def build_inline(
    rows: list[list[InlineKeyboardButton]],
) -> list[list[InlineKeyboardButton]]:
    """Pass-through for inline row lists."""
    return rows


def build_reply(
    rows: list[list[KeyboardButton]],
) -> list[list[KeyboardButton]]:
    """Pass-through for reply row lists."""
    return rows
