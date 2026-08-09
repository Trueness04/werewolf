"""In-memory game entity for lobby/night flow."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Game:
    """Game snapshot used by managers."""

    chat_id: int
    mode: str
    game_id: int | None = None
    starter_id: int | None = None
    starter_name: str = ""
    state: str = ""
    night_count: int = 0
    day_count: int = 0
    created_at: datetime | None = None
    player_ids: list[int] = field(default_factory=list)
