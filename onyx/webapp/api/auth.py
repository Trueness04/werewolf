"""Telegram WebApp initData validation."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from fastapi import Header, HTTPException

from app.config.settings import get_settings


def parse_init_data(raw: str) -> dict[str, str]:
    """Parse query-string initData into a dict."""
    return dict(parse_qsl(raw, keep_blank_values=True))


def validate_init_data(
    raw: str,
    *,
    max_age_sec: int = 86400,
) -> dict:
    """Validate Telegram WebApp initData; return user."""
    settings = get_settings()
    data = parse_init_data(raw)
    recv_hash = data.pop("hash", None)
    if not recv_hash:
        raise HTTPException(401, "missing hash")
    check = "\n".join(
        f"{k}={v}"
        for k, v in sorted(data.items())
    )
    secret = hmac.new(
        b"WebAppData",
        settings.bot_token.encode(),
        hashlib.sha256,
    ).digest()
    calc = hmac.new(
        secret,
        check.encode(),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(calc, recv_hash):
        raise HTTPException(401, "bad initData")
    auth_date = int(data.get("auth_date") or "0")
    if auth_date and time.time() - auth_date > max_age_sec:
        raise HTTPException(401, "initData expired")
    user_raw = data.get("user")
    if not user_raw:
        raise HTTPException(401, "missing user")
    user = json.loads(user_raw)
    return user


async def current_user(
    x_telegram_init_data: str | None = Header(
        default=None,
        alias="X-Telegram-Init-Data",
    ),
    authorization: str | None = Header(default=None),
) -> dict:
    """FastAPI dependency: Telegram user dict."""
    raw = x_telegram_init_data
    if not raw and authorization:
        if authorization.lower().startswith("tma "):
            raw = authorization[4:].strip()
    settings = get_settings()
    if not raw:
        if settings.debug_mode:
            return {
                "id": 1,
                "first_name": "Debug",
                "username": "debug",
            }
        raise HTTPException(401, "auth required")
    return validate_init_data(raw)
