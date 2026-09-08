"""Sudo-only /ai command — runtime AI players switch."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.integrations.ai_gate import ai_callable
from app.managers.sudo import is_sudo

AI_ON_TEXT = "سوییچ AI روشن شد ✅"
AI_OFF_TEXT = "سوییچ AI خاموش شد ⛔"
AI_STATE_ON_TEXT = "سوییچ AI روشن است ✅"
AI_STATE_OFF_TEXT = "سوییچ AI خاموش است ⛔"

_ON_WORDS = frozenset(
    {"on", "1", "yes", "روشن", "فعال"}
)
_OFF_WORDS = frozenset(
    {"off", "0", "no", "خاموش", "غیرفعال"}
)


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
    args = [
        str(item).strip().lower()
        for item in (context.args or [])
    ]
    set_to: bool | None = None
    if args and args[0] in _ON_WORDS:
        set_to = True
    elif args and args[0] in _OFF_WORDS:
        set_to = False
    if set_to is None:
        _get = ai_callable(
            "AI.registry",
            "ai_runtime_enabled",
            "ai_toggle:state",
        )
        state = bool(await _get())
        text = (
            AI_STATE_ON_TEXT
            if state
            else AI_STATE_OFF_TEXT
        )
    else:
        _set = ai_callable(
            "AI.registry",
            "set_ai_runtime_enabled",
            "ai_toggle:set",
        )
        await _set(set_to)
        text = AI_ON_TEXT if set_to else AI_OFF_TEXT
    await context.bot.send_message(
        chat_id=chat.id,
        text=text,
    )
