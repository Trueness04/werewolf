"""Onyx bot entrypoint."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.managers.gatekeeper import Gatekeeper
from app.managers.logger_manager import (
    get_logger,
    setup_loguru,
)


def main() -> None:
    """Run gatekeeper, load settings, start app."""
    setup_loguru(debug_mode=False)
    Gatekeeper().enforce()
    from app.config.settings import get_settings
    from app.main import run

    settings = get_settings()
    setup_loguru(settings.debug_mode)
    get_logger().info("launcher_start")
    run(settings)


if __name__ == "__main__":
    main()
