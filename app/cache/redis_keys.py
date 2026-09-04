"""Resolve Redis key names from config JSON."""

from __future__ import annotations

from app.config.paths import REDIS_KEYS
from app.managers.json_loader import load_json


class RedisKeySpace:
    """Builds Redis keys/fields from redis_keys.json."""

    def __init__(self) -> None:
        self._raw = load_json(REDIS_KEYS)
        self._fields: dict[str, str] = {
            str(k): str(v)
            for k, v in self._raw["fields"].items()
        }

    def game_hash(self, chat_id: int) -> str:
        """Hash key for one group lobby/game."""
        template = str(self._raw["game_hash"])
        return template.format(chat_id=chat_id)

    def active_join_chats(self) -> str:
        """Set of chats currently in join phase."""
        return str(self._raw["active_join_chats"])

    def active_night_chats(self) -> str:
        """Set of chats currently in night phase."""
        return str(self._raw["active_night_chats"])

    def active_day_chats(self) -> str:
        """Set of chats currently in day phase."""
        return str(self._raw["active_day_chats"])

    def active_vote_chats(self) -> str:
        """Set of chats currently in vote phase."""
        return str(self._raw["active_vote_chats"])

    def join_user(self, user_id: int) -> str:
        """Key marking user presence in a lobby."""
        template = str(self._raw["join_user"])
        return template.format(user_id=user_id)

    def player_join_lock(self, user_id: int) -> str:
        """Short-lived lock against double join."""
        template = str(self._raw["player_join_lock"])
        return template.format(user_id=user_id)

    def game_roles(self, chat_id: int) -> str:
        """Roles map key for a game."""
        template = str(self._raw["game_roles_key"])
        return template.format(chat_id=chat_id)

    def game_players(self, chat_id: int) -> str:
        """Players snapshot key for a game."""
        template = str(self._raw["game_players_key"])
        return template.format(chat_id=chat_id)

    def night_actions(self, chat_id: int) -> str:
        """Hash of night actions for a game."""
        template = str(self._raw["game_night_actions"])
        return template.format(chat_id=chat_id)

    def day_actions(self, chat_id: int) -> str:
        """Hash of day actions for a game."""
        template = str(self._raw["game_day_actions"])
        return template.format(chat_id=chat_id)

    def day_sent(self, chat_id: int) -> str:
        """Set of users who got day role UI."""
        template = str(self._raw["game_day_sent"])
        return template.format(chat_id=chat_id)

    def vote_ballots(self, chat_id: int) -> str:
        """Hash target_id -> JSON list of voters."""
        template = str(self._raw["game_vote_ballots"])
        return template.format(chat_id=chat_id)

    def vote_sent(self, chat_id: int) -> str:
        """Set of users who received vote UI."""
        template = str(self._raw["game_vote_sent"])
        return template.format(chat_id=chat_id)

    def game_flags(self, chat_id: int) -> str:
        """Hash of phase flags for a game."""
        template = str(self._raw["game_flags"])
        return template.format(chat_id=chat_id)

    def ai_players(self, chat_id: int) -> str:
        """Set of AI user ids in a game."""
        template = str(self._raw["game_ai_players"])
        return template.format(chat_id=chat_id)

    def ai_personas(self, chat_id: int) -> str:
        """Hash user_id -> persona_id."""
        template = str(self._raw["game_ai_personas"])
        return template.format(chat_id=chat_id)

    def ai_chat_queue(self, chat_id: int) -> str:
        """List of pending AI chat JSON lines."""
        template = str(self._raw["game_ai_chat_queue"])
        return template.format(chat_id=chat_id)

    def ai_chat_count(self, chat_id: int) -> str:
        """Hash user_id -> messages sent this day."""
        template = str(self._raw["game_ai_chat_count"])
        return template.format(chat_id=chat_id)

    def night_count(self, chat_id: int) -> str:
        """Night counter key."""
        template = str(self._raw["game_night_count"])
        return template.format(chat_id=chat_id)

    def day_count(self, chat_id: int) -> str:
        """Day counter key."""
        template = str(self._raw["game_day_count"])
        return template.format(chat_id=chat_id)

    def timer_end(self, chat_id: int) -> str:
        """Absolute Unix end for current phase."""
        template = str(self._raw["game_timer_end"])
        return template.format(chat_id=chat_id)

    def next_game_list(self, chat_id: int) -> str:
        """Set of users waiting for next lobby."""
        template = str(self._raw["game_next_list"])
        return template.format(chat_id=chat_id)

    def player_role(self, user_id: int) -> str:
        """Per-player role key."""
        template = str(self._raw["player_role"])
        return template.format(user_id=user_id)

    def player_state(self, user_id: int) -> str:
        """Per-player state key."""
        template = str(self._raw["player_state"])
        return template.format(user_id=user_id)

    def night_sent(self, chat_id: int) -> str:
        """Set of users who received night DM."""
        template = str(self._raw["night_sent"])
        return template.format(chat_id=chat_id)

    def role_intro_sent(self, chat_id: int) -> str:
        """Set of users who got role intro this game."""
        template = str(self._raw["role_intro_sent"])
        return template.format(chat_id=chat_id)

    def player_last_role(self, user_id: int) -> str:
        """Last game's role per user (anti-repeat)."""
        template = str(self._raw["player_last_role"])
        return template.format(user_id=user_id)

    def ai_runtime_enabled(self) -> str:
        """Global runtime AI on/off switch key."""
        return str(self._raw["ai_runtime_enabled"])

    def field(self, name: str) -> str:
        """Return configured hash field name.

        Unknown names pass through (dodge_day:{uid}).
        """
        return self._fields.get(name, name)
