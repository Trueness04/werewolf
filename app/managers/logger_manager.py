"""loguru setup for app/debug/games sinks."""

from __future__ import annotations

import sys
from typing import Any

from loguru import logger

from app.managers.logging_settings import (
    LoggingConfig,
    load_logging_config,
)

_configured = False


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
