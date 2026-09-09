"""Profile, ranks, shop, wallet, challenge, meta play APIs."""

# Split of meta.py (no logic change).
from __future__ import annotations

from webapp.api._m_core import *  # noqa: F401,F403

@router.get("/shop")
async def shop_catalog() -> dict:
    data = load_shop()
    cfg = load_sudo_cfg()
    settings = get_settings()
    live = bool(cfg.get("charge_live"))
    return {
        "items": data["items"],
        "charge_packages": data.get("charge_packages")
        or [],
        "charge_enabled": True,
        "charge_live": live,
        "sandbox_pay_allowed": (
            settings.debug_mode or live
        ),
        "notes": data.get("notes") or {},
        "currency_label": _wmsg("webapp_currency"),
    }


@router.get("/shop/charges")
async def my_charge_orders(
    tg: dict = Depends(current_user),
) -> dict:
    me_u = await ensure_user(tg)
    async with session_scope() as session:
        rows = (
            await session.execute(
                select(ChargeOrderRow)
                .where(
                    ChargeOrderRow.user_id == me_u.user_id
                )
                .order_by(ChargeOrderRow.id.desc())
                .limit(40)
            )
        ).scalars().all()
        return {"items": [_charge_dict(r) for r in rows]}


@router.post("/shop/charge/{package_id}")
async def create_charge_order(
    package_id: str,
    tg: dict = Depends(current_user),
) -> dict:
    me_u = await ensure_user(tg)
    packages = {
        str(x["id"]): x
        for x in (load_shop().get("charge_packages") or [])
    }
    pk = packages.get(package_id)
    if pk is None:
        raise HTTPException(404, "package.not.found")
    cfg = load_sudo_cfg()
    live = bool(cfg.get("charge_live"))
    note = (
        "awaiting_gateway"
        if live
        else "pending_offline"
    )
    async with session_scope() as session:
        order = ChargeOrderRow(
            user_id=me_u.user_id,
            package_id=package_id,
            coins=int(pk["coins"]),
            price_toman=int(pk["price_toman"]),
            status="pending",
            note=note,
        )
        session.add(order)
        await session.flush()
        return {
            "ok": True,
            "order": _charge_dict(order),
            "charge_live": live,
            "needs_gateway": live,
        }


@router.post("/shop/charge/{order_id}/sandbox-pay")
async def sandbox_pay_charge(
    order_id: int,
    tg: dict = Depends(current_user),
) -> dict:
    """Fulfill pending charge in debug or when live (until real gateway)."""
    settings = get_settings()
    cfg = load_sudo_cfg()
    if not (
        settings.debug_mode
        or bool(cfg.get("charge_live"))
    ):
        raise HTTPException(
            403,
            _wmsg("webapp_sandbox_guard"),
        )
    me_u = await ensure_user(tg)
    return await _credit_pending_order(
        order_id,
        me_u.user_id,
        status="paid",
        note="sandbox_pay",
    )


class ChargeVerifyIn(BaseModel):
    order_id: int
    gateway_ref: str = Field(min_length=1, max_length=128)
    status: str = Field(
        default="paid",
        pattern="^(paid|failed)$",
    )
    secret: str = Field(default="", max_length=128)


@router.post("/shop/charge/verify")
async def verify_charge_callback(
    body: ChargeVerifyIn,
) -> dict:
    """
    Bank/gateway callback stub.
    When CHARGE_VERIFY_SECRET is set, require matching secret.
    Credits coins on status=paid.
    """
    settings = get_settings()
    expected = settings.charge_verify_secret or ""
    cfg = load_sudo_cfg()
    expected = str(
        expected
        or cfg.get("charge_verify_secret")
        or ""
    )
    if expected and body.secret != expected:
        raise HTTPException(403, "bad.verify.secret")
    async with session_scope() as session:
        order = await session.get(
            ChargeOrderRow,
            body.order_id,
        )
        if order is None:
            raise HTTPException(404, "order.missing")
        if order.status in ("paid", "manual"):
            return {
                "ok": True,
                "already": True,
                "status": order.status,
            }
        if body.status == "failed":
            order.status = "failed"
            order.gateway_ref = body.gateway_ref
            order.updated_at = datetime.now(timezone.utc)
            order.note = (
                "log"
            ).strip("|")
            return {"ok": True, "status": "failed"}
        uid = int(order.user_id)
    return await _credit_pending_order(
        body.order_id,
        uid,
        status="paid",
        note=f"gateway:{body.gateway_ref}",
    )


@router.post("/shop/buy/{item_id}")
async def buy_item(
    item_id: str,
    tg: dict = Depends(current_user),
) -> dict:
    me_u = await ensure_user(tg)
    catalog = {
        str(x["id"]): x for x in load_shop()["items"]
    }
    item = catalog.get(item_id)
    if item is None:
        raise HTTPException(404, "item.not.found")
    price = int(item["price"])
    async with session_scope() as session:
        row = await session.get(UserRow, me_u.user_id)
        if row is None or int(row.coins) < price:
            raise HTTPException(400, "insufficient.coins")
        row.coins = int(row.coins) - price
        if item.get("kind") == "xp":
            row.xp = int(row.xp) + int(
                item.get("xp_grant") or 0
            )
        coins_grant = int(item.get("coins_grant") or 0)
        if coins_grant:
            row.coins = int(row.coins) + coins_grant
        owned = (
            await session.execute(
                select(ShopOwnedRow).where(
                    ShopOwnedRow.user_id == me_u.user_id,
                    ShopOwnedRow.item_id == item_id,
                )
            )
        ).scalar_one_or_none()
        if owned:
            owned.qty = int(owned.qty) + 1
        else:
            session.add(
                ShopOwnedRow(
                    user_id=me_u.user_id,
                    item_id=item_id,
                    qty=1,
                )
            )
        session.add(
            CoinLedgerRow(
                user_id=me_u.user_id,
                delta=-price,
                reason=f"shop:{item_id}",
            )
        )
        # unlock shop_buyer achievement (idempotent)
        exists = (
            await session.execute(
                select(AchievementUnlockRow).where(
                    AchievementUnlockRow.user_id
                    == me_u.user_id,
                    AchievementUnlockRow.achievement_id
                    == "shop_buyer",
                )
            )
        ).scalar_one_or_none()
        if exists is None:
            session.add(
                AchievementUnlockRow(
                    user_id=me_u.user_id,
                    achievement_id="shop_buyer",
                )
            )
        return {"ok": True, "coins": int(row.coins)}


@router.post("/wallet/transfer")
async def transfer(
    body: TransferIn,
    tg: dict = Depends(current_user),
) -> dict:
    me_u = await ensure_user(tg)
    if body.to_user_id == me_u.user_id:
        raise HTTPException(400, "self.transfer")
    async with session_scope() as session:
        src = await session.get(UserRow, me_u.user_id)
        dst = await session.get(UserRow, body.to_user_id)
        if src is None or dst is None:
            raise HTTPException(404, "user.missing")
        if int(src.coins) < body.amount:
            raise HTTPException(400, "insufficient")
        src.coins = int(src.coins) - body.amount
        dst.coins = int(dst.coins) + body.amount
        session.add(
            CoinLedgerRow(
                user_id=me_u.user_id,
                delta=-body.amount,
                reason="transfer_out",
                ref_user_id=body.to_user_id,
            )
        )
        session.add(
            CoinLedgerRow(
                user_id=body.to_user_id,
                delta=body.amount,
                reason="transfer_in",
                ref_user_id=me_u.user_id,
            )
        )
        return {"ok": True, "coins": int(src.coins)}


