"""Day-phase inline keyboards."""

from __future__ import annotations

from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup

from app.config.paths import CALLBACK_TEMPLATES
from app.managers.json_loader import load_json
from app.managers.text_managers import TextManager


def build_day_target_keyboard(
    chat_id: int,
    actor_id: int,
    targets: list[tuple[int, str]],
) -> InlineKeyboardMarkup:
    """Build single-target day buttons."""
    tpl = load_json(CALLBACK_TEMPLATES)
    pattern = str(tpl["day_target"])
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


def build_day_yes_no(
    texts: TextManager,
    lang: str,
    chat_id: int,
    actor_id: int,
    yes_key: str,
    no_key: str,
) -> InlineKeyboardMarkup:
    """Build yes/no day decision buttons."""
    tpl = load_json(CALLBACK_TEMPLATES)
    yes_data = str(tpl["day_yes"]).format(
        chat_id=chat_id,
        actor=actor_id,
    )
    no_data = str(tpl["day_no"]).format(
        chat_id=chat_id,
        actor=actor_id,
    )
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text=texts.get(
                        yes_key,
                        lang,
                        bundle="day",
                    ),
                    callback_data=yes_data,
                ),
                InlineKeyboardButton(
                    text=texts.get(
                        no_key,
                        lang,
                        bundle="day",
                    ),
                    callback_data=no_data,
                ),
            ]
        ]
    )
