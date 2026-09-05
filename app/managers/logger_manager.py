"""loguru setup for app/debug/games/telegram sinks."""

from __future__ import annotations

import asyncio
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

# Bounded async queue → telegram sender; never blocks the app.
_tg_queue: asyncio.Queue | None = None
_TG_QUEUE_MAX = 200

_FMT_COMPACT = (
    "<c>{time:HH:mm:ss}</c> <b>{level.name}</b> "
    "{name}:{function} — {message}"
)


def _tg_sender_loop(queue: asyncio.Queue) -> None:
    """Drain the log queue into the Telegram log group."""

    async def _run() -> None:
        from app.cache.redis_client import get_redis  # noqa: F401

        while True:
            record = await queue.get()
            try:
                await _send_record(record)
            except Exception:
                pass  # logging must never crash the app
            finally:
                queue.task_done()

    asyncio.ensure_future(_run())


async def _send_record(record: dict[str, Any]) -> None:
    """Send one formatted record to LOG_GROUP_ID."""
    from app.config.settings import get_settings
    from telegram import Bot

    gid = get_settings().log_group_id
    if not gid:
        return
    token = str(get_settings().bot_token or "").strip()
    if not token:
        return
    text = _FMT_COMPACT.format(
        time=record["time"],
        level=record["level"],
        name=record["name"],
        function=record["function"],
        message=record["message"],
    )
    exc = record.get("exception")
    if exc:
        text += f"\n<pre>{str(exc)[-1200:]}</pre>"
    if len(text) > 3800:
        text = text[:3800] + "…"
    bot = Bot(token=token)
    await bot.send_message(
        chat_id=int(gid),
        text=text,
        parse_mode="HTML",
    )


def _add_telegram_sink(cfg: LoggingConfig) -> None:
    """Attach a queue-backed sink that mirrors logs to Telegram."""
    global _tg_queue

    def _sink(message: Any) -> None:
        global _tg_queue
        if _tg_queue is None:
            try:
                _tg_queue = asyncio.Queue(maxsize=_TG_QUEUE_MAX)
                _tg_sender_loop(_tg_queue)
            except Exception:
                return  # no running loop yet — skip
        record = message.record
        if _tg_queue.full():
            return  # drop instead of blocking the app
        _tg_queue.put_nowait(record)

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
    """Attach a rotating file sink."""
    path = directory / f"{name}.log"
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
