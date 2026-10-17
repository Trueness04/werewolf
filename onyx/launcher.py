"""Onyx unified entrypoint — bot + webapp + DB schema."""

from __future__ import annotations

import asyncio
import sys
import threading
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.managers.gatekeeper import Gatekeeper
from app.managers.logger_manager import (
    get_logger,
    setup_loguru,
)


def _ensure_db() -> None:
    """Create/migrate schema before serving traffic."""
    from app.database.bootstrap import ensure_schema

    asyncio.run(ensure_schema())


def _start_webapp(host: str, port: int) -> None:
    """Run FastAPI webapp in this thread (daemon)."""
    import uvicorn

    uvicorn.run(
        "webapp.main:app",
        host=host,
        port=port,
        log_level="info",
        access_log=False,
    )


def main() -> None:
    """Gatekeeper → DB → webapp thread → Telegram bot."""
    setup_loguru(debug_mode=False)
    Gatekeeper().enforce()
    from app.config.settings import get_settings
    from app.main import run

    settings = get_settings()
    setup_loguru(settings.debug_mode)
    log = get_logger()
    log.info("launcher_start")

    log.info("db_schema_ensure")
    _ensure_db()
    log.info("db_schema_ok")

    host = settings.webapp_host
    port = settings.webapp_port
    web = threading.Thread(
        target=_start_webapp,
        args=(host, port),
        name="onyx-webapp",
        daemon=True,
    )
    web.start()
    log.info(
        "webapp_started host={h} port={p}",
        h=host,
        p=port,
    )
    if settings.webapp_url:
        log.info(
            "webapp_url={u}",
            u=settings.webapp_url,
        )
    else:
        log.warning(
            "WEBAPP_URL empty — set for Telegram Mini App"
        )

    run(settings)


if __name__ == "__main__":
    main()
