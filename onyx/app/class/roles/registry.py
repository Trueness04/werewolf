"""Build role_id -> role class instances."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from app.config.paths import (
    ROLE_CLASS_MAP,
    ROLES_JSON,
)
from app.managers.json_loader import load_json

from .base_role import BaseRole


class RoleRegistry:
    """Loads definitions and constructs roles."""

    def __init__(self) -> None:
        raw = load_json(ROLES_JSON)
        self._defs: dict[str, dict[str, Any]] = {
            str(item["role_id"]): dict(item)
            for item in raw["roles"]
        }
        self._map = {
            str(k): str(v)
            for k, v in load_json(
                ROLE_CLASS_MAP
            ).items()
        }

    def definition(self, role_id: str) -> dict[str, Any]:
        """Return raw JSON definition for role_id."""
        return self._defs[role_id]

    def all_definitions(self) -> dict[str, dict[str, Any]]:
        """Return all role definitions."""
        return dict(self._defs)

    def create(self, role_id: str) -> BaseRole:
        """Instantiate concrete role class."""
        path = self._map[role_id]
        module_path, cls_name = path.rsplit(".", 1)
        module = import_module(module_path)
        cls = getattr(module, cls_name)
        return cls(role_id, self._defs[role_id])
