"""Mighty role: Harley Quinn."""

from __future__ import annotations

from typing import Any

from ..base_role import BaseRole


class HarleyRole(BaseRole):
    """Joker partner; shares book-hunt win."""

    async def resolve(self, ctx: dict[str, Any]) -> None:
        """Handled in NightSteps.joker_find."""
        _ = ctx
