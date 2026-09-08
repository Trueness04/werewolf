"""Split webapp/api/meta.py (902 lines) into 3 sibling modules + facade.

Boundaries chosen at decorator lines; no logic change. All decorators
start new sections so each part ends right before the next decorator.
"""
import pathlib
import subprocess

ROOT = pathlib.Path("/home/amin/Project/onyx")
orig = subprocess.run(
    [
        "git",
        "show",
        "HEAD:webapp/api/meta.py",
    ],
    capture_output=True,
    text=True,
    cwd=str(ROOT),
).stdout
lines = orig.splitlines(keepends=True)
docline = lines[0]

decs = [
    i
    for i, l in enumerate(lines, 1)
    if l.startswith("@router.")
]

# groups: profile(ranks/shop/wallet) / challenges+hero+achievements / online+tournaments
p_shop = next(i for i in decs if '"/shop"' in lines[i - 1])
p_chal = next(i for i in decs if '"/challenges"' in lines[i - 1])
p_online = next(i for i in decs if '"/online"' in lines[i - 1])

parts = [
    ("_m_core.py", 2, p_shop - 1),
    ("_m_profile.py", p_shop, p_chal - 1),
    ("_m_play.py", p_chal, p_online - 1),
    ("_m_online.py", p_online, len(lines)),
]
for name, start, end in parts:
    body = "".join(lines[start - 1 : end])
    piece = (
        docline.rstrip("\n")
        + "\n\n"
        + "# Split of meta.py (no logic change).\n"
        + "from __future__ import annotations\n\n"
        + body
    )
    (ROOT / "webapp/api" / name).write_text(
        piece, encoding="utf-8"
    )
    print(name, end - start + 1, "lines")

facade = (
    docline
    + "\n"
    + "from webapp.api._m_core import *  # noqa\n"
    + "from webapp.api._m_profile import *  # noqa\n"
    + "from webapp.api._m_play import *  # noqa\n"
    + "from webapp.api._m_online import *  # noqa\n"
)
(ROOT / "webapp/api/meta.py").write_text(
    facade, encoding="utf-8"
)
print("meta facade written")
