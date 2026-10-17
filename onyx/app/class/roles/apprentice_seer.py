"""Role module: ApprenticeSeerRole."""

from __future__ import annotations

from .base_role import BaseRole


class ApprenticeSeerRole(BaseRole):
    """Concrete role behavior shell."""

    async def resolve(self, ctx: dict) -> None:
        """Night resolve hook (pipeline-driven)."""
        _ = ctx
        return None
