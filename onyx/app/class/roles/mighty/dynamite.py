"""Dynamite role shell."""

from __future__ import annotations

from ..base_role import BaseRole


class DynamiteRole(BaseRole):
    """Dynamite; resolve is pipeline-driven."""

    async def resolve(self, ctx: dict) -> None:
        """No-op; special_teams handles the slot."""
        _ = ctx
        return None
