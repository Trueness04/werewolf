"""Inline join keyboard with URL deeplink."""

from __future__ import annotations

from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup

from app.managers.text_managers import TextManager


def build_join_keyboard(
    texts: TextManager,
    lang: str,
    join_url: str,
    *,
    challenge: bool = False,
) -> InlineKeyboardMarkup:
    """Build joinToGame / JoinChallenge URL button."""
    key = "JoinChallenge" if challenge else "joinToGame"
    label = texts.get(key, lang)
    button = InlineKeyboardButton(
        text=label,
        url=join_url,
    )
    return InlineKeyboardMarkup([[button]])
