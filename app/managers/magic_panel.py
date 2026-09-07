"""Magic panel (پنل جادو) — per-player one-time PV panel."""

from __future__ import annotations

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.managers.chat_bridge import ChatBridge
from app.managers.logger_manager import get_logger
from app.managers.text_managers import TextManager
from app.config.settings import get_settings


def _magic_sent_key(chat_id: int) -> str:
    """One-time-per-player-per-game set key (runtime-built)."""
    # Final registration in redis_keys.json is orchestrator's job;
    # built at runtime from chat_id variable.
    return f"game:{chat_id}:magic_panel_sent"


async def read_magic_panel_flags(
    chat_id: int,
    keys: RedisKeySpace | None = None,
) -> dict[str, bool]:
    """Clone of read_panel_flags for MagicPanelEnabled."""
    try:
        keys = keys or RedisKeySpace()
        webapp_url = webapp_url or get_settings().webapp_url
        redis = await get_redis()
        flags = keys.game_flags(chat_id)

        async def flag(field: str, default: bool) -> bool:
            raw = await redis.hget(flags, keys.field(field))
            if raw is None:
                return default
            return str(raw) not in ("0", "false", "no", "")

        enabled = await flag("MagicPanelEnabled", True)
        return {"enabled": enabled, "MagicPanelEnabled": enabled}
    except Exception as exc:
        get_logger().exception(
            "magic_panel.py: read_magic_panel_flags chat={} exc={}",
            chat_id,
            exc,
        )
        return {"enabled": True, "MagicPanelEnabled": True}


async def send_magic_panel(
    chat_id: int,
    user_id: int,
    *,
    bridge: ChatBridge | None = None,
    texts: TextManager | None = None,
    keys: RedisKeySpace | None = None,
    lang: str | None = None,
    webapp_url: str | None = None,
) -> None:
    """Send magic panel once per player per game.

    Guard: if user_id already in sent set, return.
    On success: sadd uid. On failure (bridge.send_text returns 0): do not sadd.
    """
    try:
        keys = keys or RedisKeySpace()
        texts = texts or TextManager()
        lang = lang or get_settings().default_lang
        redis = await get_redis()
        sent_key = _magic_sent_key(chat_id)

                # Balance + magic inventory header (real data, webapp owns actions)
        try:
            from app.managers.lobby_coins import get_user_coins
            from app.managers.magic_inventory import inventory_counts
            balance = await get_user_coins(int(user_id))
            inv = await inventory_counts(int(user_id))
            inv_txt = " · ".join(
                f"{k}:{v}" for k, v in sorted(inv.items()) if v
            ) or "0"
        except Exception as exc:
            get_logger().exception(
                "magic_panel.py: send_magic_panel balance chat={} user={} exc={}",
                chat_id,
                user_id,
                exc,
            )
            balance, inv_txt = 0, "0"

# One-time guard
        try:
            is_member = await redis.sismember(sent_key, str(user_id))
        except Exception as exc:
            get_logger().exception(
                "magic_panel.py: send_magic_panel sismember chat={} user={} exc={}",
                chat_id,
                user_id,
                exc,
            )
            is_member = False
        if is_member:
            return

        # Skip AI seats (negative ids)
        if int(user_id) < 0:
            return

        flags = await read_magic_panel_flags(chat_id, keys)
        enabled = bool(flags.get("enabled", True))

        # Lazy import keyboard to avoid circular deps
        from app.keyboards.inline.magic_panel_keyboard import (
            build_magic_panel_keyboard,
        )

        markup = build_magic_panel_keyboard(
            chat_id,
            enabled,
            webapp_url=webapp_url,
            balance=balance,
            inventory=inv_txt,
        )

        # Bridge required — resolve from texts/lang if not provided
        if bridge is None:
            # No bridge available — cannot send; leave not-sadded for retry
            get_logger().warning(
                "magic_panel.py: send_magic_panel no bridge chat={} user={}",
                chat_id,
                user_id,
            )
            return

        title = texts.get("MagicPanelTitle", lang, bundle="lobby")
        body = texts.get("MagicPanelBody", lang, bundle="lobby")
        # Fallback if bundle keys missing
        if not title or title == "MagicPanelTitle":
            title = "🔮 پنل جادو"
        if not body or body == "MagicPanelBody":
            body = "جادوها را از اینجا مدیریت کن"

        text = f"<b>{title}</b>\n\n{body}"
        try:
            msg_id = await bridge.send_text(user_id, text, reply_markup=markup)
        except Exception as exc:
            get_logger().exception(
                "magic_panel.py: send_magic_panel send_text chat={} user={} exc={}",
                chat_id,
                user_id,
                exc,
            )
            return

        if not msg_id:
            # Not delivered — do not sadd so it retries later
            return

        try:
            await redis.sadd(sent_key, str(user_id))
        except Exception as exc:
            get_logger().exception(
                "magic_panel.py: send_magic_panel sadd chat={} user={} exc={}",
                chat_id,
                user_id,
                exc,
            )
    except Exception as exc:
        get_logger().exception(
            "magic_panel.py: send_magic_panel chat={} user={} exc={}",
            chat_id,
            user_id,
            exc,
        )


async def ensure_magic_panel_at_start(
    chat_id: int,
    *,
    keys: RedisKeySpace | None = None,
) -> bool:
    """Stub: check MagicPanelEnabled flag at game start.

    Returns True if panel is enabled, False otherwise.
    """
    try:
        flags = await read_magic_panel_flags(chat_id, keys)
        return bool(flags.get("enabled", True))
    except Exception as exc:
        get_logger().exception(
            "magic_panel.py: ensure_magic_panel_at_start chat={} exc={}",
            chat_id,
            exc,
        )
        return True
