"""PN-12: Dozd resolve is a no-op."""

import pytest

from app.managers.wolf_specials import resolve_thief


@pytest.mark.asyncio
async def test_resolve_thief_noop() -> None:
    ctx = {
        "players": [
            {
                "user_id": 1,
                "role": "role_dozd",
                "alive": True,
            },
            {
                "user_id": 2,
                "role": "role_pishgo",
                "alive": True,
            },
        ],
        "roles": {"1": "role_dozd", "2": "role_pishgo"},
        "actions": {"1": "2"},
        "messages": [],
        "chat_id": 99,
    }
    await resolve_thief(ctx)
    assert ctx["roles"]["1"] == "role_dozd"
    assert ctx["roles"]["2"] == "role_pishgo"
    assert ctx["messages"] == []
