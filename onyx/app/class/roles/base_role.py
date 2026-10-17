"""Base class for all concrete game roles."""

from __future__ import annotations

from typing import Any


class BaseRole:
    """Config-backed role with night hooks."""

    def __init__(
        self,
        role_id: str,
        definition: dict[str, Any],
    ) -> None:
        self.role_id = role_id
        self._def = definition

    @property
    def team(self) -> str:
        """Return team id from role definition."""
        return str(self._def["team"])

    @property
    def night1_active(self) -> bool:
        """Whether role acts on first night."""
        return bool(self._def["night1_active"])

    @property
    def target_type(self) -> str:
        """single_target | yes_no | none."""
        return str(self._def["target_type"])

    @property
    def action_kind(self) -> str:
        """Logical action kind for resolver."""
        return str(self._def["action_kind"])

    @property
    def unique(self) -> bool:
        """Whether at most one copy may exist."""
        return bool(self._def.get("unique", False))

    @property
    def support_role(self) -> bool:
        """Village support priority flag."""
        return bool(
            self._def.get("support_role", False)
        )

    @property
    def message_keys(self) -> dict[str, Any]:
        """Localized message key map."""
        raw = self._def.get("message_keys", {})
        return dict(raw)

    @property
    def mighty_stub(self) -> bool:
        """True when Mighty behavior unfinished."""
        return bool(
            self._def.get("mighty_stub", False)
        )

    async def resolve(self, ctx: dict[str, Any]) -> None:
        """Optional per-role resolve hook."""
        _ = ctx
        return None
