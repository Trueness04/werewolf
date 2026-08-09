"""Vote-phase inline keyboards."""

from __future__ import annotations

from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup

from app.config.paths import CALLBACK_TEMPLATES
from app.managers.json_loader import load_json


def build_vote_keyboard(
    chat_id: int,
    voter_id: int,
    targets: list[tuple[int, str]],
) -> InlineKeyboardMarkup:
    """Build vote target buttons."""
    tpl = load_json(CALLBACK_TEMPLATES)
    pattern = str(tpl["vote_target"])
    rows: list[list[InlineKeyboardButton]] = []
    for uid, name in targets:
        data = pattern.format(
            chat_id=chat_id,
            voter=voter_id,
            target=uid,
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=name,
                    callback_data=data,
                )
            ]
        )
    return InlineKeyboardMarkup(rows)


def build_sheriff_shot_keyboard(
    chat_id: int,
    actor_id: int,
    targets: list[tuple[int, str]],
) -> InlineKeyboardMarkup:
    """Build sheriff death-shot target buttons."""
    tpl = load_json(CALLBACK_TEMPLATES)
    pattern = str(tpl["sheriff_shot"])
    rows: list[list[InlineKeyboardButton]] = []
    for uid, name in targets:
        data = pattern.format(
            chat_id=chat_id,
            actor=actor_id,
            target=uid,
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=name,
                    callback_data=data,
                )
            ]
        )
    return InlineKeyboardMarkup(rows)
