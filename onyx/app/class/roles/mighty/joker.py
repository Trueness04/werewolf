"""Mighty role: Joker."""

from __future__ import annotations

from typing import Any

from ..base_role import BaseRole


class JokerRole(BaseRole):
    """Book-hunter solo win role."""

    async def resolve(self, ctx: dict[str, Any]) -> None:
        """Handled in NightSteps.joker_find."""
        _ = ctx
