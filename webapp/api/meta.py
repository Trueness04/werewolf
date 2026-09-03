"""Profile, ranks, shop, wallet, challenge, meta play APIs."""

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
from webapp.api.auth import current_user
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
            raise HTTPException(404, "order missing")
        if int(order.user_id) != user_id:
            raise HTTPException(403, "not your order")
        if order.status in ("paid", "manual"):
            raise HTTPException(400, "already fulfilled")
        row = await session.get(UserRow, user_id)
        if row is None:
            raise HTTPException(404, "user missing")
        order.status = status
        order.note = (
            (order.note or "") + f" | {note}"
        ).strip(" |")
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
        raise HTTPException(404, "user not found")
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
        "currency_label": "تومان",
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
        raise HTTPException(404, "package not found")
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
            "sandbox-pay requires DEBUG_MODE or charge_live",
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
        raise HTTPException(403, "bad verify secret")
    async with session_scope() as session:
        order = await session.get(
            ChargeOrderRow,
            body.order_id,
        )
        if order is None:
            raise HTTPException(404, "order missing")
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
                (order.note or "") + " | gateway_failed"
            ).strip(" |")
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
        raise HTTPException(404, "item not found")
    price = int(item["price"])
    async with session_scope() as session:
        row = await session.get(UserRow, me_u.user_id)
        if row is None or int(row.coins) < price:
            raise HTTPException(400, "insufficient coins")
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
        raise HTTPException(400, "self transfer")
    async with session_scope() as session:
        src = await session.get(UserRow, me_u.user_id)
        dst = await session.get(UserRow, body.to_user_id)
        if src is None or dst is None:
            raise HTTPException(404, "user missing")
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


@router.get("/challenges")
async def list_challenges() -> dict:
    async with session_scope() as session:
        rows = (
            await session.execute(
                select(ChallengeRow)
                .order_by(ChallengeRow.created_at.desc())
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


@router.post("/challenges")
async def create_challenge(
    body: ChallengeIn,
    tg: dict = Depends(current_user),
) -> dict:
    me_u = await ensure_user(tg)
    async with session_scope() as session:
        row = ChallengeRow(
            title=body.title.strip(),
            creator_id=me_u.user_id,
            stake=body.stake,
            status="open",
        )
        session.add(row)
        await session.flush()
        session.add(
            ChallengeMemberRow(
                challenge_id=row.id,
                user_id=me_u.user_id,
            )
        )
        return {"id": row.id}


@router.post("/challenges/{cid}/join")
async def join_challenge(
    cid: int,
    tg: dict = Depends(current_user),
) -> dict:
    me_u = await ensure_user(tg)
    async with session_scope() as session:
        chal = await session.get(ChallengeRow, cid)
        if chal is None or chal.status != "open":
            raise HTTPException(404, "challenge closed")
        exists = (
            await session.execute(
                select(ChallengeMemberRow).where(
                    ChallengeMemberRow.challenge_id == cid,
                    ChallengeMemberRow.user_id
                    == me_u.user_id,
                )
            )
        ).scalar_one_or_none()
        if exists:
            return {"ok": True, "already": True}
        session.add(
            ChallengeMemberRow(
                challenge_id=cid,
                user_id=me_u.user_id,
            )
        )
    return {"ok": True}


@router.get("/hero")
async def get_hero(
    tg: dict = Depends(current_user),
) -> dict:
    me_u = await ensure_user(tg)
    meta = load_meta()
    async with session_scope() as session:
        hero = await session.get(HeroRow, me_u.user_id)
        return {
            "hero": (
                {
                    "user_id": int(hero.user_id),
                    "name": hero.name,
                    "kind": hero.kind,
                    "created_at": (
                        hero.created_at.isoformat()
                        if hero.created_at
                        else None
                    ),
                }
                if hero
                else None
            ),
            "price": int(meta.get("hero_price") or 20),
            "kinds": meta.get("hero_kinds") or [],
            "coins": int(me_u.coins),
        }


@router.post("/hero")
async def create_hero(
    body: HeroIn,
    tg: dict = Depends(current_user),
) -> dict:
    me_u = await ensure_user(tg)
    meta = load_meta()
    price = int(meta.get("hero_price") or 20)
    kinds = {
        str(k["id"]): k
        for k in (meta.get("hero_kinds") or [])
    }
    kind = body.kind.strip() or "all"
    if kinds and kind not in kinds:
        raise HTTPException(400, "invalid kind")
    async with session_scope() as session:
        existing = await session.get(
            HeroRow, me_u.user_id
        )
        if existing is not None:
            raise HTTPException(400, "hero exists")
        row = await session.get(UserRow, me_u.user_id)
        if row is None or int(row.coins) < price:
            raise HTTPException(400, "insufficient coins")
        row.coins = int(row.coins) - price
        session.add(
            HeroRow(
                user_id=me_u.user_id,
                name=body.name.strip(),
                kind=kind,
            )
        )
        session.add(
            CoinLedgerRow(
                user_id=me_u.user_id,
                delta=-price,
                reason="hero_create",
            )
        )
        ach = (
            await session.execute(
                select(AchievementUnlockRow).where(
                    AchievementUnlockRow.user_id
                    == me_u.user_id,
                    AchievementUnlockRow.achievement_id
                    == "hero_born",
                )
            )
        ).scalar_one_or_none()
        if ach is None:
            session.add(
                AchievementUnlockRow(
                    user_id=me_u.user_id,
                    achievement_id="hero_born",
                )
            )
        return {
            "ok": True,
            "coins": int(row.coins),
            "hero": {
                "name": body.name.strip(),
                "kind": kind,
            },
        }


@router.get("/achievements")
async def list_achievements(
    tg: dict = Depends(current_user),
) -> dict:
    me_u = await ensure_user(tg)
    catalog = load_achievements().get("items") or []
    async with session_scope() as session:
        unlocked = (
            await session.execute(
                select(AchievementUnlockRow).where(
                    AchievementUnlockRow.user_id
                    == me_u.user_id
                )
            )
        ).scalars().all()
        unlocked_map = {
            r.achievement_id: (
                r.unlocked_at.isoformat()
                if r.unlocked_at
                else None
            )
            for r in unlocked
        }
        items = []
        for it in catalog:
            aid = str(it["id"])
            items.append(
                {
                    **it,
                    "unlocked": aid in unlocked_map,
                    "unlocked_at": unlocked_map.get(aid),
                }
            )
        return {
            "items": items,
            "unlocked_count": len(unlocked_map),
        }


@router.get("/online")
async def online_status(
    tg: dict = Depends(current_user),
) -> dict:
    """Online queue status for current user."""
    me_u = await ensure_user(tg)
    meta = load_meta()
    online = meta.get("online") or {}
    redis = await _online_redis()
    key = "onyx:online_queue"
    members = await redis.smembers(key)
    in_queue = str(me_u.user_id) in members
    return {
        "status": str(online.get("status") or "open"),
        "message_fa": str(
            online.get("message_fa")
            or "صف مچ‌میکینگ آماده است."
        ),
        "matchmaking": "queue",
        "queue_size": len(members),
        "in_queue": in_queue,
        "min_players": int(
            online.get("min_players") or 5
        ),
    }


@router.post("/online/queue")
async def online_join_queue(
    tg: dict = Depends(current_user),
) -> dict:
    """Join/leave online matchmaking queue."""
    me_u = await ensure_user(tg)
    redis = await _online_redis()
    key = "onyx:online_queue"
    uid = str(me_u.user_id)
    if await redis.sismember(key, uid):
        await redis.srem(key, uid)
        return {"ok": True, "in_queue": False}
    await redis.sadd(key, uid)
    await redis.expire(key, 3600)
    size = await redis.scard(key)
    return {
        "ok": True,
        "in_queue": True,
        "queue_size": size,
    }


async def _online_redis():
    from app.cache.redis_client import get_redis

    return await get_redis()


@router.get("/tournaments")
async def list_tournaments() -> dict:
    meta = load_meta()
    tcfg = meta.get("tournament") or {}
    async with session_scope() as session:
        rows = (
            await session.execute(
                select(TournamentRow)
                .order_by(TournamentRow.created_at.desc())
                .limit(40)
            )
        ).scalars().all()
        items = []
        for r in rows:
            count = (
                await session.execute(
                    select(func.count())
                    .select_from(TournamentMemberRow)
                    .where(
                        TournamentMemberRow.tournament_id
                        == r.id
                    )
                )
            ).scalar_one()
            items.append(
                {
                    "id": int(r.id),
                    "title": r.title,
                    "creator_id": int(r.creator_id),
                    "stake": int(r.stake),
                    "status": r.status,
                    "members": int(count),
                }
            )
        return {
            "items": items,
            "defaults": {
                "stake": int(
                    tcfg.get("default_stake") or 10
                ),
                "max_members": int(
                    tcfg.get("max_members") or 32
                ),
            },
        }


@router.post("/tournaments")
async def create_tournament(
    body: TournamentIn,
    tg: dict = Depends(current_user),
) -> dict:
    me_u = await ensure_user(tg)
    meta = load_meta()
    tcfg = meta.get("tournament") or {}
    stake = (
        int(body.stake)
        if body.stake is not None
        else int(tcfg.get("default_stake") or 10)
    )
    if stake < int(tcfg.get("min_stake") or 0):
        raise HTTPException(400, "stake too low")
    title = (
        (body.title or "").strip()
        or str(
            tcfg.get("title_default")
            or "تورنمنت اونیکس"
        )
    )
    max_m = int(tcfg.get("max_members") or 32)
    async with session_scope() as session:
        row_u = await session.get(UserRow, me_u.user_id)
        if row_u is None or int(row_u.coins) < stake:
            raise HTTPException(400, "insufficient coins")
        if stake > 0:
            row_u.coins = int(row_u.coins) - stake
            session.add(
                CoinLedgerRow(
                    user_id=me_u.user_id,
                    delta=-stake,
                    reason="tournament_stake",
                )
            )
        row = TournamentRow(
            title=title,
            creator_id=me_u.user_id,
            stake=stake,
            status="open",
        )
        session.add(row)
        await session.flush()
        session.add(
            TournamentMemberRow(
                tournament_id=row.id,
                user_id=me_u.user_id,
            )
        )
        return {
            "id": int(row.id),
            "coins": int(row_u.coins),
            "max_members": max_m,
        }


@router.post("/tournaments/{tid}/join")
async def join_tournament(
    tid: int,
    tg: dict = Depends(current_user),
) -> dict:
    me_u = await ensure_user(tg)
    meta = load_meta()
    max_m = int(
        (meta.get("tournament") or {}).get(
            "max_members"
        )
        or 32
    )
    async with session_scope() as session:
        tour = await session.get(TournamentRow, tid)
        if tour is None or tour.status != "open":
            raise HTTPException(404, "tournament closed")
        exists = (
            await session.execute(
                select(TournamentMemberRow).where(
                    TournamentMemberRow.tournament_id
                    == tid,
                    TournamentMemberRow.user_id
                    == me_u.user_id,
                )
            )
        ).scalar_one_or_none()
        if exists:
            return {"ok": True, "already": True}
        count = (
            await session.execute(
                select(func.count())
                .select_from(TournamentMemberRow)
                .where(
                    TournamentMemberRow.tournament_id
                    == tid
                )
            )
        ).scalar_one()
        if int(count) >= max_m:
            raise HTTPException(400, "tournament full")
        stake = int(tour.stake)
        row_u = await session.get(UserRow, me_u.user_id)
        if row_u is None or int(row_u.coins) < stake:
            raise HTTPException(400, "insufficient coins")
        if stake > 0:
            row_u.coins = int(row_u.coins) - stake
            session.add(
                CoinLedgerRow(
                    user_id=me_u.user_id,
                    delta=-stake,
                    reason="tournament_stake",
                )
            )
        session.add(
            TournamentMemberRow(
                tournament_id=tid,
                user_id=me_u.user_id,
            )
        )
        return {"ok": True, "coins": int(row_u.coins)}
