"""Application bootstrap after gatekeeper."""

from __future__ import annotations

import asyncio
import sys
import threading
import traceback

from telegram import BotCommand, Update
from telegram.error import Forbidden
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.config.paths import COMMANDS_JSON
from app.config.settings import Settings, get_settings
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
from app.handlers.extend import extend_join
from app.handlers.flee import flee_join
from app.handlers.force_start import force_start
from app.handlers.join_game import (
    join_command,
    start_payload_join,
)
from app.handlers.kill_game import kill_game
from app.handlers.mode_info import mode_info
from app.handlers.next_game import (
    cancel_next_callback,
    cancel_next_pattern,
    next_game_command,
)
from app.handlers.challenge import (
    challenge_force,
    start_challenge,
)
from app.handlers.economy import (
    coin_pack_command,
    mycoin_command,
    sendcoin_command,
    shop_command,
)
from app.handlers.meta_play import (
    achievement_command,
    myhero_command,
    onlinegame_command,
)
from app.handlers.sudo_handler import sudo_command
from app.handlers.config_handler import (
    config_callback,
    config_command,
    config_pattern,
)
from app.handlers.magic_handler import (
    magic_callback,
    magic_callback_pattern,
)
from app.handlers.night_action_handler import (
    night_callback,
    night_callback_pattern,
)
from app.handlers.players_list import players_list
from app.handlers.senior_handler import (
    senior_callback,
    senior_callback_pattern,
)
from app.handlers.start_game import start_game_entry
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
from app.managers.chat_bridge import ChatBridge
from app.managers.json_loader import load_json
from app.managers.logger_manager import (
    get_logger,
    setup_loguru,
)
from app.managers.phase_ticker import (
    tick_active_days,
    tick_active_nights,
    tick_active_votes,
    tick_end_checks,
)
from app.managers.timer_manager import TimerManager
from AI.runner import tick_ai_agents
from app.handlers.ai_toggle import ai_command


def _cmd(app: Application, cmds: dict, key: str, handler) -> None:
    """Register a command handler from cmds dict."""
    app.add_handler(CommandHandler(str(cmds[key]), handler))


def _cbq(app: Application, handler, pattern_fn) -> None:
    """Register a CallbackQueryHandler."""
    app.add_handler(
        CallbackQueryHandler(handler, pattern=pattern_fn())
    )


def _register_handlers(app: Application) -> None:
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


async def _post_init(app: Application) -> None:
    """Register commands + start phase tick loop."""
    settings: Settings = app.bot_data["settings"]
    cmds = load_json(COMMANDS_JSON)
    bot_cmds = [
        BotCommand(str(name), str(mode))
        for name, mode in cmds["start_commands"].items()
    ]
    bot_cmds.extend(
        [
            BotCommand("forcestart", "force start"),
            BotCommand("join", "join lobby"),
            BotCommand("players", "player list"),
            BotCommand("extend", "extend join"),
            BotCommand("killgame", "cancel game"),
        ]
    )
    await app.bot.set_my_commands(bot_cmds)
    interval = float(settings.tick_interval_seconds)
    app.bot_data["tick_task"] = asyncio.create_task(
        _tick_loop(app, interval)
    )


async def _tick_loop(
    app: Application,
    interval: float,
) -> None:
    """Async loop for join + night + day + vote."""
    log = get_logger()
    while True:
        try:
            bridge = ChatBridge(app.bot)
            await TimerManager(bridge).tick_all()
            from AI.sender import build_ai_bridge

            ai_bridge = build_ai_bridge() or bridge
            await tick_ai_agents(ai_bridge)
            await tick_end_checks(bridge)
            await tick_active_nights(bridge)
            await tick_active_days(bridge)
            await tick_active_votes(bridge)
        except Exception as exc:
            log.exception(
                "phase_tick_failed err={err}",
                err=str(exc),
            )
        await asyncio.sleep(interval)


def _fmt_exc(exc: BaseException) -> str:
    """Format exception to string."""
    fmt = traceback.format_exception(type(exc), exc, exc.__traceback__)
    return "".join(fmt).rstrip()


def _install_exception_hooks() -> None:
    """Route unhandled exceptions into loguru app.log."""
    log = get_logger()

    def _hook(etype: type, evalue: BaseException, etb: object) -> None:
        if issubclass(etype, KeyboardInterrupt):
            log.warning("keyboard_interrupt")
            return
        log.error("unhandled_exception\n{}", _fmt_exc(evalue))

    sys.excepthook = _hook

    def _thread_hook(args) -> None:
        _hook(args.exc_type, args.exc_value, args.exc_traceback)

    threading.excepthook = _thread_hook

    def _loop_handler(_loop: asyncio.AbstractEventLoop, ctx: dict) -> None:
        exc = ctx.get("exception")
        msg = ctx.get("message", "")
        if exc is not None:
            log.error("loop_exception {}\n{}", msg, _fmt_exc(exc))
        else:
            log.error("loop_error {}", msg)

    asyncio.get_event_loop().set_exception_handler(_loop_handler)


async def _telegram_error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Log PTB handler exceptions into app.log."""
    log = get_logger()
    exc = context.error
    if isinstance(exc, Forbidden):
        log.warning(
            "handler_forbidden update={} err={}",
            type(update).__name__,
            str(exc),
        )
        return
    if exc is None:
        return
    text = "".join(
        traceback.format_exception(
            type(exc),
            exc,
            exc.__traceback__,
        )
    )
    log.error(
        "handler_error update={}\n{}",
        type(update).__name__,
        text.rstrip(),
    )


def run(settings: Settings) -> None:
    """Start telegram bot runtime."""
    setup_loguru(settings.debug_mode)
    log = get_logger()
    # Python 3.12+ may have no default loop for PTB.
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    _install_exception_hooks()
    application = (
        Application.builder()
        .token(settings.bot_token)
        .post_init(_post_init)
        .build()
    )
    application.bot_data["settings"] = settings
    _register_handlers(application)
    application.add_error_handler(_telegram_error_handler)
    log.info("bot_polling_start")
    application.run_polling()
