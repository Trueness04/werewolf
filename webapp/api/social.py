"""Feed, follow, posts, likes, comments, reports."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from app.database.models.social import (
    CommentRow,
    FeedEventRow,
    FollowRow,
    LikeRow,
    PostRow,
    ReportRow,
)
from app.database.models.user import UserRow
from app.database.session import session_scope
from webapp.api.auth import current_user
from webapp.api.helpers import (
    ensure_user,
    public_profile,
)

router = APIRouter(prefix="/api", tags=["social"])


class PostIn(BaseModel):
    body: str = Field(min_length=1, max_length=280)
    media_url: str | None = None


class CommentIn(BaseModel):
    body: str = Field(min_length=1, max_length=280)


class ReportIn(BaseModel):
    target_type: str
    target_id: int
    reason: str = Field(max_length=256)


@router.get("/feed")
async def feed(
    following_only: bool = False,
    tg: dict = Depends(current_user),
) -> dict:
    me = await ensure_user(tg)
    async with session_scope() as session:
        followees: set[int] = set()
        if following_only:
            rows = (
                await session.execute(
                    select(FollowRow.followee_id).where(
                        FollowRow.follower_id == me.user_id
                    )
                )
            ).scalars().all()
            followees = {int(x) for x in rows}
            followees.add(int(me.user_id))
        posts = (
            await session.execute(
                select(PostRow)
                .order_by(PostRow.created_at.desc())
                .limit(50)
            )
        ).scalars().all()
        events = (
            await session.execute(
                select(FeedEventRow)
                .order_by(FeedEventRow.created_at.desc())
                .limit(30)
            )
        ).scalars().all()
        items: list[dict] = []
        for p in posts:
            if following_only and p.user_id not in followees:
                continue
            author = await session.get(UserRow, p.user_id)
            items.append(
                {
                    "kind": "user_post",
                    "id": p.id,
                    "user": public_profile(author)
                    if author
                    else {"user_id": p.user_id},
                    "body": p.body,
                    "media_url": p.media_url,
                    "created_at": str(p.created_at),
                }
            )
        for e in events:
            if following_only and e.user_id not in followees:
                continue
            items.append(
                {
                    "kind": e.event_type,
                    "id": e.id,
                    "user_id": e.user_id,
                    "payload": json.loads(e.payload or "{}"),
                    "created_at": str(e.created_at),
                }
            )
        items.sort(
            key=lambda x: x.get("created_at") or "",
            reverse=True,
        )
    return {"items": items[:50]}


@router.post("/posts")
async def create_post(
    body: PostIn,
    tg: dict = Depends(current_user),
) -> dict:
    me = await ensure_user(tg)
    async with session_scope() as session:
        row = PostRow(
            user_id=me.user_id,
            body=body.body.strip(),
            media_url=body.media_url,
        )
        session.add(row)
        await session.flush()
        return {"id": row.id, "ok": True}


@router.patch("/posts/{post_id}")
async def edit_post(
    post_id: int,
    body: PostIn,
    tg: dict = Depends(current_user),
) -> dict:
    me = await ensure_user(tg)
    async with session_scope() as session:
        row = await session.get(PostRow, post_id)
        if row is None or row.user_id != me.user_id:
            raise HTTPException(404, "post not found")
        row.body = body.body.strip()
        row.media_url = body.media_url
        row.updated_at = datetime.now(timezone.utc)
    return {"ok": True}


@router.delete("/posts/{post_id}")
async def delete_post(
    post_id: int,
    tg: dict = Depends(current_user),
) -> dict:
    me = await ensure_user(tg)
    async with session_scope() as session:
        row = await session.get(PostRow, post_id)
        if row is None or row.user_id != me.user_id:
            raise HTTPException(404, "post not found")
        await session.execute(
            delete(LikeRow).where(LikeRow.post_id == post_id)
        )
        await session.execute(
            delete(CommentRow).where(
                CommentRow.post_id == post_id
            )
        )
        await session.delete(row)
    return {"ok": True}


@router.post("/posts/{post_id}/like")
async def like_post(
    post_id: int,
    tg: dict = Depends(current_user),
) -> dict:
    me = await ensure_user(tg)
    async with session_scope() as session:
        exists = (
            await session.execute(
                select(LikeRow).where(
                    LikeRow.post_id == post_id,
                    LikeRow.user_id == me.user_id,
                )
            )
        ).scalar_one_or_none()
        if exists:
            await session.delete(exists)
            return {"liked": False}
        session.add(
            LikeRow(user_id=me.user_id, post_id=post_id)
        )
    return {"liked": True}


@router.post("/posts/{post_id}/comments")
async def add_comment(
    post_id: int,
    body: CommentIn,
    tg: dict = Depends(current_user),
) -> dict:
    me = await ensure_user(tg)
    async with session_scope() as session:
        if await session.get(PostRow, post_id) is None:
            raise HTTPException(404, "post not found")
        row = CommentRow(
            post_id=post_id,
            user_id=me.user_id,
            body=body.body.strip(),
        )
        session.add(row)
        await session.flush()
        return {"id": row.id}


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: int,
    tg: dict = Depends(current_user),
) -> dict:
    """Author or post owner may delete."""
    me = await ensure_user(tg)
    async with session_scope() as session:
        c = await session.get(CommentRow, comment_id)
        if c is None:
            raise HTTPException(404)
        post = await session.get(PostRow, c.post_id)
        if c.user_id != me.user_id and (
            post is None or post.user_id != me.user_id
        ):
            raise HTTPException(403)
        await session.delete(c)
    return {"ok": True}


@router.post("/follow/{user_id}")
async def follow(
    user_id: int,
    tg: dict = Depends(current_user),
) -> dict:
    me = await ensure_user(tg)
    if user_id == me.user_id:
        raise HTTPException(400, "cannot follow self")
    async with session_scope() as session:
        exists = (
            await session.execute(
                select(FollowRow).where(
                    FollowRow.follower_id == me.user_id,
                    FollowRow.followee_id == user_id,
                )
            )
        ).scalar_one_or_none()
        if exists:
            await session.delete(exists)
            return {"following": False}
        session.add(
            FollowRow(
                follower_id=me.user_id,
                followee_id=user_id,
            )
        )
    return {"following": True}


@router.post("/report")
async def report(
    body: ReportIn,
    tg: dict = Depends(current_user),
) -> dict:
    me = await ensure_user(tg)
    async with session_scope() as session:
        session.add(
            ReportRow(
                reporter_id=me.user_id,
                target_type=body.target_type,
                target_id=body.target_id,
                reason=body.reason,
            )
        )
    return {"ok": True}
