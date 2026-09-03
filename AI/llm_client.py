"""NVIDIA OpenAI-compatible chat client."""

from __future__ import annotations

from typing import Any

from app.config.paths import AI_AGENTS
from app.config.settings import Settings, get_settings
from app.managers.json_loader import load_json


class LlmClient:
    """Thin wrapper around OpenAI SDK for NVIDIA."""

    def __init__(
        self,
        settings: Settings | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._cfg = load_json(AI_AGENTS)
        self._client: Any | None = None

    @property
    def enabled(self) -> bool:
        """True when API key is configured."""
        return bool(self._settings.nvidia_api_key)

    def _base_url(self) -> str:
        """Resolve API base URL from env or config."""
        return str(
            self._settings.nvidia_base_url
            or self._cfg["nvidia_base_url"]
        )

    def _model(self) -> str:
        """Resolve model id from env or config."""
        return str(
            self._settings.nvidia_model
            or self._cfg["nvidia_model"]
        )

    def _ensure(self) -> Any:
        """Lazy-create OpenAI client."""
        if self._client is not None:
            return self._client
        if not self.enabled:
            raise RuntimeError("nvidia_api_key_missing")
        from openai import OpenAI

        self._client = OpenAI(
            base_url=self._base_url(),
            api_key=self._settings.nvidia_api_key,
        )
        return self._client

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 200,
        temperature: float = 1.0,
        top_p: float = 1.0,
    ) -> str:
        """Non-stream chat completion; return text."""
        client = self._ensure()
        result = client.chat.completions.create(
            model=self._model(),
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stream=False,
        )
        choice = result.choices[0].message
        return str(choice.content or "").strip()
