"""Profile, ranks, shop, wallet, challenge, meta play APIs."""

# Split of meta.py (no logic change).
from __future__ import annotations

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
            or _wmsg("webapp_queue_ready")
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
        raise HTTPException(400, _wmsg("http_stake_low"))
    title = (
        (body.title or "").strip()
        or str(
            tcfg.get("title_default")
            or _wmsg("webapp_tournament_default")
        )
    )
    max_m = int(tcfg.get("max_members") or 32)
    async with session_scope() as session:
        row_u = await session.get(UserRow, me_u.user_id)
        if row_u is None or int(row_u.coins) < stake:
            raise HTTPException(400, "insufficient.coins")
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
            raise HTTPException(404, "tournament.closed")
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
            raise HTTPException(400, "tournament.full")
        stake = int(tour.stake)
        row_u = await session.get(UserRow, me_u.user_id)
        if row_u is None or int(row_u.coins) < stake:
            raise HTTPException(400, "insufficient.coins")
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
