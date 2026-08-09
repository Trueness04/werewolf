"""Mighty stub role: VampireRole."""

from __future__ import annotations

from ..base_role import BaseRole


class VampireRole(BaseRole):
    """Mighty role stub; filled later."""

    async def resolve(self, ctx: dict) -> None:
        """Not implemented for Mighty yet."""
        raise NotImplementedError(self.role_id)
