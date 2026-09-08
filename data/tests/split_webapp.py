"""Split webapp/api/admin.py + meta.py and two app files, no logic change.

admin.py (987) -> admin_parts/{core,users,charges,misc}.py + facade admin.py
meta.py (902) -> meta_parts/{core,profile,shop,challenge}.py + facade meta.py
start_game.py (368) -> move _send_start_message block into start_message.py
day_manager.py (355) -> move reset block into day_reset.py
Then verify: py_compile, imports, gatekeeper.
"""
import pathlib
import re

ROOT = pathlib.Path("/home/amin/Project/onyx")


def split_file(
    src_path: str,
    parts: list[tuple[str, int, int]],
    facade_imports: str,
) -> None:
    """Cut src_path into sibling modules by line ranges (1-based, inclusive)."""
    p = ROOT / src_path
    lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
    header_end = parts[0][1] - 1
    header = "".join(lines[:header_end])
    out_dir = p.parent
    pieces = []
    for name, start, end in parts:
        body = "".join(lines[start - 1 : end])
        piece = (
            "# Split of "
            + p.name
            + " (no logic change).\n"
            + "from __future__ import annotations\n\n"
            + header
            + "\n\n"
            + body
        )
        (out_dir / name).write_text(
            piece, encoding="utf-8"
        )
        pieces.append(name)
    facade = (
        p.read_text(encoding="utf-8").splitlines()[0]
        + "\n\nfrom __future__ import annotations\n\n"
        + facade_imports
    )
    p.write_text(facade, encoding="utf-8")
    print(
        "split",
        src_path,
        "->",
        pieces,
        "facade lines:",
        len(facade.splitlines()),
    )


split_file(
    "webapp/api/admin.py",
    [
        ("_a_core.py", 44, 117),
        ("_a_users.py", 118, 410),
        ("_a_charges.py", 411, 653),
        ("_a_misc.py", 654, 987),
    ],
    "from webapp.api._a_core import *  # noqa\n"
    "from webapp.api._a_users import *  # noqa\n"
    "from webapp.api._a_charges import *  # noqa\n"
    "from webapp.api._a_misc import *  # noqa\n",
)
print("admin done")
