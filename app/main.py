"""Application bootstrap after gatekeeper."""

from __future__ import annotations

import asyncio
import sys
import threading
import time
import traceback

from telegram import BotCommand
from telegram.error import Forbidden
from telegram.ext import (
    Application,
    ContextTypes,
)

from app.config.paths import COMMANDS_JSON
from app.config.settings import Settings
from app.main_handlers import _register_handlers
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


async def _safe_ai_tick(
    ai_bridge: object,
    log: object,
) -> None:
    """Run AI tick guarded; never break phase loop.

    Returns immediately (no-op) when the AI package is
    absent or disabled.
    """
    from app.integrations.ai_gate import maybe_run_ai

    try:
        await asyncio.wait_for(
            maybe_run_ai(
                "AI.runner",
                "tick_ai_agents",
                "main.py:_safe_ai_tick",
                ai_bridge,
            ),
            timeout=10,
        )
    except asyncio.TimeoutError:
        log.warning("ai_tick_timeout after 10s")
    except Exception as exc:
        log.warning("ai_tick_failed err={err}", err=str(exc))


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
            from app.integrations.ai_gate import ai_class

            ai_bridge = (
                ai_class(
                    "AI.sender",
                    "build_ai_bridge",
                    "main.py:_tick_loop",
                )
                or bridge
            )
            # AI on a separate task so an LLM hang
            # never stalls the phase tick loop.
            asyncio.create_task(
                _safe_ai_tick(ai_bridge, log)
            )
            await tick_end_checks(bridge)
            await tick_active_nights(bridge)
            await tick_active_days(bridge)
            await tick_active_votes(bridge)
            log.info(
                "phase_tick_ok ai_bridge_is_game={v}",
                v=(ai_bridge is bridge),
            )
        except Exception as exc:
            log.exception(
                "phase_tick_failed err={err} "
                "step=end/nights/days/votes",
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
    """Start telegram bot runtime (Conflict-resilient)."""
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
    # PTB's updater dies on a single 409 Conflict (e.g. deploy overlap
    # or any other getUpdates client). Wrap: on Conflict, wait and rerun.
    from telegram.error import Conflict as _C

    delay_s = 15
    while True:
        try:
            application.run_polling(
                drop_pending_updates=True,
                close_loop=False,
            )
            return
        except _C:
            log.warning("polling_conflict — retry in {}s", delay_s)
            time.sleep(delay_s)
        except SystemExit:
            raise
        except Exception:
            raise
