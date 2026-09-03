"""Generate in-character AI chat and queue it."""

from __future__ import annotations

import json
from random import SystemRandom
from typing import Any

from AI.chat_clean import clean_chat_line
from AI.context import GameContext
from AI.llm_client import LlmClient
from AI.personas import PersonaBook
from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import AI_AGENTS
from app.managers.game_event import log_game_event
from app.managers.json_loader import load_json


class AiTalker:
    """LLM day-talk producer for AI personas."""

    def __init__(
        self,
        keys: RedisKeySpace | None = None,
        llm: LlmClient | None = None,
    ) -> None:
        self._keys = keys or RedisKeySpace()
        self._llm = llm or LlmClient()
        self._book = PersonaBook(self._keys)
        self._ctx = GameContext(self._keys)
        self._cfg = load_json(AI_AGENTS)
        self._rng = SystemRandom()

    async def produce_day_talk(
        self,
        chat_id: int,
    ) -> int:
        """Queue up to limit lines for each AI seat."""
        if not bool(self._cfg.get("chat_enabled")):
            return 0
        if not self._llm.enabled:
            return 0
        redis = await get_redis()
        produced = 0
        limit = int(self._cfg["messages_per_day_each"])
        for uid in await self._ctx.ai_ids(chat_id):
            try:
                n = await self._one_line(
                    redis,
                    chat_id,
                    uid,
                    limit,
                )
            except Exception:
                log_game_event(
                    "ai_talk_error",
                    chat_id=chat_id,
                    user_id=uid,
                )
                continue
            produced += n
        return produced

    async def _one_line(
        self,
        redis: Any,
        chat_id: int,
        uid: int,
        limit: int,
    ) -> int:
        """Produce and queue one seat line."""
        sent = int(
            await redis.hget(
                self._keys.ai_chat_count(chat_id),
                str(uid),
            )
            or "0"
        )
        if sent >= limit:
            return 0
        snap = await self._ctx.snapshot(chat_id, uid)
        if snap is None:
            return 0
        persona = await self._book.for_user(chat_id, uid)
        if persona is None:
            return 0
        name = str(persona.get("nickname") or "")
        if not name:
            name = self._self_name(snap, uid) or "?"
        line = self._generate(persona, snap, name)
        if not line:
            return 0
        payload = {
            "user_id": uid,
            "name": name,
            "text": line,
        }
        await redis.rpush(
            self._keys.ai_chat_queue(chat_id),
            json.dumps(payload, ensure_ascii=False),
        )
        await redis.hset(
            self._keys.ai_chat_count(chat_id),
            str(uid),
            str(sent + 1),
        )
        log_game_event(
            "ai_talk_queued",
            chat_id=chat_id,
            user_id=uid,
        )
        return 1

    def _self_name(
        self,
        snap: dict[str, Any],
        uid: int,
    ) -> str:
        """Display name of this AI from snapshot."""
        for item in snap.get("players", []):
            if int(item.get("user_id", 0)) == uid:
                return str(item.get("name") or "")
        return ""

    def _alive_names(
        self,
        snap: dict[str, Any],
        me: str,
    ) -> list[str]:
        """Alive nicknames excluding self."""
        out: list[str] = []
        for item in snap.get("players", []):
            if not item.get("alive", True):
                continue
            name = str(item.get("name") or "")
            if name and name != me:
                out.append(name)
        return out

    def _generate(
        self,
        persona: dict[str, Any],
        snap: dict[str, Any],
        my_name: str,
    ) -> str:
        """Ask LLM for one clean Persian line."""
        names = self._alive_names(snap, my_name)
        labels = self._cfg.get("team_labels") or {}
        team = str(
            (snap.get("role") or {}).get("team") or ""
        )
        team_fa = str(labels.get(team) or "نامشخص")
        extra = str(self._cfg.get("chat_system_extra", ""))
        system = f"{persona['system']}\n{extra}".strip()
        target = (
            self._rng.choice(names) if names else my_name
        )
        tmpl = str(self._cfg["chat_user_template"])
        rules = str(self._cfg["chat_user_rules"])
        user = tmpl.format(
            my_name=my_name,
            alive=", ".join(names),
            team=team_fa,
            target=target,
            rules=rules,
        )
        retries = int(self._cfg.get("chat_retries", 2))
        for _ in range(max(1, retries)):
            try:
                text = self._llm.complete(
                    system,
                    user,
                    max_tokens=int(
                        self._cfg["chat_max_tokens"]
                    ),
                    temperature=float(
                        self._cfg["chat_temperature"]
                    ),
                    top_p=float(self._cfg["chat_top_p"]),
                )
            except Exception:
                text = ""
            cleaned = clean_chat_line(text)
            if cleaned:
                return cleaned
        return self._fallback(names, target)

    def _fallback(
        self,
        names: list[str],
        target: str,
    ) -> str:
        """Config Persian line if LLM junks out."""
        lines = list(
            self._cfg.get("chat_fallback_lines") or []
        )
        if not lines:
            return ""
        who = target or (
            self._rng.choice(names) if names else "رفیق"
        )
        raw = str(self._rng.choice(lines))
        return clean_chat_line(
            raw.replace("{target}", who)
        )


async def flush_ai_chat(
    bridge,
    chat_id: int,
    keys: RedisKeySpace | None = None,
) -> int:
    """Send queued AI lines into the group chat."""
    keys = keys or RedisKeySpace()
    cfg = load_json(AI_AGENTS)
    template = str(cfg["chat_line_template"])
    redis = await get_redis()
    sent = 0
    while True:
        raw = await redis.lpop(
            keys.ai_chat_queue(chat_id)
        )
        if not raw:
            break
        item = json.loads(raw)
        body = template.format(
            name=item["name"],
            text=item["text"],
        )
        await bridge.send_text(chat_id, body)
        sent += 1
    return sent


async def reset_day_chat_counts(
    chat_id: int,
    keys: RedisKeySpace | None = None,
) -> None:
    """Clear per-day AI chat counters."""
    keys = keys or RedisKeySpace()
    redis = await get_redis()
    await redis.delete(keys.ai_chat_count(chat_id))


def fill_target() -> int:
    """Configured lobby fill size for AI."""
    cfg = load_json(AI_AGENTS)
    return int(cfg.get("fill_to", 6))
