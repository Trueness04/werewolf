"""In-memory player entity for lobby/game flow."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Player:
    """Player snapshot including role fields."""

    user_id: int
    fullname: str
    role: str | None = None
    team: str | None = None
    alive: bool = True
