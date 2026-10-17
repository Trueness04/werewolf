"""Inline magic (مجیک) use panel after role assign."""

from __future__ import annotations

from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup

from app.config.paths import CALLBACK_TEMPLATES
from app.keyboards.keyboard_maker import inline_button
from app.managers.json_loader import load_json
from app.managers.text_managers import TextManager

# (callback type, TextManager key, BUTTON_STYLES key)
_MAGIC_BTNS = (
    ("MajiKhabar", "BtnMajikKhabar", "majik_khabar"),
    ("MajikSear", "BtnMajikSear", "majik_sear"),
    ("MajiKHil", "BtnMajikHil", "majik_hil"),
    ("MajiKGhost", "BtnMajikGhost", "majik_ghost"),
)


def build_magic_keyboard(
    texts: TextManager,
    lang: str,
    chat_id: int,
    *,
    counts: dict[str, int] | None = None,
) -> InlineKeyboardMarkup:
    """Four magic activate buttons; all styled."""
    counts = counts or {}
    tpl = load_json(CALLBACK_TEMPLATES)
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for type_id, text_key, style_key in _MAGIC_BTNS:
        n = int(counts.get(type_id, 0))
        label = texts.get(text_key, lang, n)
        cb = str(tpl["select_majik"]).format(
            chat_id=chat_id,
            type=type_id,
        )
        row.append(
            inline_button(
                label,
                style_key=style_key,
                callback_data=cb,
            )
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)
