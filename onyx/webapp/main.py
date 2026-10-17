"""Onyx Telegram WebApp — FastAPI entry (PN-06…08, 11)."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database.models import social as _social  # noqa: F401
from app.database.models import admin as _admin  # noqa: F401
from webapp.api.admin import router as admin_router
from webapp.api.meta import router as meta_router
from webapp.api.social import router as social_router

DIST = Path(__file__).resolve().parent / "dist"
INDEX = DIST / "index.html"


def _need_build() -> HTTPException:
    return HTTPException(
        status_code=503,
        detail=(
            "webapp/dist missing — "
            "cd webapp/ui && npm run build"
        ),
    )


app = FastAPI(
    title="Onyx WebApp",
    version="0.2.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(social_router)
app.include_router(meta_router)
app.include_router(admin_router)

if DIST.is_dir():
    assets = DIST / "assets"
    if assets.is_dir():
        app.mount(
            "/assets",
            StaticFiles(directory=str(assets)),
            name="assets",
        )


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "product": "onyx-webapp"}


@app.get("/")
async def index() -> FileResponse:
    if not INDEX.is_file():
        raise _need_build()
    return FileResponse(INDEX)


@app.get("/{full_path:path}")
async def spa(full_path: str) -> FileResponse:
    """SPA fallback for client routes (API stays on routers)."""
    candidate = DIST / full_path
    if candidate.is_file():
        return FileResponse(candidate)
    if not INDEX.is_file():
        raise _need_build()
    return FileResponse(INDEX)
