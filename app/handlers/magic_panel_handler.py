"""Callback handler for magic panel (پنل جادو) — mp:."""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.settings import get_settings
from app.handlers.callback_safe import answer_safe
from app.managers.logger_manager import get_logger


async def magic_panel_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle mp:chat:action callbacks — sudo toggle only, no edit/delete."""
    try:
        query = update.callback_query
        if query is None or query.data is None:
            return
        user = update.effective_user
        if user is None:
            return
        data = str(query.data)
        if not data.startswith("mp:"):
            return
        parts = data.split(":")
        if len(parts) < 3:
            try:
                await answer_safe(query)
            except Exception as exc:
                get_logger().exception(
                    "magic_panel_handler.py: magic_panel_callback answer len<3 chat=? user={} exc={}",
                    getattr(user, "id", "?"),
                    exc,
                )
            return
        try:
            chat_id = int(parts[1])
        except (ValueError, TypeError) as exc:
            get_logger().exception(
                "magic_panel_handler.py: magic_panel_callback bad chat_id data={} exc={}",
                data,
                exc,
            )
            try:
                await answer_safe(query)
            except Exception as exc2:
                get_logger().exception(
                    "magic_panel_handler.py: magic_panel_callback answer bad_chat exc={}",
                    exc2,
                )
            return

        action = parts[2]

        # Non-toggle buttons — only answer(), no state change
        if action in ("noop", "info"):
            try:
                await answer_safe(query)
            except Exception as exc:
                get_logger().exception(
                    "magic_panel_handler.py: magic_panel_callback noop/info chat={} user={} exc={}",
                    chat_id,
                    user.id,
                    exc,
                )
            return

        if action != "toggle":
            # Unknown action — safe no-op answer only
            try:
                await answer_safe(query)
            except Exception as exc:
                get_logger().exception(
                    "magic_panel_handler.py: magic_panel_callback unknown action={} chat={} exc={}",
                    action,
                    chat_id,
                    exc,
                )
            return

        # Toggle — only sudo may toggle
        try:
            sudo_set = get_settings().sudo_id_set()
        except Exception as exc:
            get_logger().exception(
                "magic_panel_handler.py: magic_panel_callback sudo_id_set chat={} exc={}",
                chat_id,
                exc,
            )
            sudo_set = set()

        if int(user.id) not in sudo_set:
            try:
                await answer_safe(query)
            except Exception as exc:
                get_logger().exception(
                    "magic_panel_handler.py: magic_panel_callback not sudo chat={} user={} exc={}",
                    chat_id,
                    user.id,
                    exc,
                )
            return

        # Sudo toggle: flip MagicPanelEnabled 0/1 via game flags hash
        try:
            keys = RedisKeySpace()
            redis = await get_redis()
            flags_key = keys.game_flags(chat_id)
            field = keys.field("MagicPanelEnabled")
            raw = await redis.hget(flags_key, field)
            # Default enabled = True if missing
            if raw is None:
                cur_enabled = True
            else:
                cur_enabled = str(raw) not in ("0", "false", "no", "")
            new_val = "0" if cur_enabled else "1"
            await redis.hset(flags_key, field, new_val)
        except Exception as exc:
            get_logger().exception(
                "magic_panel_handler.py: magic_panel_callback toggle hset chat={} user={} exc={}",
                chat_id,
                user.id,
                exc,
            )
            try:
                await answer_safe(query)
            except Exception as exc2:
                get_logger().exception(
                    "magic_panel_handler.py: magic_panel_callback answer after hset fail exc={}",
                    exc2,
                )
            return

        # Never edit or delete panel message — answer() only
        try:
            await answer_safe(query)
        except Exception as exc:
            get_logger().exception(
                "magic_panel_handler.py: magic_panel_callback answer after toggle chat={} exc={}",
                chat_id,
                exc,
            )

    except Exception as exc:
        get_logger().exception(
            "magic_panel_handler.py: magic_panel_callback unhandled exc={}",
            exc,
        )
        try:
            q = update.callback_query if "update" in locals() else None
            if q is not None:
                await answer_safe(q)
        except Exception:
            pass


def magic_panel_callback_pattern() -> str:
    """Pattern for mp: callbacks."""
    return r"^mp:"
