"""Abstract AI agent contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """One AI seat that can decide phase actions."""

    def __init__(self, user_id: int, name: str) -> None:
        self.user_id = user_id
        self.name = name

    @abstractmethod
    def decide_night(
        self,
        snapshot: dict[str, Any],
    ) -> str | None:
        """Return night choice or None to skip."""

    @abstractmethod
    def decide_day(
        self,
        snapshot: dict[str, Any],
    ) -> str | None:
        """Return day choice or None to skip."""

    @abstractmethod
    def decide_vote(
        self,
        snapshot: dict[str, Any],
    ) -> int | None:
        """Return vote target user_id or None."""

    @abstractmethod
    def decide_sheriff_shot(
        self,
        snapshot: dict[str, Any],
    ) -> int | None:
        """Return death-shot target or None."""
