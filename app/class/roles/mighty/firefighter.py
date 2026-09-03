"""Firefighter / Magento role shell."""

from __future__ import annotations

from ..base_role import BaseRole


class FirefighterRole(BaseRole):
    """Fire team; night resolve is pipeline-driven."""

    async def resolve(self, ctx: dict) -> None:
        """No-op; fire_resolve handles the slot."""
        _ = ctx
        return None
