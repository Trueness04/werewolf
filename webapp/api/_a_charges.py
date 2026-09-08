"""Sudo admin API — full bot + webapp control panel."""

# Split of admin.py (no logic change).
from __future__ import annotations

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
            raise HTTPException(404, "ledger.missing")
        if entry.reason.startswith("admin_reverse:"):
            raise HTTPException(400, "already.a.reverse")
        delta = -int(entry.delta)
        row = await session.get(UserRow, entry.user_id)
        if row is None:
            raise HTTPException(404, "user.missing")
        new_bal = int(row.coins) + delta
        if new_bal < 0:
            raise HTTPException(
                            400,
                            _wmsg("http_reverse_negative"),
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
        raise HTTPException(400, "manual.grants.off")
    actor = int(tg["id"])
    async with session_scope() as session:
        row = await session.get(UserRow, body.user_id)
        if row is None:
            raise HTTPException(404, "user.not.found")
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
            raise HTTPException(404, "order.missing")
        prev = order.status
        order_user = int(order.user_id)
        order.status = body.status
        order.note = (
            (order.note or "")
            + f"|.fix:{body.note}"
        ).strip("|")
        order.actor_id = actor
        order.updated_at = datetime.now(timezone.utc)
        row = await session.get(UserRow, order.user_id)
        if row is None:
            raise HTTPException(404, "user.missing")
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
                    "cannot.reverse.insufficient.coins",
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


