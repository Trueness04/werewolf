"""Handler registration (split of main)."""

from __future__ import annotations

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.config.paths import COMMANDS_JSON
from app.config.settings import get_settings
from app.handlers.ai_toggle import ai_command
from app.handlers.challenge import (
    challenge_force,
    start_challenge,
)
from app.handlers.config_handler import (
    config_callback,
    config_command,
    config_pattern,
)
from app.handlers.day_action_handler import (
    day_callback,
    day_callback_pattern,
)
from app.handlers.dodge_handler import (
    dodge_day_callback,
    dodge_day_pattern,
    dodge_vote_callback,
    dodge_vote_pattern,
)
from app.handlers.economy import (
    coin_pack_command,
    mycoin_command,
    sendcoin_command,
    shop_command,
)
from app.handlers.extend import extend_join
from app.handlers.flee import flee_join
from app.handlers.force_start import force_start
from app.handlers.hotfix_handler import hotfix_command
from app.handlers.join_game import (
    join_command,
    start_payload_join,
)
from app.handlers.kill_game import kill_game
from app.handlers.magic_handler import (
    magic_callback,
    magic_callback_pattern,
)
from app.handlers.meta_play import (
    achievement_command,
    myhero_command,
    onlinegame_command,
)
from app.handlers.mode_info import mode_info
from app.handlers.night_action_handler import (
    night_callback,
    night_callback_pattern,
)
from app.handlers.next_game import (
    cancel_next_callback,
    cancel_next_pattern,
    next_game_command,
)
from app.handlers.players_list import players_list
from app.handlers.senior_handler import (
    senior_callback,
    senior_callback_pattern,
)
from app.handlers.smite_handler import smite_command
from app.handlers.start_game import start_game_entry
from app.handlers.sudo_handler import sudo_command
from app.handlers.vote_action_handler import (
    black_revenge_callback,
    black_revenge_pattern,
    darneshan_pick_callback,
    darneshan_pick_pattern,
    sheriff_callback_pattern,
    sheriff_shot_callback,
    vote_callback,
    vote_callback_pattern,
)
from app.managers.json_loader import load_json
from app.managers.logger_manager import get_logger


def _cmd(
    app,
    cmds: dict,
    key: str,
    handler,
) -> None:
    """Register a command handler from cmds dict."""
    app.add_handler(CommandHandler(str(cmds[key]), handler))


def _cbq(app, handler, pattern_fn) -> None:
    """Register a CallbackQueryHandler."""
    app.add_handler(
        CallbackQueryHandler(handler, pattern=pattern_fn())
    )


def _register_handlers(app) -> None:
    """Register lobby/night/day/vote handlers."""
    cmds = load_json(COMMANDS_JSON)
    for cmd in cmds["start_commands"]:
        app.add_handler(CommandHandler(cmd, start_game_entry))
    app.add_handler(CommandHandler("start", start_payload_join))
    _cmd(app, cmds, "join", join_command)
    _cmd(app, cmds, "flee", flee_join)
    _cmd(app, cmds, "force_start", force_start)
    _cmd(app, cmds, "extend", extend_join)
    _cmd(app, cmds, "players", players_list)
    _cmd(app, cmds, "kill_game", kill_game)
    _cmd(app, cmds, "mode_info", mode_info)
    _cmd(app, cmds, "next_game", next_game_command)
    _cmd(app, cmds, "config", config_command)
    _cmd(app, cmds, "start_challenge", start_challenge)
    _cmd(app, cmds, "challenge_force", challenge_force)
    _cmd(app, cmds, "mycoin", mycoin_command)
    _cmd(app, cmds, "sendcoin", sendcoin_command)
    _cmd(app, cmds, "shop", shop_command)
    _cmd(app, cmds, "coin", coin_pack_command)
    _cmd(app, cmds, "sudo", sudo_command)
    _cmd(app, cmds, "ai_toggle", ai_command)
    _cmd(app, cmds, "hotfix", hotfix_command)
    _cmd(app, cmds, "smite", smite_command)
    _cmd(app, cmds, "myhero", myhero_command)
    _cmd(app, cmds, "achievement", achievement_command)
    _cmd(app, cmds, "onlinegame", onlinegame_command)
    _cbq(app, night_callback, night_callback_pattern)
    _cbq(app, magic_callback, magic_callback_pattern)
    _cbq(app, day_callback, day_callback_pattern)
    _cbq(app, vote_callback, vote_callback_pattern)
    _cbq(app, sheriff_shot_callback, sheriff_callback_pattern)
    _cbq(app, black_revenge_callback, black_revenge_pattern)
    _cbq(app, darneshan_pick_callback, darneshan_pick_pattern)
    _cbq(app, dodge_day_callback, dodge_day_pattern)
    _cbq(app, dodge_vote_callback, dodge_vote_pattern)
    _cbq(app, config_callback, config_pattern)
    _cbq(app, senior_callback, senior_callback_pattern)
    _cbq(app, cancel_next_callback, cancel_next_pattern)
    if get_settings().debug_mode:
        app.add_handler(
            MessageHandler(filters.COMMAND, _debug_unhandled_command),
            group=99,
        )


async def _debug_unhandled_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Log commands that no handler answered."""
    _ = context
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return
    get_logger().info(
        "cmd_seen chat={c} text={t}",
        c=chat.id,
        t=msg.text,
    )
