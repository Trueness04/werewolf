"""Game mode helpers loaded from game_modes.json."""

from __future__ import annotations

from dataclasses import dataclass

from app.config.paths import GAME_MODES
from app.managers.json_loader import load_json


@dataclass(frozen=True)
class GameModeInfo:
    """Resolved mode configuration."""

    name: str
    min_players: int
    command: str
    start_text_key: str
    needs_vampire_roles: bool
    skip_role_assign: bool


def load_modes() -> dict[str, GameModeInfo]:
    """Return all modes from config."""
    raw = load_json(GAME_MODES)
    result: dict[str, GameModeInfo] = {}
    for name, data in raw["modes"].items():
        result[str(name)] = GameModeInfo(
            name=str(name),
            min_players=int(data["min_players"]),
            command=str(data["command"]),
            start_text_key=str(data["start_text_key"]),
            needs_vampire_roles=bool(
                data["needs_vampire_roles"]
            ),
            skip_role_assign=bool(
                data["skip_role_assign"]
            ),
        )
    return result


def get_mode(name: str) -> GameModeInfo:
    """Return one mode or raise KeyError."""
    return load_modes()[name]
