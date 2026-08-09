"""Default heuristic AI agent implementation."""

from __future__ import annotations

from typing import Any

from AI.base_agent import BaseAgent
from AI import brain
from AI.registry import AgentRegistry


class HeuristicAgent(BaseAgent):
    """Rule-based agent for night/day/vote."""

    def __init__(self, user_id: int, name: str) -> None:
        super().__init__(user_id, name)
        self._cfg = AgentRegistry().config

    def decide_night(
        self,
        snapshot: dict[str, Any],
    ) -> str | None:
        """Night action from role heuristics."""
        return brain.night_choice(
            snapshot,
            float(self._cfg["night_yes_chance"]),
        )

    def decide_day(
        self,
        snapshot: dict[str, Any],
    ) -> str | None:
        """Day action from role heuristics."""
        return brain.day_choice(
            snapshot,
            float(self._cfg["immediate_yes_chance"]),
            float(self._cfg["gunner_shoot_chance"]),
            float(self._cfg["spy_act_chance"]),
        )

    def decide_vote(
        self,
        snapshot: dict[str, Any],
    ) -> int | None:
        """Vote target heuristic."""
        return brain.vote_choice(snapshot)

    def decide_sheriff_shot(
        self,
        snapshot: dict[str, Any],
    ) -> int | None:
        """Sheriff death-shot: random other."""
        return brain.pick_random_id(
            brain.alive_others(
                snapshot,
                int(snapshot["self_id"]),
            )
        )
