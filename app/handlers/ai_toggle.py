"""Sudo-only /ai command — runtime AI players switch."""

from __future__ import annotations

import json

from telegram import Update
from telegram.ext import ContextTypes

from app.integrations.ai_gate import ai_callable
from app.managers.sudo import is_sudo
from app.managers.text_managers import TextManager

_texts = TextManager()


def _load_words(key: str) -> frozenset:
    raw = _texts.get(key, "fa", bundle="ai")
    try:
        items = json.loads(raw)
        return frozenset(str(x).lower() for x in items)
    except Exception:
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
