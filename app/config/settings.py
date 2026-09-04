"""Application settings loaded from environment."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)

from app.config.paths import (
    DOTENV_FILE,
    URL_TEMPLATES,
)
from app.managers.error_manager import ErrorManager


class Settings(BaseSettings):
    """Runtime configuration from data/env/.env."""

    model_config = SettingsConfigDict(
        env_file=str(DOTENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(alias="BOT_TOKEN")
    db_host: str = Field(alias="DB_HOST")
    db_port: int = Field(alias="DB_PORT")
    db_name: str = Field(alias="DB_NAME")
    db_user: str = Field(alias="DB_USER")
    db_password: str = Field(alias="DB_PASSWORD")
    redis_host: str = Field(alias="REDIS_HOST")
    redis_port: int = Field(alias="REDIS_PORT")
    redis_password: str = Field(default="", alias="REDIS_PASSWORD")
    default_lang: str = Field(alias="DEFAULT_LANG")
    fallback_lang: str = Field(alias="FALLBACK_LANG")
    bot_username: str = Field(alias="BOT_USERNAME")
    join_duration_seconds: int = Field(
        alias="JOIN_DURATION_SECONDS",
    )
    tick_interval_seconds: int = Field(
        alias="TICK_INTERVAL_SECONDS",
    )
    max_players: int = Field(alias="MAX_PLAYERS")
    extend_default_seconds: int = Field(
        alias="EXTEND_DEFAULT_SECONDS",
    )
    max_extend_seconds: int = Field(
        default=300,
        alias="MAX_EXTEND_SECONDS",
    )
    join_cost_coins: int = Field(alias="JOIN_COST_COINS")
    debug_mode: bool = Field(alias="DEBUG_MODE")
    enable_bot_to_bot: bool = Field(
        alias="ENABLE_BOT_TO_BOT",
    )
    bot_to_bot_max_messages: int = Field(
        alias="BOT_TO_BOT_MAX_MESSAGES",
    )
    bot_to_bot_timeout_seconds: int = Field(
        alias="BOT_TO_BOT_TIMEOUT_SECONDS",
    )
    night_duration_seconds: int = Field(
        alias="NIGHT_DURATION_SECONDS",
    )
    role_balance_max_attempts: int = Field(
        alias="ROLE_BALANCE_MAX_ATTEMPTS",
    )
    balance_tolerance: int = Field(
        alias="BALANCE_TOLERANCE",
    )
    day_duration_seconds: int = Field(
        alias="DAY_DURATION_SECONDS",
    )
    vote_duration_seconds: int = Field(
        alias="VOTE_DURATION_SECONDS",
    )
    sheriff_shot_seconds: int = Field(
        alias="SHERIFF_SHOT_SECONDS",
    )
    secret_vote: bool = Field(alias="SECRET_VOTE")
    ai_bot_token: str = Field(
        default="",
        alias="AI_BOT_TOKEN",
    )
    ai_bot_username: str = Field(
        default="",
        alias="AI_BOT_USERNAME",
    )
    nvidia_api_key: str = Field(
        default="",
        alias="NVIDIA_API_KEY",
    )
    nvidia_base_url: str = Field(
        default="",
        alias="NVIDIA_BASE_URL",
    )
    nvidia_model: str = Field(
        default="",
        alias="NVIDIA_MODEL",
    )
    webapp_url: str = Field(
        default="",
        alias="WEBAPP_URL",
    )
    webapp_host: str = Field(
        default="0.0.0.0",
        alias="WEBAPP_HOST",
    )
    webapp_port: int = Field(
        default=8080,
        alias="WEBAPP_PORT",
    )
    sudo_ids: str = Field(
        default="",
        alias="SUDO_IDS",
    )

    charge_verify_secret: str = Field(
        default="",
        alias="CHARGE_VERIFY_SECRET",
    )

    def sudo_id_set(self) -> set[int]:
        """Parse comma-separated Telegram sudo user ids."""
        out: set[int] = set()
        for part in self.sudo_ids.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                out.add(int(part))
            except ValueError:
                continue
        return out

    def _templates(self) -> dict[str, str]:
        """Load URL templates from data/config."""
        with URL_TEMPLATES.open(encoding="utf-8") as handle:
            raw: Any = json.load(handle)
        return {
            str(key): str(value)
            for key, value in raw.items()
        }

    @property
    def database_url(self) -> str:
        """Build async SQLAlchemy PostgreSQL DSN."""
        template = self._templates()["database"]
        return template.format(
            user=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            name=self.db_name,
        )

    @property
    def redis_url(self) -> str:
        """Build Redis URL from host and port."""
        template = self._templates()["redis"]
        return template.format(
            password=self.redis_password,
            host=self.redis_host,
            port=self.redis_port,
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached Settings singleton."""
    if not DOTENV_FILE.is_file():
        errors = ErrorManager()
        msg = errors.get(
            "settings.env_missing",
            path=DOTENV_FILE.as_posix(),
        )
        raise FileNotFoundError(msg)
    return Settings()
