"""Build ChatBridge for the dedicated AI Telegram bot."""

from __future__ import annotations

from telegram import Bot

from app.config.settings import Settings, get_settings
from app.managers.chat_bridge import ChatBridge


def build_ai_bridge(
    settings: Settings | None = None,
) -> ChatBridge | None:
    """Return bridge for AI bot, or None if unset."""
    cfg = settings or get_settings()
    token = str(cfg.ai_bot_token or "").strip()
    if not token:
        return None
    bot = Bot(token=token)
    return ChatBridge(bot)  # type: ignore[arg-type]
