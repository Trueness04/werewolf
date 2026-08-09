"""Sudo admin API — full bot + webapp control panel."""

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
        raise HTTPException(403, "sudo only")
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
    note: str = Field(default="sudo manual grant")


class ChargeFixIn(BaseModel):
    status: str = Field(
        pattern="^(paid|failed|reversed|manual)$"
    )
    note: str = Field(default="", max_length=200)


class SponsorIn(BaseModel):
    user_id: int
    title: str = Field(default="اسپانسر", max_length=128)
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
    note: str = Field(default="sudo reverse", max_length=200)


@router.get("/me")
async def admin_me(
    tg: dict = Depends(current_user),
) -> dict:
    """Whether current user is sudo (+ flags)."""
    await ensure_user(tg)
    uid = int(tg["id"])
    cfg = load_sudo_cfg()
    return {
        "is_sudo": is_sudo(uid),
        "user_id": uid,
        "charge_live": bool(cfg.get("charge_live")),
        "manual_grants_enabled": bool(
            cfg.get("manual_grants_enabled", True)
        ),
    }


@router.get("/overview")
async def overview(
    tg: dict = Depends(require_sudo),
) -> dict:
    """Dashboard counters."""
    _ = tg
    async with session_scope() as session:
        users = (
            await session.execute(
                select(func.count()).select_from(UserRow)
            )
        ).scalar_one()
        coins = (
            await session.execute(
                select(func.coalesce(func.sum(UserRow.coins), 0))
            )
        ).scalar_one()
        pending = (
            await session.execute(
                select(func.count())
                .select_from(ChargeOrderRow)
                .where(ChargeOrderRow.status == "pending")
            )
        ).scalar_one()
        failed = (
            await session.execute(
                select(func.count())
                .select_from(ChargeOrderRow)
                .where(ChargeOrderRow.status == "failed")
            )
        ).scalar_one()
        reports = (
            await session.execute(
                select(func.count())
                .select_from(ReportRow)
                .where(ReportRow.status == "open")
            )
        ).scalar_one()
        sponsors = (
            await session.execute(
                select(func.count())
                .select_from(SponsorRow)
                .where(SponsorRow.active.is_(True))
            )
        ).scalar_one()
        locked = (
            await session.execute(
                select(func.count())
                .select_from(GroupRow)
                .where(GroupRow.sponsor_lock.is_(True))
            )
        ).scalar_one()
    cfg = load_sudo_cfg()
    return {
        "users": int(users),
        "coins_total": int(coins),
        "charges_pending": int(pending),
        "charges_failed": int(failed),
        "reports_open": int(reports),
        "sponsors_active": int(sponsors),
        "groups_sponsor_locked": int(locked),
        "charge_live": bool(cfg.get("charge_live")),
        "manual_grants_enabled": bool(
            cfg.get("manual_grants_enabled", True)
        ),
    }


@router.get("/users")
async def search_users(
    q: str = "",
    tg: dict = Depends(require_sudo),
) -> dict:
    """Search users by id / username / name."""
    _ = tg
    q = (q or "").strip()
    async with session_scope() as session:
        stmt = select(UserRow).order_by(
            UserRow.rank.desc()
        ).limit(40)
        if q:
            clauses = [
                UserRow.fullname.ilike(f"%{q}%"),
            ]
            if q.isdigit():
                clauses.append(UserRow.user_id == int(q))
            clauses.append(
                UserRow.username.ilike(f"%{q}%")
            )
            stmt = (
                select(UserRow)
                .where(or_(*clauses))
                .limit(40)
            )
        rows = (
            await session.execute(stmt)
        ).scalars().all()
        return {
            "items": [public_profile(r) for r in rows]
        }


@router.get("/users/{user_id}")
async def user_detail(
    user_id: int,
    tg: dict = Depends(require_sudo),
) -> dict:
    """User + inventory + recent ledger."""
    _ = tg
    async with session_scope() as session:
        row = await session.get(UserRow, user_id)
        if row is None:
            raise HTTPException(404, "user not found")
        inv = (
            await session.execute(
                select(ShopOwnedRow).where(
                    ShopOwnedRow.user_id == user_id
                )
            )
        ).scalars().all()
        led = (
            await session.execute(
                select(CoinLedgerRow)
                .where(CoinLedgerRow.user_id == user_id)
                .order_by(CoinLedgerRow.id.desc())
                .limit(30)
            )
        ).scalars().all()
        sponsor = (
            await session.execute(
                select(SponsorRow).where(
                    SponsorRow.user_id == user_id
                )
            )
        ).scalar_one_or_none()
        return {
            "user": public_profile(row),
            "inventory": [
                {
                    "item_id": i.item_id,
                    "qty": i.qty,
                }
                for i in inv
            ],
            "ledger": [
                {
                    "id": x.id,
                    "delta": x.delta,
                    "reason": x.reason,
                    "ref_user_id": x.ref_user_id,
                    "created_at": (
                        x.created_at.isoformat()
                        if x.created_at
                        else None
                    ),
                }
                for x in led
            ],
            "sponsor": (
                {
                    "active": sponsor.active,
                    "title": sponsor.title,
                    "amount_toman": sponsor.amount_toman,
                }
                if sponsor
                else None
            ),
            "shop_catalog": load_shop()["items"],
        }


@router.post("/users/{user_id}/coins")
async def adjust_coins(
    user_id: int,
    body: CoinsIn,
    tg: dict = Depends(require_sudo),
) -> dict:
    """Grant or deduct coins (no gateway)."""
    cfg = load_sudo_cfg()
    if body.delta > 0 and not cfg.get(
        "manual_grants_enabled", True
    ):
        raise HTTPException(400, "manual grants off")
    actor = int(tg["id"])
    async with session_scope() as session:
        row = await session.get(UserRow, user_id)
        if row is None:
            raise HTTPException(404, "user not found")
        new_bal = int(row.coins) + int(body.delta)
        if new_bal < 0:
            raise HTTPException(400, "balance would go negative")
        row.coins = new_bal
        session.add(
            CoinLedgerRow(
                user_id=user_id,
                delta=int(body.delta),
                reason="admin_coins",
                ref_user_id=actor,
            )
        )
    await audit(
        actor,
        "adjust_coins",
        target_user_id=user_id,
        detail={"delta": body.delta, "note": body.note},
    )
    return {"ok": True, "coins": new_bal}


@router.post("/users/{user_id}/grant-item")
async def grant_item(
    user_id: int,
    body: GrantItemIn,
    tg: dict = Depends(require_sudo),
) -> dict:
    """Give magic/shop item without payment."""
    cfg = load_sudo_cfg()
    if not cfg.get("manual_grants_enabled", True):
        raise HTTPException(400, "manual grants off")
    catalog = {
        str(x["id"]): x for x in load_shop()["items"]
    }
    if body.item_id not in catalog:
        # allow known magic ids even if catalog drifts
        if not body.item_id.startswith("Majik") and not body.item_id.startswith("Maji"):
            raise HTTPException(404, "unknown item")
    actor = int(tg["id"])
    async with session_scope() as session:
        row = await session.get(UserRow, user_id)
        if row is None:
            raise HTTPException(404, "user not found")
        owned = (
            await session.execute(
                select(ShopOwnedRow).where(
                    ShopOwnedRow.user_id == user_id,
                    ShopOwnedRow.item_id == body.item_id,
                )
            )
        ).scalar_one_or_none()
        if owned:
            owned.qty = int(owned.qty) + int(body.qty)
            qty = int(owned.qty)
        else:
            session.add(
                ShopOwnedRow(
                    user_id=user_id,
                    item_id=body.item_id,
                    qty=int(body.qty),
                )
            )
            qty = int(body.qty)
        session.add(
            CoinLedgerRow(
                user_id=user_id,
                delta=0,
                reason=f"admin_grant:{body.item_id}",
                ref_user_id=actor,
            )
        )
    await audit(
        actor,
        "grant_item",
        target_user_id=user_id,
        detail={
            "item_id": body.item_id,
            "qty": body.qty,
            "note": body.note,
        },
    )
    return {"ok": True, "item_id": body.item_id, "qty": qty}


@router.get("/ledger")
async def list_ledger(
    user_id: int | None = None,
    limit: int = 50,
    tg: dict = Depends(require_sudo),
) -> dict:
    """Recent coin ledger (optional user filter)."""
    _ = tg
    limit = min(max(limit, 1), 200)
    async with session_scope() as session:
        stmt = select(CoinLedgerRow).order_by(
            CoinLedgerRow.id.desc()
        ).limit(limit)
        if user_id is not None:
            stmt = (
                select(CoinLedgerRow)
                .where(CoinLedgerRow.user_id == user_id)
                .order_by(CoinLedgerRow.id.desc())
                .limit(limit)
            )
        rows = (
            await session.execute(stmt)
        ).scalars().all()
        return {
            "items": [
                {
                    "id": x.id,
                    "user_id": x.user_id,
                    "delta": x.delta,
                    "reason": x.reason,
                    "ref_user_id": x.ref_user_id,
                    "created_at": (
                        x.created_at.isoformat()
                        if x.created_at
                        else None
                    ),
                }
                for x in rows
            ]
        }


@router.post("/ledger/{entry_id}/reverse")
async def reverse_ledger(
    entry_id: int,
    body: LedgerFixIn,
    tg: dict = Depends(require_sudo),
) -> dict:
    """Reverse a ledger row (fix broken tx)."""
    actor = int(tg["id"])
    async with session_scope() as session:
        entry = await session.get(CoinLedgerRow, entry_id)
        if entry is None:
            raise HTTPException(404, "ledger missing")
        if entry.reason.startswith("admin_reverse:"):
            raise HTTPException(400, "already a reverse")
        delta = -int(entry.delta)
        row = await session.get(UserRow, entry.user_id)
        if row is None:
            raise HTTPException(404, "user missing")
        new_bal = int(row.coins) + delta
        if new_bal < 0:
            raise HTTPException(
                400,
                "reverse would go negative",
            )
        row.coins = new_bal
        session.add(
            CoinLedgerRow(
                user_id=entry.user_id,
                delta=delta,
                reason=f"admin_reverse:{entry.id}",
                ref_user_id=actor,
            )
        )
    await audit(
        actor,
        "reverse_ledger",
        target_user_id=entry.user_id,
        detail={
            "entry_id": entry_id,
            "delta": delta,
            "note": body.note,
        },
    )
    return {"ok": True, "coins": new_bal}


@router.get("/charges")
async def list_charges(
    status: str | None = None,
    tg: dict = Depends(require_sudo),
) -> dict:
    """Charge orders for gateway / manual repair."""
    _ = tg
    async with session_scope() as session:
        stmt = select(ChargeOrderRow).order_by(
            ChargeOrderRow.id.desc()
        ).limit(80)
        if status:
            stmt = (
                select(ChargeOrderRow)
                .where(ChargeOrderRow.status == status)
                .order_by(ChargeOrderRow.id.desc())
                .limit(80)
            )
        rows = (
            await session.execute(stmt)
        ).scalars().all()
        return {
            "items": [_charge_dict(r) for r in rows],
            "charge_live": bool(
                load_sudo_cfg().get("charge_live")
            ),
        }


@router.post("/charges/manual")
async def manual_charge(
    body: ManualChargeIn,
    tg: dict = Depends(require_sudo),
) -> dict:
    """Sudo grants coins as if paid (pre-gateway)."""
    cfg = load_sudo_cfg()
    if not cfg.get("manual_grants_enabled", True):
        raise HTTPException(400, "manual grants off")
    actor = int(tg["id"])
    async with session_scope() as session:
        row = await session.get(UserRow, body.user_id)
        if row is None:
            raise HTTPException(404, "user not found")
        order = ChargeOrderRow(
            user_id=body.user_id,
            package_id=body.package_id,
            coins=body.coins,
            price_toman=body.price_toman,
            status="manual",
            note=body.note,
            actor_id=actor,
            updated_at=datetime.now(timezone.utc),
        )
        session.add(order)
        row.coins = int(row.coins) + int(body.coins)
        session.add(
            CoinLedgerRow(
                user_id=body.user_id,
                delta=int(body.coins),
                reason="charge_manual",
                ref_user_id=actor,
            )
        )
        await session.flush()
        oid = int(order.id)
        bal = int(row.coins)
    await audit(
        actor,
        "charge_manual",
        target_user_id=body.user_id,
        detail={
            "order_id": oid,
            "coins": body.coins,
            "note": body.note,
        },
    )
    return {"ok": True, "order_id": oid, "coins": bal}


@router.post("/charges/{order_id}/fix")
async def fix_charge(
    order_id: int,
    body: ChargeFixIn,
    tg: dict = Depends(require_sudo),
) -> dict:
    """Fulfill / fail / reverse a charge order."""
    actor = int(tg["id"])
    order_user = 0
    async with session_scope() as session:
        order = await session.get(ChargeOrderRow, order_id)
        if order is None:
            raise HTTPException(404, "order missing")
        prev = order.status
        order_user = int(order.user_id)
        order.status = body.status
        order.note = (
            (order.note or "")
            + f" | fix:{body.note}"
        ).strip(" |")
        order.actor_id = actor
        order.updated_at = datetime.now(timezone.utc)
        row = await session.get(UserRow, order.user_id)
        if row is None:
            raise HTTPException(404, "user missing")
        credited = False
        if body.status in ("paid", "manual") and prev not in (
            "paid",
            "manual",
        ):
            row.coins = int(row.coins) + int(order.coins)
            session.add(
                CoinLedgerRow(
                    user_id=order.user_id,
                    delta=int(order.coins),
                    reason=f"charge_{body.status}",
                    ref_user_id=actor,
                )
            )
            credited = True
        elif body.status == "reversed" and prev in (
            "paid",
            "manual",
        ):
            bal = int(row.coins) - int(order.coins)
            if bal < 0:
                raise HTTPException(
                    400,
                    "cannot reverse — insufficient coins",
                )
            row.coins = bal
            session.add(
                CoinLedgerRow(
                    user_id=order.user_id,
                    delta=-int(order.coins),
                    reason="charge_reversed",
                    ref_user_id=actor,
                )
            )
            credited = True
        bal = int(row.coins)
    await audit(
        actor,
        "charge_fix",
        target_user_id=order_user,
        detail={
            "order_id": order_id,
            "from": prev,
            "to": body.status,
            "credited": credited,
            "note": body.note,
        },
    )
    return {"ok": True, "coins": bal, "status": body.status}


@router.get("/sponsors")
async def list_sponsors(
    tg: dict = Depends(require_sudo),
) -> dict:
    _ = tg
    async with session_scope() as session:
        rows = (
            await session.execute(
                select(SponsorRow).order_by(
                    SponsorRow.id.desc()
                )
            )
        ).scalars().all()
        return {
            "items": [
                {
                    "id": r.id,
                    "user_id": r.user_id,
                    "title": r.title,
                    "amount_toman": r.amount_toman,
                    "active": r.active,
                    "note": r.note,
                }
                for r in rows
            ]
        }


@router.post("/sponsors")
async def upsert_sponsor(
    body: SponsorIn,
    tg: dict = Depends(require_sudo),
) -> dict:
    actor = int(tg["id"])
    async with session_scope() as session:
        user = await session.get(UserRow, body.user_id)
        if user is None:
            raise HTTPException(404, "user not found")
        row = (
            await session.execute(
                select(SponsorRow).where(
                    SponsorRow.user_id == body.user_id
                )
            )
        ).scalar_one_or_none()
        if row is None:
            row = SponsorRow(user_id=body.user_id)
            session.add(row)
        row.title = body.title
        row.amount_toman = body.amount_toman
        row.active = body.active
        row.note = body.note
        await session.flush()
        sid = int(row.id)
    await audit(
        actor,
        "sponsor_upsert",
        target_user_id=body.user_id,
        detail=body.model_dump(),
    )
    return {"ok": True, "id": sid}


@router.get("/groups")
async def list_groups(
    tg: dict = Depends(require_sudo),
) -> dict:
    _ = tg
    async with session_scope() as session:
        rows = (
            await session.execute(
                select(GroupRow).limit(100)
            )
        ).scalars().all()
        return {
            "items": [
                {
                    "chat_id": r.chat_id,
                    "status": r.status,
                    "lang": r.lang,
                    "sponsor_lock": bool(
                        getattr(r, "sponsor_lock", False)
                    ),
                    "max_players": r.max_players,
                }
                for r in rows
            ]
        }


@router.post("/groups/{chat_id}/sponsor-lock")
async def set_sponsor_lock(
    chat_id: int,
    body: GroupLockIn,
    tg: dict = Depends(require_sudo),
) -> dict:
    """Lock/unlock group behind sponsor gate."""
    actor = int(tg["id"])
    async with session_scope() as session:
        row = await session.get(GroupRow, chat_id)
        if row is None:
            raise HTTPException(404, "group not found")
        row.sponsor_lock = bool(body.sponsor_lock)
    await audit(
        actor,
        "sponsor_lock",
        detail={
            "chat_id": chat_id,
            "sponsor_lock": body.sponsor_lock,
        },
    )
    return {"ok": True, "sponsor_lock": body.sponsor_lock}


@router.get("/reports")
async def list_reports(
    tg: dict = Depends(require_sudo),
) -> dict:
    _ = tg
    async with session_scope() as session:
        rows = (
            await session.execute(
                select(ReportRow)
                .order_by(ReportRow.id.desc())
                .limit(60)
            )
        ).scalars().all()
        return {
            "items": [
                {
                    "id": r.id,
                    "reporter_id": r.reporter_id,
                    "target_type": r.target_type,
                    "target_id": r.target_id,
                    "reason": r.reason,
                    "status": getattr(r, "status", "open"),
                }
                for r in rows
            ]
        }


@router.post("/reports/{report_id}/resolve")
async def resolve_report(
    report_id: int,
    tg: dict = Depends(require_sudo),
) -> dict:
    actor = int(tg["id"])
    async with session_scope() as session:
        row = await session.get(ReportRow, report_id)
        if row is None:
            raise HTTPException(404)
        row.status = "resolved"
    await audit(
        actor,
        "report_resolve",
        detail={"report_id": report_id},
    )
    return {"ok": True}


@router.get("/bans")
async def list_bans(
    tg: dict = Depends(require_sudo),
) -> dict:
    _ = tg
    async with session_scope() as session:
        rows = (
            await session.execute(
                select(BanRow).order_by(BanRow.id.desc()).limit(50)
            )
        ).scalars().all()
        return {
            "items": [
                {
                    "id": r.id,
                    "user_id": r.user_id,
                    "forever": r.forever,
                    "expire_at": (
                        r.expire_at.isoformat()
                        if r.expire_at
                        else None
                    ),
                }
                for r in rows
            ]
        }


@router.post("/bans")
async def add_ban(
    body: BanIn,
    tg: dict = Depends(require_sudo),
) -> dict:
    actor = int(tg["id"])
    async with session_scope() as session:
        session.add(
            BanRow(
                user_id=body.user_id,
                forever=body.forever,
                expire_at=None,
            )
        )
    await audit(
        actor,
        "ban_add",
        target_user_id=body.user_id,
        detail={"forever": body.forever, "note": body.note},
    )
    return {"ok": True}


@router.delete("/bans/{ban_id}")
async def remove_ban(
    ban_id: int,
    tg: dict = Depends(require_sudo),
) -> dict:
    actor = int(tg["id"])
    async with session_scope() as session:
        row = await session.get(BanRow, ban_id)
        if row is None:
            raise HTTPException(404)
        uid = int(row.user_id)
        session.delete(row)
    await audit(
        actor,
        "ban_remove",
        target_user_id=uid,
        detail={"ban_id": ban_id},
    )
    return {"ok": True}


@router.get("/challenges")
async def admin_challenges(
    tg: dict = Depends(require_sudo),
) -> dict:
    _ = tg
    async with session_scope() as session:
        rows = (
            await session.execute(
                select(ChallengeRow)
                .order_by(ChallengeRow.id.desc())
                .limit(40)
            )
        ).scalars().all()
        return {
            "items": [
                {
                    "id": r.id,
                    "title": r.title,
                    "creator_id": r.creator_id,
                    "status": r.status,
                    "stake": r.stake,
                }
                for r in rows
            ]
        }


@router.post("/challenges/{cid}/close")
async def close_challenge(
    cid: int,
    tg: dict = Depends(require_sudo),
) -> dict:
    actor = int(tg["id"])
    async with session_scope() as session:
        row = await session.get(ChallengeRow, cid)
        if row is None:
            raise HTTPException(404)
        row.status = "closed"
    await audit(
        actor,
        "challenge_close",
        detail={"challenge_id": cid},
    )
    return {"ok": True}


@router.get("/settings")
async def get_settings_admin(
    tg: dict = Depends(require_sudo),
) -> dict:
    _ = tg
    return load_sudo_cfg()


@router.patch("/settings")
async def patch_settings(
    body: SettingsIn,
    tg: dict = Depends(require_sudo),
) -> dict:
    actor = int(tg["id"])
    cfg = load_sudo_cfg()
    data = body.model_dump(exclude_none=True)
    cfg.update(data)
    save_sudo_cfg(cfg)
    await audit(
        actor,
        "settings_patch",
        detail=data,
    )
    return cfg


@router.get("/shop-catalog")
async def shop_catalog_admin(
    tg: dict = Depends(require_sudo),
) -> dict:
    _ = tg
    data = load_shop()
    return {
        "items": data["items"],
        "charge_packages": data.get("charge_packages")
        or [],
    }


def _charge_dict(r: ChargeOrderRow) -> dict:
    return {
        "id": r.id,
        "user_id": r.user_id,
        "package_id": r.package_id,
        "coins": r.coins,
        "price_toman": r.price_toman,
        "status": r.status,
        "gateway_ref": r.gateway_ref,
        "note": r.note,
        "actor_id": r.actor_id,
        "created_at": (
            r.created_at.isoformat()
            if r.created_at
            else None
        ),
    }
