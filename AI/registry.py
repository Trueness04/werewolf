"""Dynamic import registry for AI agent classes."""

from __future__ import annotations

from importlib import import_module
from typing import Any

from AI.base_agent import BaseAgent
from app.config.paths import AI_AGENTS
from app.managers.json_loader import load_json


class AgentRegistry:
    """Create agents from config class path."""

    def __init__(self) -> None:
        self._cfg = load_json(AI_AGENTS)

    @property
    def config(self) -> dict[str, Any]:
        """Return ai_agents.json document."""
        return self._cfg

    def create(
        self,
        user_id: int,
        name: str,
        class_path: str | None = None,
    ) -> BaseAgent:
        """Instantiate configured agent class."""
        path = class_path or str(
            self._cfg["default_agent"]
        )
        module_name, _, cls_name = path.rpartition(".")
        module = import_module(module_name)
        cls = getattr(module, cls_name)
        agent = cls(user_id, name)
        if not isinstance(agent, BaseAgent):
            raise TypeError(path)
        return agent

    def make_user_id(self, index: int) -> int:
        """Stable negative id for AI seat index."""
        base = int(self._cfg["id_base"])
        return base - (index + 1)

    def make_name(self, index: int) -> str:
        """Display name for AI seat index."""
        prefix = str(self._cfg["name_prefix"])
        return f"{prefix}{index + 1}"

    def is_ai_id(self, user_id: int) -> bool:
        """True when user_id is in AI id space."""
        base = int(self._cfg["id_base"])
        return user_id <= base - 1
