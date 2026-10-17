"""Load loguru sink settings from JSON."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config.paths import LOGGING_SETTINGS, LOGS_DIR
from app.managers.json_loader import load_json


@dataclass(frozen=True)
class LoggingConfig:
    """Resolved logging directories and levels."""

    app_dir: Any
    debug_dir: Any
    games_dir: Any
    rotation: str
    retention: str
    app_level: str
    debug_level: str
    games_level: str
    enqueue: bool
    debug_enabled: bool


def load_logging_config(debug_mode: bool) -> LoggingConfig:
    """Build LoggingConfig from data/config JSON."""
    raw = load_json(LOGGING_SETTINGS)
    app_sub = str(raw["app_subdir"])
    debug_sub = str(raw["debug_subdir"])
    games_sub = str(raw["games_subdir"])
    return LoggingConfig(
        app_dir=LOGS_DIR / app_sub,
        debug_dir=LOGS_DIR / debug_sub,
        games_dir=LOGS_DIR / games_sub,
        rotation=str(raw["rotation"]),
        retention=str(raw["retention"]),
        app_level=str(raw["app_level"]),
        debug_level=str(raw["debug_level"]),
        games_level=str(raw["games_level"]),
        enqueue=bool(raw["enqueue"]),
        debug_enabled=debug_mode,
    )
