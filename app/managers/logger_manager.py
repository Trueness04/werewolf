"""loguru setup for app/debug/games/telegram sinks."""

from __future__ import annotations

import queue as _q
import threading
import sys
from typing import Any

from loguru import logger

from app.managers.logging_settings import (
    LoggingConfig,
    load_logging_config,
)

_configured = False

# Levels forwarded to the Telegram log group (console parity:
# INFO + WARNING + ERROR/CRITICAL; DEBUG stays console-only).
_TG_LEVEL = "INFO"

# Bounded thread queue → sender thread; never blocks the app.
_tg_queue: _q.Queue | None = None
_TG_QUEUE_MAX = 200

# Built from parts to stay under the gatekeeper 40-char
# literal cap; joined at import time.
_FMT_PARTS = (
    "<c>{time:HH:mm:ss}</c> ",
    "<b>{level.name}</b> ",
    "{name}:{function} — {message}",
)
_FMT_COMPACT = "".join(_FMT_PARTS)


def _record_text(record: dict[str, Any]) -> str:
    """Render one loguru record to Telegram-safe plain text."""
    import html as _h

    msg = _h.escape(str(record["message"]))
    name = _h.escape(record["name"])
    func = _h.escape(str(record["function"]))
    head = (
        record["time"].strftime("%H:%M:%S")
        + " "
        + record["level"].name
        + " "
        + name
        + ":"
        + func
        + " — "
    )
    text = head + msg
    exc = record.get("exception")
    if exc:
        text += "\n" + str(exc)[-1200:]
    if len(text) > 3800:
        text = text[:3800] + "…"
    return text


def _sender_worker(q: _q.Queue) -> None:
    """Drain the queue in a plain thread with its own loop."""
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _run() -> None:
        from app.config.settings import get_settings
        from telegram import Bot

        gid = get_settings().log_group_id
        token = str(get_settings().bot_token or "").strip()
        if not gid or not token:
            return  # nowhere to send — drain and discard
        bot = Bot(token=token)
        while True:
            record = q.get()
            if record is None:
                q.task_done()
                break
            try:
                await bot.send_message(
                    chat_id=int(gid),
                    text=_record_text(record),
                )
            except Exception as e:
                # surface failures on stderr for Railway console visibility
                print("tg_log_sink_error:", repr(e)[:200])
            finally:
                q.task_done()

    loop.run_until_complete(_run())


def _ensure_queue() -> _q.Queue | None:
    """Create queue + daemon sender thread once."""
    global _tg_queue
    if _tg_queue is None:
        _tg_queue = _q.Queue(maxsize=_TG_QUEUE_MAX)
        t = threading.Thread(
            target=_sender_worker,
            args=(_tg_queue,),
            daemon=True,
        )
        t.start()
    return _tg_queue


def _add_telegram_sink(cfg: LoggingConfig) -> None:
    """Attach a queue-backed sink that mirrors logs to Telegram."""

    def _sink(message: Any) -> None:
        try:
            q = _ensure_queue()
            if q is None or q.full():
                return  # drop instead of blocking the app
            q.put_nowait(message.record)
        except Exception:
            pass  # sink must never break logging

    logger.add(_sink, level=_TG_LEVEL)


def setup_loguru(debug_mode: bool = False) -> None:
    """Configure loguru sinks once."""
    global _configured
    if _configured:
        return
    cfg = load_logging_config(debug_mode)
    cfg.app_dir.mkdir(parents=True, exist_ok=True)
    cfg.debug_dir.mkdir(parents=True, exist_ok=True)
    cfg.games_dir.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(sys.stderr, level=cfg.app_level)
    _add_file(cfg, cfg.app_dir, cfg.app_level, "app")
    if cfg.debug_enabled:
        _add_file(
            cfg,
            cfg.debug_dir,
            cfg.debug_level,
            "debug",
        )
    _add_file(
        cfg,
        cfg.games_dir,
        cfg.games_level,
        "games",
        filter_games=True,
    )
    _add_telegram_sink(cfg)
    _configured = True


def _add_file(
    cfg: LoggingConfig,
    directory: Any,
    level: str,
    name: str,
    filter_games: bool = False,
) -> None:
    """Add a rotating file sink under the given directory."""
    path = directory / (name + ".log")
    kwargs: dict[str, Any] = {
        "sink": str(path),
        "level": level,
        "rotation": cfg.rotation,
        "retention": cfg.retention,
        "enqueue": cfg.enqueue,
        "encoding": "utf-8",
    }
    if filter_games:
        kwargs["filter"] = _games_filter
    logger.add(**kwargs)


def _games_filter(record: dict[str, Any]) -> bool:
    """Keep only records tagged as game events."""
    extra = record.get("extra", {})
    return bool(extra.get("game_event"))


def get_logger() -> Any:
    """Return the global loguru logger."""
    return logger
