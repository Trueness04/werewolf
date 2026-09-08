"""Profile, ranks, shop, wallet, challenge, meta play APIs."""

# Split of meta.py (no logic change).
from __future__ import annotations

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
            raise HTTPException(404, "challenge.closed")
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
        raise HTTPException(400, _wmsg("http_invalid_kind"))
    async with session_scope() as session:
        existing = await session.get(
            HeroRow, me_u.user_id
        )
        if existing is not None:
            raise HTTPException(400, "hero.exists")
        row = await session.get(UserRow, me_u.user_id)
        if row is None or int(row.coins) < price:
            raise HTTPException(400, "insufficient.coins")
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


