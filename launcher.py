"""Onyx unified entrypoint — bot + webapp + DB schema."""

from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import threading
import venv
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
_ENV_DIR = _ROOT / "data" / "env"
_VENV_DIR = _ENV_DIR / ".venv"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.managers.gatekeeper import Gatekeeper
from app.managers.logger_manager import (
    get_logger,
    setup_loguru,
)


def _ensure_venv():
    """Create .venv in data/env if missing."""
    if (_VENV_DIR / "Scripts" / "python.exe").exists():
        return str(_VENV_DIR / "Scripts" / "python.exe")
    venv.create(_VENV_DIR, with_pip=True)
    pip = str(_VENV_DIR / "Scripts" / "pip.exe")
    subprocess.check_call([
        pip, "install", "-r",
        str(_ENV_DIR / "requirements.txt"),
    ])
    return str(_VENV_DIR / "Scripts" / "python.exe")


def _kill_old_bot(token: str):
    """Kill processes running launcher.py (Windows-only)."""
    if os.name != "nt":
        return
    own_pid = os.getpid()
    out = subprocess.check_output(
        ["tasklist", "/FI", "IMAGENAME eq python.exe",
         "/FO", "CSV", "/NH"],
        text=True, encoding="utf-8",
    )
    for line in out.strip().splitlines():
        parts = line.split(",")
        if len(parts) < 2:
            continue
        pid = int(parts[1].strip('"'))
        if pid == own_pid:
            continue
        try:
            cmdline = subprocess.check_output(
                ["wmic", "process", "where",
                 f"ProcessId={pid}",
                 "get", "CommandLine", "/VALUE"],
                text=True, encoding="utf-8",
            )
        except Exception:
            continue
        if "launcher.py" in cmdline and pid != own_pid:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                capture_output=True,
            )


def _port_in_use(port):
    with socket.socket() as s:
        try:
            s.bind(("", port))
            return False
        except OSError:
            return True


def _find_port(preferred):
    """Return preferred or next free port."""
    if not _port_in_use(preferred):
        return preferred
    for p in range(preferred + 1, preferred + 10):
        if not _port_in_use(p):
            return p
    return preferred


def _ensure_db() -> None:
    """Create/migrate schema before serving traffic."""
    from app.database.bootstrap import ensure_schema
    asyncio.run(ensure_schema())


def _start_webapp(host: str, port: int) -> None:
    """Run FastAPI webapp in this thread (daemon)."""
    import uvicorn
    uvicorn.run(
        "webapp.main:app",
        host=host, port=port,
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

    log.info("kill_old_processes")
    _kill_old_bot(settings.bot_token or "")

    log.info("db_schema_ensure")
    _ensure_db()
    log.info("db_schema_ok")

    host = settings.webapp_host
    port = _find_port(settings.webapp_port)
    web = threading.Thread(
        target=_start_webapp,
        args=(host, port),
        name="onyx-webapp",
        daemon=True,
    )
    web.start()
    log.info("webapp_started host={} port={}", host, port)

    if settings.webapp_url:
        log.info("webapp_url={}", settings.webapp_url)
    else:
        log.warning("webapp_url_empty")

    run(settings)


if __name__ == "__main__":
    main()
