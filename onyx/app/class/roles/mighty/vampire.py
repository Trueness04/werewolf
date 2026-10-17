"""Mighty role shell: VampireRole."""

from __future__ import annotations

from ..base_role import BaseRole


class VampireRole(BaseRole):
    """Vampire; night resolve is pipeline-driven."""

    async def resolve(self, ctx: dict) -> None:
        """No-op; vampire_resolve handles the slot."""
        _ = ctx
        return None
