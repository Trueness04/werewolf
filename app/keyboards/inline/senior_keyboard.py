"""Inline keyboard for session senior control panel."""

from __future__ import annotations

from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup

from app.config.paths import CALLBACK_TEMPLATES
from app.managers.json_loader import load_json
from app.managers.text_managers import TextManager


def _btn(
    text: str,
    chat_id: int,
    action: str,
    value: str = "t",
) -> InlineKeyboardButton:
    tpl = load_json(CALLBACK_TEMPLATES)
    data = str(tpl["senior_action"]).format(
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


def build_senior_keyboard(
    texts: TextManager,
    lang: str,
    chat_id: int,
    *,
    magic_allowed: bool,
    mute_die: bool,
    secret_vote: bool,
    vampire_on: bool,
    blood_on: bool,
    roles_locked: bool,
    kill_confirm: bool = False,
) -> InlineKeyboardMarkup:
    """PV panel «پنل کنترل بازی» for session senior."""
    t = texts.get
    if kill_confirm:
        return InlineKeyboardMarkup(
            [
                [
                    _btn(
                        t(
                            "SessionSeniorKillYes",
                            lang,
                            bundle="lobby",
                        ),
                        chat_id,
                        "kill",
                        "yes",
                    )
                ],
                [
                    _btn(
                        t(
                            "SessionSeniorKillNo",
                            lang,
                            bundle="lobby",
                        ),
                        chat_id,
                        "kill",
                        "no",
                    )
                ],
            ]
        )
    rows: list[list[InlineKeyboardButton]] = [
        [
            _btn(
                _flag(
                    t(
                        "SessionSeniorMagic",
                        lang,
                        bundle="lobby",
                    ),
                    magic_allowed,
                ),
                chat_id,
                "magic",
            )
        ],
        [
            _btn(
                _flag(
                    t(
                        "SessionSeniorMuteDie",
                        lang,
                        bundle="lobby",
                    ),
                    mute_die,
                ),
                chat_id,
                "mute",
            )
        ],
        [
            _btn(
                _flag(
                    t(
                        "SessionSeniorSecretVote",
                        lang,
                        bundle="lobby",
                    ),
                    secret_vote,
                ),
                chat_id,
                "secret",
            )
        ],
    ]
    if not roles_locked:
        rows.append(
            [
                _btn(
                    _flag(
                        t(
                            "SessionSeniorVamp",
                            lang,
                            bundle="lobby",
                        ),
                        vampire_on,
                    ),
                    chat_id,
                    "vamp",
                )
            ]
        )
        rows.append(
            [
                _btn(
                    _flag(
                        t(
                            "SessionSeniorBlood",
                            lang,
                            bundle="lobby",
                        ),
                        blood_on,
                    ),
                    chat_id,
                    "blood",
                )
            ]
        )
    rows.extend(
        [
            [
                _btn(
                    t(
                        "SessionSeniorExtend",
                        lang,
                        bundle="lobby",
                    ),
                    chat_id,
                    "extend",
                )
            ],
            [
                _btn(
                    t(
                        "SessionSeniorForce",
                        lang,
                        bundle="lobby",
                    ),
                    chat_id,
                    "force",
                )
            ],
            [
                _btn(
                    t(
                        "SessionSeniorKill",
                        lang,
                        bundle="lobby",
                    ),
                    chat_id,
                    "kill",
                    "ask",
                )
            ],
        ]
    )
    return InlineKeyboardMarkup(rows)
