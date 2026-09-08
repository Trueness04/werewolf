"""Sudo admin API — full bot + webapp control panel."""

# Split of admin.py (no logic change).
from __future__ import annotations


from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select

from app.database.models.admin import (
    ChargeOrderRow,
    SponsorRow,
)
from app.database.models.ban import BanRow
from app.database.models.group import GroupRow
from app.database.models.social import (
    ChallengeRow,
    CoinLedgerRow,
    ReportRow,
    ShopOwnedRow,
)
from app.database.models.user import UserRow
from app.database.session import session_scope
from app.managers.text_managers import TextManager

_texts = TextManager()
from app.managers.sudo import (
    audit,
    is_sudo,
    load_sudo_cfg,
    save_sudo_cfg,
)
from webapp.api.auth import current_user
from webapp.api.helpers import (
    ensure_user,
    load_shop,
    public_profile,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


async def require_sudo(
    tg: dict = Depends(current_user),
) -> dict:
    """Auth + sudo allowlist."""
    await ensure_user(tg)
    uid = int(tg["id"])
    if not is_sudo(uid):
        raise HTTPException(403, _wmsg("http_sudo_only"))
    return tg


class CoinsIn(BaseModel):
    delta: int
    note: str = Field(default="", max_length=200)


class GrantItemIn(BaseModel):
    item_id: str
    qty: int = Field(default=1, ge=1, le=99)
    note: str = Field(default="", max_length=200)


class ManualChargeIn(BaseModel):
    user_id: int
    package_id: str = "manual"
    coins: int = Field(ge=1)
    price_toman: int = Field(default=0, ge=0)
    note: str = Field(default="sudo.manual.grant")


class ChargeFixIn(BaseModel):
    status: str = Field(
        pattern="^(paid|failed|reversed|manual)$"
    )
    note: str = Field(default="", max_length=200)


class SponsorIn(BaseModel):
    user_id: int
    title: str = Field(
        default=_texts.get(
            "webapp_sponsor_default",
            "fa",
            bundle="webapp",
        ),
        max_length=128,
    )
    amount_toman: int = Field(default=0, ge=0)
    active: bool = True
    note: str = Field(default="", max_length=280)


class GroupLockIn(BaseModel):
    sponsor_lock: bool


class BanIn(BaseModel):
    user_id: int
    forever: bool = True
    note: str = Field(default="", max_length=200)


class SettingsIn(BaseModel):
    charge_live: bool | None = None
    manual_grants_enabled: bool | None = None
    sponsor_lock_default: bool | None = None


class LedgerFixIn(BaseModel):
    note: str = Field(default="sudo.reverse", max_length=200)


