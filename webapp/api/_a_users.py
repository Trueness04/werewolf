"""Sudo admin API — full bot + webapp control panel."""

# Split of admin.py (no logic change).
from __future__ import annotations

from fastapi import APIRouter  # noqa: F401

from webapp.api._a_core import *  # noqa: F401,F403

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
            raise HTTPException(404, "user.not.found")
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
        raise HTTPException(400, "manual.grants.off")
    actor = int(tg["id"])
    async with session_scope() as session:
        row = await session.get(UserRow, user_id)
        if row is None:
            raise HTTPException(404, "user.not.found")
        new_bal = int(row.coins) + int(body.delta)
        if new_bal < 0:
            raise HTTPException(400, "balance.would.go.negative")
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
        raise HTTPException(400, "manual.grants.off")
    catalog = {
        str(x["id"]): x for x in load_shop()["items"]
    }
    if body.item_id not in catalog:
        # allow known magic ids even if catalog drifts
        is_magic = body.item_id.startswith(
            "Majik"
        ) or body.item_id.startswith("Maji")
        if not is_magic:
            raise HTTPException(404, _wmsg("http_unknown_item"))
    actor = int(tg["id"])
    async with session_scope() as session:
        row = await session.get(UserRow, user_id)
        if row is None:
            raise HTTPException(404, "user.not.found")
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


