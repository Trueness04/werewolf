"""Callback handler for magic panel (mj:chat:type)."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import CALLBACK_TEMPLATES
from app.handlers import deps
from app.handlers.callback_safe import answer_safe
from app.managers.json_loader import load_json
from app.managers.magic_effects import activate_magic
from app.managers.magic_inventory import EFFECT_TYPES


async def magic_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Activate one magic from inline panel."""
    query = update.callback_query
    if query is None or query.data is None:
        return
    user = update.effective_user
    if user is None:
        return
    await answer_safe(query)
    tpl = load_json(CALLBACK_TEMPLATES)
    prefix = str(tpl["select_majik_prefix"])
    data = query.data
    if not data.startswith(prefix):
        return
    parts = data.split(":")
    if len(parts) < 3:
        return
    try:
        chat_id = int(parts[1])
    except ValueError:
        return
    effect = parts[2]
    if effect not in EFFECT_TYPES:
        return
    lang = deps.lang_of(update)
    tm = deps.texts()
    bridge = deps.bridge()
    result = await activate_magic(
        chat_id=chat_id,
        user_id=user.id,
        effect_type=effect,
        bridge=bridge,
        texts=tm,
        lang=lang,
    )
    err_map = {
        "not_buy": "NotBuy",
        "not_in_game": "PlayerNotInGame",
        "already": "LastUserMajic",
        "dead": "NotInGameCloseKeyboard",
        "veto": "MagicVetoed",
        "bad": "NotBuy",
    }
    if result != "ok":
        key = err_map.get(result, "NotBuy")
        text = tm.get(key, lang)
        try:
            await query.edit_message_text(text)
        except Exception:
            await bridge.send_text(user.id, text)
        return
    try:
        await query.edit_message_reply_markup(
            reply_markup=None
        )
    except Exception:
        pass


def magic_callback_pattern() -> str:
    """Pattern for mj: callbacks."""
    tpl = load_json(CALLBACK_TEMPLATES)
    return str(tpl["select_majik_handler_pattern"])
