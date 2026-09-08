"""Gatekeeper self-integrity: manifest + golden copy + seal.

The manifest records a SHA-256 hash of every gatekeeper source
and config file inside data/gatekeeper/integrity.json.  A golden
copy of that manifest plus an HMAC key live OUTSIDE the repo in
~/.onyx_gatekeeper/.  At every start the gatekeeper verifies:

1. manifest exists and matches its golden copy byte-for-byte;
2. the manifest HMAC signature matches the golden key;
3. every protected file hash matches the manifest.

Any local edit to a protected file, to the manifest, or to the
golden copy therefore fails startup.  Re-sealing requires an
interactive terminal and a typed seal word, so non-interactive
agents cannot silently re-baseline tampered files.
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import secrets
import sys

from app.config.paths import (
    GK_GOLDEN_KEY,
    GK_GOLDEN_MANIFEST,
    GK_INTEGRITY,
    ROOT,
)
from app.managers.console_manager import ConsoleManager
from app.managers.logger_manager import get_logger

# Typed by the human operator at re-baseline time.
SEAL_WORD = "SEAL-ONYX-GATEKEEPER"

PROTECTED: tuple[str, ...] = (
    "launcher.py",
    "app/main.py",
    "app/config/paths.py",
    "app/managers/gatekeeper.py",
    "app/managers/gk_structure.py",
    "app/managers/gk_hardcoding.py",
    "app/managers/gk_integrity.py",
    "data/gatekeeper/structure.json",
    "data/gatekeeper/patterns.json",
    "data/gatekeeper/limits.json",
    "data/text/errors.json",
    "data/console/gatekeeper.json",
)

_CI_VARS = ("CI", "GITHUB_ACTIONS", "GITLAB_CI", "TF_BUILD")


def _sha256(data: bytes) -> str:
    """Hex SHA-256 of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def _canonical(files: dict[str, str]) -> bytes:
    """Stable byte form used for the HMAC signature."""
    return json.dumps(
        {"files": files},
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _hashes_lenient() -> dict[str, str | None]:
    """Hash protected files; None when a file is missing."""
    out: dict[str, str | None] = {}
    for rel in PROTECTED:
        path = ROOT / rel
        out[rel] = (
            _sha256(path.read_bytes())
            if path.is_file()
            else None
        )
    return out


def _signature(files: dict[str, str], key: bytes) -> str:
    """HMAC-SHA256 over the canonical file map."""
    return hmac.new(
        key,
        _canonical(files),
        hashlib.sha256,
    ).hexdigest()


def _load_key() -> bytes | None:
    """Read the golden HMAC key, if present."""
    if not GK_GOLDEN_KEY.is_file():
        return None
    raw = GK_GOLDEN_KEY.read_text(encoding="utf-8").strip()
    try:
        return bytes.fromhex(raw)
    except ValueError:
        return None


def build_manifest(key: bytes) -> bytes:
    """Serialize the signed manifest for the current tree."""
    files = {
        rel: digest
        for rel, digest in _hashes_lenient().items()
        if digest is not None
    }
    doc = {
        "algorithm": "sha256+hmac-sha256",
        "files": files,
        "signature": _signature(files, key),
    }
    text = json.dumps(
        doc,
        indent=2,
        sort_keys=True,
        ensure_ascii=False,
    )
    return text.encode("utf-8") + b"\n"


def verify() -> list[tuple[str, dict[str, str]]]:
    """Return (error_key, params) pairs for every problem."""
    if not GK_INTEGRITY.is_file():
        return [("gatekeeper.integrity.no_manifest", {})]
    if not GK_GOLDEN_MANIFEST.is_file():
        return [("gatekeeper.integrity.no_golden", {})]
    local = GK_INTEGRITY.read_bytes()
    golden = GK_GOLDEN_MANIFEST.read_bytes()
    if local != golden:
        return [("gatekeeper.integrity.manifest_drift", {})]
    key = _load_key()
    if key is None:
        return [("gatekeeper.integrity.key_missing", {})]
    try:
        doc = json.loads(local.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return [("gatekeeper.integrity.bad_manifest", {})]
    files = doc.get("files", {})
    if _signature(files, key) != str(doc.get("signature")):
        return [("gatekeeper.integrity.bad_signature", {})]
    actual = _hashes_lenient()
    return [
        ("gatekeeper.integrity.file_mismatch", {"file": rel})
        for rel, digest in files.items()
        if actual.get(rel) != digest
    ]


def write_baseline(confirmation: str) -> int:
    """Seal the protected tree; return a process exit code."""
    log = get_logger()
    if confirmation.strip() != SEAL_WORD:
        log.error("gatekeeper_seal_word_rejected")
        return 1
    GK_GOLDEN_KEY.parent.mkdir(parents=True, exist_ok=True)
    if not GK_GOLDEN_KEY.is_file():
        GK_GOLDEN_KEY.write_text(
            secrets.token_hex(32),
            encoding="utf-8",
        )
    key = _load_key()
    if key is None:
        log.error("gatekeeper_seal_key_unreadable")
        return 1
    data = build_manifest(key)
    GK_INTEGRITY.write_bytes(data)
    GK_GOLDEN_MANIFEST.write_bytes(data)
    log.info("gatekeeper_seal_ok files={}", len(PROTECTED))
    return 0


def _interactive_lock() -> bool:
    """True only for a human on a real terminal."""
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return False
    return not any(
        os.environ.get(var) for var in _CI_VARS
    )


def _cli_rebaseline() -> int:
    """Guarded re-baseline entrypoint."""
    log = get_logger()
    if not _interactive_lock():
        log.error("gatekeeper_seal_needs_tty")
        console = ConsoleManager()
        log.error(console.format("rebaseline_refused"))
        return 2
    console = ConsoleManager()
    word = input(console.format("rebaseline_prompt"))
    return write_baseline(word)


def main(argv: list[str] | None = None) -> int:
    """CLI: --rebaseline seals; default verifies quietly."""
    parser = argparse.ArgumentParser(
        prog="app.managers.gk_integrity",
    )
    parser.add_argument("--rebaseline", action="store_true")
    args = parser.parse_args(argv)
    if args.rebaseline:
        return _cli_rebaseline()
    log = get_logger()
    issues = verify()
    for key, kwargs in issues:
        log.error(key, **kwargs)
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
