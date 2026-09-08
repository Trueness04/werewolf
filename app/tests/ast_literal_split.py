"""One-shot AST-anchored literal splitter (only splits plain "..." string
constants > 40 chars that are NOT docstrings). No regex mangling of docstrings.
"""
import ast
import re

FILES = [
    "app/managers/session_senior_start.py",
    "app/managers/session_senior_panel.py",
    "app/handlers/senior_kill.py",
    "app/handlers/senior_actions.py",
]

DQ = chr(34)
TQ = DQ * 3


def split_body(body: str, width: int = 34):
    chunks = []
    cur = ""
    j = 0
    while j < len(body):
        take = 2 if body[j] == "\\" and j + 1 < len(body) else 1
        if len(cur) + take > width:
            chunks.append(cur)
            cur = ""
        cur += body[j : j + take]
        j += take
    if cur:
        chunks.append(cur)
    return chunks


for path in FILES:
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    docs = set()

    def collect_docs(n):
        b = getattr(n, "body", None)
        if b:
            f = b[0]
            if (
                isinstance(f, ast.Expr)
                and isinstance(getattr(f, "value", None), ast.Constant)
                and isinstance(f.value.value, str)
            ):
                docs.add(id(f.value))

    for n in ast.walk(tree):
        if isinstance(
            n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)
        ):
            collect_docs(n)

    targets = [
        (n.lineno, n.value)
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant)
        and isinstance(n.value, str)
        and len(n.value) > 40
        and id(n) not in docs
    ]
    lines = src.splitlines(keepends=True)
    for lineno, _val in sorted(targets, reverse=True):
        seg = lines[lineno - 1]
        stripped = seg.strip()
        if not stripped.startswith(DQ):
            continue
        m = re.match(r"^" + re.escape(DQ) + r"(.*)" + re.escape(DQ) + r"(,?)\s*$", stripped)
        if not m:
            continue
        body = m.group(1)
        comma = m.group(2)
        if len(body) <= 40:
            continue
        chunks = split_body(body)
        if len(chunks) < 2:
            continue
        indent = re.match(r"\s*", seg).group(0)
        rebuilt = []
        last = len(chunks) - 1
        for k, c in enumerate(chunks):
            tail = "," if (k == last and comma) else ""
            rebuilt.append(indent + DQ + c + DQ + tail + "\n")
        lines[lineno - 1 : lineno] = rebuilt
    open(path, "w", encoding="utf-8").write("".join(lines))
print("AST SPLIT DONE")
