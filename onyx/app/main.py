"""Application bootstrap after gatekeeper."""

from __future__ import annotations

import asyncio

from telegram import BotCommand, Update
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
from app.handlers.extend import extend_join
from app.handlers.force_start import force_start
from app.handlers.join_game import (
    join_command,
    start_payload_join,
)
from app.handlers.kill_game import kill_game
from app.handlers.night_action_handler import (
    night_callback,
    night_callback_pattern,
)
from app.handlers.players_list import players_list
from app.handlers.start_game import start_game_entry
from app.handlers.vote_action_handler import (
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


def _register_handlers(app: Application) -> None:
    """Register lobby/night/day/vote handlers."""
    cmds = load_json(COMMANDS_JSON)
    for command in cmds["start_commands"]:
        app.add_handler(
            CommandHandler(command, start_game_entry)
        )
    app.add_handler(
        CommandHandler("start", start_payload_join)
    )
    app.add_handler(
        CommandHandler(
            str(cmds["join"]),
            join_command,
        )
    )
    app.add_handler(
        CommandHandler(
            str(cmds["force_start"]),
            force_start,
        )
    )
    app.add_handler(
        CommandHandler(
            str(cmds["extend"]),
            extend_join,
        )
    )
    app.add_handler(
        CommandHandler(
            str(cmds["players"]),
            players_list,
        )
    )
    app.add_handler(
        CommandHandler(
            str(cmds["kill_game"]),
            kill_game,
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            night_callback,
            pattern=night_callback_pattern(),
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            day_callback,
            pattern=day_callback_pattern(),
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            vote_callback,
            pattern=vote_callback_pattern(),
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            sheriff_shot_callback,
            pattern=sheriff_callback_pattern(),
        )
    )
    if get_settings().debug_mode:
        app.add_handler(
            MessageHandler(
                filters.COMMAND,
                _debug_unhandled_command,
            ),
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
            await tick_ai_agents(bridge)
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


def run(settings: Settings) -> None:
    """Start telegram bot runtime."""
    setup_loguru(settings.debug_mode)
    log = get_logger()
    # Python 3.12+ may have no default loop for PTB.
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    application = (
        Application.builder()
        .token(settings.bot_token)
        .post_init(_post_init)
        .build()
    )
    application.bot_data["settings"] = settings
    _register_handlers(application)
    log.info("bot_polling_start")
    application.run_polling()
