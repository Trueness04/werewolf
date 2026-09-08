"""Sudo admin API — full bot + webapp control panel."""

# Split of admin.py (no logic change).
from __future__ import annotations

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
            raise HTTPException(404, "user.not.found")
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
            raise HTTPException(404, "group.not.found")
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
