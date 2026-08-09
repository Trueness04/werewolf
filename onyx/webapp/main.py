"""Onyx Telegram WebApp — FastAPI entry (PN-06…08, 11)."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.database.models import social as _social  # noqa: F401
from app.database.models import admin as _admin  # noqa: F401
from webapp.api.admin import router as admin_router
from webapp.api.meta import router as meta_router
from webapp.api.social import router as social_router

STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI(
    title="Onyx WebApp",
    version="0.1.0",
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
app.mount(
    "/static",
    StaticFiles(directory=str(STATIC)),
    name="static",
)


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.get("/health")
async def health() -> dict:
    return {"ok": True, "product": "onyx-webapp"}
