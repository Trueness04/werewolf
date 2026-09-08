"""Profile, ranks, shop, wallet, challenge, meta play APIs."""

# Split of meta.py (no logic change).
from __future__ import annotations


from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.config.settings import get_settings
from app.database.models.admin import ChargeOrderRow
from app.database.models.social import (
    AchievementUnlockRow,
    ChallengeMemberRow,
    ChallengeRow,
    CoinLedgerRow,
    HeroRow,
    ShopOwnedRow,
    TournamentMemberRow,
    TournamentRow,
)
from app.database.models.user import UserRow
from app.database.session import session_scope
from app.managers.rank_governor import royal_family
from app.managers.sudo import load_sudo_cfg
from app.managers.text_managers import TextManager
from webapp.api.auth import current_user

_texts = TextManager()


def _wmsg(key: str, /, *args: object) -> str:
    return _texts.get(key, "fa", *args, bundle="webapp")
from webapp.api.helpers import (
    ensure_user,
    get_user,
    list_users_by_rank,
    load_achievements,
    load_icons,
    load_meta,
    load_shop,
    public_profile,
)

router = APIRouter(prefix="/api", tags=["meta"])


class TransferIn(BaseModel):
    to_user_id: int
    amount: int = Field(ge=4)


class ChallengeIn(BaseModel):
    title: str = Field(min_length=3, max_length=128)
    stake: int = Field(default=0, ge=0)


class BioIn(BaseModel):
    bio: str = Field(max_length=280)


class HeroIn(BaseModel):
    name: str = Field(min_length=2, max_length=64)
    kind: str = Field(default="all", max_length=32)


class TournamentIn(BaseModel):
    title: str | None = Field(
        default=None,
        max_length=128,
    )
    stake: int | None = Field(default=None, ge=0)


def _charge_dict(r: ChargeOrderRow) -> dict:
    return {
        "id": int(r.id),
        "user_id": int(r.user_id),
        "package_id": r.package_id,
        "coins": int(r.coins),
        "price_toman": int(r.price_toman),
        "status": r.status,
        "note": r.note,
        "created_at": (
            r.created_at.isoformat()
            if r.created_at
            else None
        ),
    }


async def _credit_pending_order(
    order_id: int,
    user_id: int,
    *,
    status: str,
    note: str,
) -> dict:
    async with session_scope() as session:
        order = await session.get(ChargeOrderRow, order_id)
        if order is None:
            raise HTTPException(404, "order.missing")
        if int(order.user_id) != user_id:
            raise HTTPException(403, "not.your.order")
        if order.status in ("paid", "manual"):
            raise HTTPException(400, "already.fulfilled")
        row = await session.get(UserRow, user_id)
        if row is None:
            raise HTTPException(404, "user.missing")
        order.status = status
        order.note = (
            (order.note or "") + f" | {note}"
        ).strip("|")
        if note.startswith("gateway:"):
            order.gateway_ref = note.split(":", 1)[-1]
        order.updated_at = datetime.now(timezone.utc)
        row.coins = int(row.coins) + int(order.coins)
        session.add(
            CoinLedgerRow(
                user_id=user_id,
                delta=int(order.coins),
                reason=f"charge_{status}",
            )
        )
        return {
            "ok": True,
            "order_id": int(order.id),
            "coins": int(row.coins),
            "status": status,
        }


@router.get("/me")
async def me(tg: dict = Depends(current_user)) -> dict:
    row = await ensure_user(tg)
    icons = load_icons()
    unlocked = [
        r
        for r in icons["ranks"]
        if int(r["rank"]) <= int(row.rank)
    ]
    return {
        **public_profile(row),
        "icons": unlocked,
        "medals": icons.get("medals") or [],
    }


@router.get("/profile/{user_id}")
async def profile(user_id: int) -> dict:
    row = await get_user(user_id)
    if row is None:
        raise HTTPException(404, "user.not.found")
    icons = load_icons()
    unlocked = [
        r
        for r in icons["ranks"]
        if int(r["rank"]) <= int(row.rank)
    ]
    return {
        **public_profile(row),
        "icons": unlocked,
        "medals": icons.get("medals") or [],
    }


@router.patch("/me/bio")
async def set_bio(
    body: BioIn,
    tg: dict = Depends(current_user),
) -> dict:
    me_u = await ensure_user(tg)
    async with session_scope() as session:
        row = await session.get(UserRow, me_u.user_id)
        if row is None:
            raise HTTPException(404)
        row.bio = body.bio
    return {"ok": True}


@router.get("/ranks")
async def ranks() -> dict:
    rows = await list_users_by_rank(50)
    royal = await royal_family(3)
    royal_ids = {int(r.user_id) for r in royal}
    items = []
    for i, row in enumerate(rows, start=1):
        item = public_profile(row)
        item["place"] = i
        item["royal"] = int(row.user_id) in royal_ids
        item["governor"] = i == 1
        items.append(item)
    return {
        "items": items,
        "governor": public_profile(royal[0])
        if royal
        else None,
    }


