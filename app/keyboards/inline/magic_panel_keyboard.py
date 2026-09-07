"""Inline keyboard for magic panel (پنل جادو)."""

from __future__ import annotations

from telegram import InlineKeyboardButton
from telegram import InlineKeyboardMarkup
from telegram import WebAppInfo

from app.managers.logger_manager import get_logger


def _btn(
    text: str,
    chat_id: int,
    action: str,
    value: str = "t",
) -> InlineKeyboardButton:
    """Build single mp: button — mirrors senior_keyboard._btn style."""
    if value != "t":
        data = f"mp:{chat_id}:{action}:{value}"
    else:
        data = f"mp:{chat_id}:{action}"
    return InlineKeyboardButton(text=text, callback_data=data)


def _flag(label: str, enabled: bool) -> str:
    mark = "ON" if enabled else "OFF"
    return f"{label} [{mark}]"


def build_magic_panel_keyboard(
    chat_id: int,
    enabled: bool,
    webapp_url: str = "",
) -> InlineKeyboardMarkup:
    """Magic panel switch — toggle + webapp entry, never edited.

    Callback data:
      - mp:{chat_id}:toggle  (sudo only toggle)
      - mp:{chat_id}:info    (safe no-op)
      - mp:{chat_id}:noop    (safe no-op)
    WebApp button (when webapp_url given): opens magic view.
    """
    try:
        rows: list[list[InlineKeyboardButton]] = [
            [
                _btn(
                    _flag("🔮 Magic", enabled),
                    chat_id,
                    "toggle",
                )
            ],
        ]
        url = (webapp_url or "").rstrip("/")
        if url:
            rows.append(
                [
                    InlineKeyboardButton(
                        text="🌌 Open Magic WebApp",
                        web_app=WebAppInfo(url=f"{url}/?view=magic"),
                    )
                ]
            )
        rows.append(
            [
                _btn("ℹ️ Info", chat_id, "info"),
                _btn("✕", chat_id, "noop"),
            ]
        )
        return InlineKeyboardMarkup(rows)
    except Exception as exc:
        get_logger().exception(
            "magic_panel_keyboard.py: build_magic_panel_keyboard chat={} enabled={} exc={}",
            chat_id,
            enabled,
            exc,
        )
        try:
            return InlineKeyboardMarkup(
                [
                    [_btn(_flag("Magic", enabled), chat_id, "toggle")],
                    [_btn("noop", chat_id, "noop")],
                ]
            )
        except Exception as exc2:
            get_logger().exception(
                "magic_panel_keyboard.py: build_magic_panel_keyboard fallback2 chat={} exc={}",
                chat_id,
                exc2,
            )
            return InlineKeyboardMarkup([])
