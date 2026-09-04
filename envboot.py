import base64, os, pathlib
raw = os.environ.get("DEPLOY_ENV_FILE")
if raw:
    p = pathlib.Path("data/env/.env")
    if not p.is_file():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(base64.b64decode(raw))
