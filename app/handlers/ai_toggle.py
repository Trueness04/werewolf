"""Sudo-only /ai command — runtime AI players switch."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.integrations.ai_gate import ai_callable
from app.managers.sudo import is_sudo
from app.managers.text_managers import TextManager
from app.managers.logger_manager import get_logger

_texts = TextManager()


def _load_words(key: str) -> frozenset:
    """Read full word list from the ai bundle.

    TextManager.get() picks ONE random item from list
    entries, so the raw entry is resolved directly.
    """
    try:
        entry = _texts._resolve_entry(
            key,
            "fa",
            "ai",
            None,
        )
        if not isinstance(entry, list):
            return frozenset()
        return frozenset(
            str(item).lower() for item in entry
        )
    except Exception as exc:
        get_logger().warning(
            "ai_toggle.load_words.exc={}", exc
        )
        return frozenset()


async def ai_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Toggle runtime AI switch (sudo ids only)."""
    user = update.effective_user
    chat = update.effective_chat
    if user is None or chat is None:
        return
    if not is_sudo(user.id):
        return
    texts = TextManager()
    lang = "fa"
    args = [
        str(item).strip().lower()
        for item in (context.args or [])
    ]
    set_to: bool | None = None
    if args and args[0] in _load_words("ai_arg_on"):
        set_to = True
    elif args and args[0] in _load_words("ai_arg_off"):
        set_to = False
    if set_to is None:
        _get = ai_callable(
            "AI.registry",
            "ai_runtime_enabled",
            "ai_toggle:state",
        )
        state = bool(await _get())
        key = (
            "ai_state_on"
            if state
            else "ai_state_off"
        )
    else:
        _set = ai_callable(
            "AI.registry",
            "set_ai_runtime_enabled",
            "ai_toggle:set",
        )
        await _set(set_to)
        key = "ai_on" if set_to else "ai_off"
    await context.bot.send_message(
        chat_id=chat.id,
        text=texts.get(key, lang, bundle="ai"),
    )
