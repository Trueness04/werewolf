"""Inline join / next-game lobby keyboards."""

from __future__ import annotations

from telegram import InlineKeyboardMarkup

from app.keyboards.keyboard_maker import inline_button
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
    button = inline_button(
        label,
        style_key="join_lobby",
        url=join_url,
    )
    return InlineKeyboardMarkup([[button]])


def build_cancel_next_keyboard(
    texts: TextManager,
    lang: str,
    callback_data: str,
) -> InlineKeyboardMarkup:
    """Cancel queued next-game wait (danger)."""
    label = texts.get(
        "cancel_nextgame_btn",
        lang,
        bundle="lobby",
    )
    button = inline_button(
        label,
        style_key="cancel_nextgame",
        callback_data=callback_data,
    )
    return InlineKeyboardMarkup([[button]])
