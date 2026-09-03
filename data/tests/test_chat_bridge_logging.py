"""Verify ChatBridge.send_text logs failures instead of swallowing them."""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.managers.chat_bridge import ChatBridge  # noqa: E402


class FakeBot:
    async def send_message(self, **kwargs):
        raise RuntimeError("simulated telegram failure")


async def main() -> None:
    bridge = ChatBridge(FakeBot())
    mid = await bridge.send_text(-123, "سلام تست <b>bold</b>")
    assert mid == 0, f"expected 0, got {mid}"
    print("OK: send_text returned 0 and logged the exception above")


asyncio.run(main())
