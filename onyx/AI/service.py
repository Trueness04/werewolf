"""Separate AI service: LLM talk + AI-bot send."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from AI.sender import build_ai_bridge
from AI.talker import AiTalker, flush_ai_chat
from app.cache.redis_client import get_redis
from app.cache.redis_keys import RedisKeySpace
from app.config.paths import AI_AGENTS
from app.config.settings import get_settings
from app.managers.json_loader import load_json
from app.managers.logger_manager import (
    get_logger,
    setup_loguru,
)


async def _tick() -> None:
    """Produce talk and send via @AI bot."""
    keys = RedisKeySpace()
    redis = await get_redis()
    talker = AiTalker(keys)
    bridge = build_ai_bridge()
    day_chats = await redis.smembers(
        keys.active_day_chats()
    )
    for item in day_chats:
        chat_id = int(item)
        await talker.produce_day_talk(chat_id)
        if bridge is not None:
            await flush_ai_chat(bridge, chat_id, keys)
    # Also flush vote-phase leftovers.
    if bridge is None:
        return
    vote_chats = await redis.smembers(
        keys.active_vote_chats()
    )
    for item in vote_chats:
        await flush_ai_chat(bridge, int(item), keys)


async def run_forever() -> None:
    """AI service loop (no getUpdates polling)."""
    settings = get_settings()
    setup_loguru(settings.debug_mode)
    log = get_logger()
    cfg = load_json(AI_AGENTS)
    interval = float(cfg.get("service_tick_seconds", 3))
    log.info(
        "ai_service_start bot={b}",
        b=settings.ai_bot_username or "-",
    )
    if not settings.nvidia_api_key:
        log.error("ai_service_missing_nvidia_key")
    if not settings.ai_bot_token:
        log.error("ai_service_missing_ai_bot_token")
    else:
        from telegram import Bot

        me = await Bot(settings.ai_bot_token).get_me()
        log.info(
            "ai_bot_ok username={u}",
            u=me.username,
        )
    while True:
        try:
            if settings.enable_bot_to_bot:
                await _tick()
        except Exception as exc:
            log.exception(
                "ai_service_tick_failed err={e}",
                e=str(exc),
            )
        await asyncio.sleep(interval)


def main() -> None:
    """Entrypoint for `python -m AI.service`."""
    get_settings.cache_clear()
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
