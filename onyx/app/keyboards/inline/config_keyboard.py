"""Inline keyboard for group /config MVP."""

from __future__ import annotations

from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup

from app.config.paths import CALLBACK_TEMPLATES
from app.managers.flavor_packs import load_flavor_packs
from app.managers.json_loader import load_json
from app.managers.text_managers import TextManager


def _btn(
    text: str,
    chat_id: int,
    action: str,
    value: str,
) -> InlineKeyboardButton:
    tpl = load_json(CALLBACK_TEMPLATES)
    data = str(tpl["config_action"]).format(
        chat_id=chat_id,
        action=action,
        value=value,
    )
    return InlineKeyboardButton(
        text=text,
        callback_data=data,
    )


def _flag(label: str, enabled: bool) -> str:
    mark = "ON" if enabled else "OFF"
    return f"{label} [{mark}]"


def build_config_keyboard(
    texts: TextManager,
    lang: str,
    chat_id: int,
    *,
    allow_flee: bool,
    allow_extend: bool,
    pin: bool,
    vamp: bool,
    blood: bool,
    secret_vote: bool,
    mute_die: bool,
    max_players: int,
    text_mode: str = "general",
) -> InlineKeyboardMarkup:
    """Main config panel for group toggles."""
    t = texts.get
    flee = t("config_group_Flee", lang, bundle="lobby")
    ext = t("config_group_Extend", lang, bundle="lobby")
    pin_l = t(
        "config_group_PinMessage",
        lang,
        bundle="lobby",
    )
    max_l = t(
        "config_group_MaxPlayer",
        lang,
        bundle="lobby",
    )
    mode_l = t(
        "config_group_gameMode",
        lang,
        bundle="main",
    )
    done = t("config_done", lang, bundle="lobby")
    packs = load_flavor_packs()
    meta = packs.get(text_mode) or packs.get("general")
    dkey = str((meta or {}).get("display_key", text_mode))
    mode_name = t(dkey, lang, bundle="main")
    if mode_name == dkey:
        mode_name = text_mode
    rows = [
        [_btn(_flag(flee, allow_flee), chat_id, "flee", "t")],
        [_btn(_flag(ext, allow_extend), chat_id, "extend", "t")],
        [_btn(_flag(pin_l, pin), chat_id, "pin", "t")],
        [_btn(_flag("Vampire", vamp), chat_id, "vamp", "t")],
        [_btn(_flag("Blood", blood), chat_id, "blood", "t")],
        [
            _btn(
                _flag(
                    t(
                        "config_group_SecretVote",
                        lang,
                        bundle="lobby",
                    ),
                    secret_vote,
                ),
                chat_id,
                "secret",
                "t",
            )
        ],
        [
            _btn(
                _flag(
                    t(
                        "config_group_MuteDie",
                        lang,
                        bundle="lobby",
                    ),
                    mute_die,
                ),
                chat_id,
                "mute",
                "t",
            )
        ],
        [
            _btn(
                f"{max_l}: {max_players}",
                chat_id,
                "maxmenu",
                "1",
            )
        ],
        [
            _btn(
                f"{mode_l}: {mode_name}",
                chat_id,
                "flavor",
                "1",
            )
        ],
        [_btn(done, chat_id, "done", "1")],
    ]
    return InlineKeyboardMarkup(rows)


def build_flavor_keyboard(
    texts: TextManager,
    lang: str,
    chat_id: int,
    current: str,
) -> InlineKeyboardMarkup:
    """Pick flavor pack from flavor_packs.json."""
    packs = load_flavor_packs()
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for pack_id, meta in packs.items():
        label = texts.get(
            str(meta["display_key"]),
            lang,
            bundle="main",
        )
        if label == str(meta["display_key"]):
            label = pack_id
        mark = "✓ " if pack_id == current else ""
        row.append(
            _btn(
                f"{mark}{label}",
                chat_id,
                "setflavor",
                pack_id,
            )
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([_btn("«", chat_id, "menu", "1")])
    return InlineKeyboardMarkup(rows)


def build_max_player_keyboard(
    chat_id: int,
) -> InlineKeyboardMarkup:
    """Pick max_player preset (up to 60)."""
    opts = (15, 20, 30, 35, 45, 50, 60)
    row1 = [
        _btn(str(n), chat_id, "max", str(n))
        for n in opts[:4]
    ]
    row2 = [
        _btn(str(n), chat_id, "max", str(n))
        for n in opts[4:]
    ]
    back = _btn("«", chat_id, "menu", "1")
    return InlineKeyboardMarkup(
        [row1, row2, [back]]
    )
