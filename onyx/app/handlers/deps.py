"""Shared handler dependencies and helpers."""

from __future__ import annotations

from importlib import import_module

from telegram import Update
from telegram.ext import ContextTypes

from app.cache.redis_keys import RedisKeySpace
from app.config.paths import COMMANDS_JSON, URL_TEMPLATES
from app.config.settings import get_settings
from app.managers.ban_manager import BanManager
from app.managers.chat_bridge import ChatBridge
from app.managers.game_state_manager import (
    GameStateManager,
)
from app.managers.json_loader import load_json
from app.managers.lobby_manager import LobbyManager
from app.managers.role_setup_manager import (
    RoleSetupManager,
)
from app.managers.text_managers import TextManager

_get_mode = import_module("app.class.game_mode").get_mode


def texts() -> TextManager:
    """Return TextManager instance."""
    return TextManager()


def settings():
    """Return app settings."""
    return get_settings()


def lang_of(update: Update) -> str:
    """Resolve language for game texts (bot default)."""
    # Do not use Telegram client language_code; it
    # mixes EN PV replies into FA groups.
    _ = update
    return get_settings().default_lang


def group_lang(group: object | None = None) -> str:
    """Language for group chat messages (bot default)."""
    _ = group
    return get_settings().default_lang


def bridge(context: ContextTypes.DEFAULT_TYPE) -> ChatBridge:
    """Build ChatBridge from context bot."""
    return ChatBridge(context.bot)


def join_url(chat_id: int) -> str:
    """Build join deeplink for a chat."""
    cfg = get_settings()
    urls = load_json(URL_TEMPLATES)
    cmds = load_json(COMMANDS_JSON)
    prefix = str(cmds["start_payload_prefix"])
    return str(urls["join_deeplink"]).format(
        bot=cfg.bot_username,
        prefix=prefix,
        chat_id=chat_id,
    )


def mode_for_command(command: str) -> str:
    """Map /command to mode name via commands.json."""
    raw = load_json(COMMANDS_JSON)
    mapping = raw["start_commands"]
    return str(mapping[command])


async def ban_block(
    update: Update,
    user_id: int,
    language: str,
    context: ContextTypes.DEFAULT_TYPE | None = None,
) -> bool:
    """Send ban PV message; True if blocked."""
    manager = BanManager(texts())
    result = await manager.check_ban(user_id, language)
    if not result.blocked:
        return False
    msg = manager.format_message(result, language)
    if msg and context is not None:
        await context.bot.send_message(
            chat_id=user_id,
            text=msg,
        )
    return True


def state_mgr() -> GameStateManager:
    """GameStateManager factory."""
    return GameStateManager(RedisKeySpace())


def lobby_mgr() -> LobbyManager:
    """LobbyManager factory."""
    return LobbyManager()


def roles_mgr() -> RoleSetupManager:
    """RoleSetupManager factory."""
    return RoleSetupManager()


def get_mode(name: str):
    """Proxy to game_mode.get_mode."""
    return _get_mode(name)
