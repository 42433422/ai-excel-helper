#!/usr/bin/env python3
"""FHD Mod 沙盒入口：5099 端口，复用仓库 app.*。"""

from __future__ import annotations

import logging
import os
import shutil
import sys
from pathlib import Path

SANDBOX_ROOT = Path(__file__).resolve().parent
FHD_ROOT = SANDBOX_ROOT.parent

if str(FHD_ROOT) not in sys.path:
    sys.path.insert(0, str(FHD_ROOT))
if str(SANDBOX_ROOT) not in sys.path:
    sys.path.insert(0, str(SANDBOX_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(SANDBOX_ROOT / ".env")
except ImportError:
    pass

os.environ.setdefault("LAN_GUARD_ENABLED", "0")
# CSRF：允许服务端 POST /api/mod-store/install（市场推送 Mod），勿在主栈 FHD 生产实例设置此项
os.environ.setdefault("XCAGI_SANDBOX_INSTANCE", "1")
os.environ.setdefault("XCAGI_NEURO_INTENT", "0")
os.environ.setdefault("XCAGI_DEBUG", "1")
os.environ.setdefault("XCAGI_DISABLE_REDIS", "1")
os.environ.setdefault("CACHE_REDIS_URL", "")
os.environ.setdefault("CELERY_BROKER_URL", "memory://")
os.environ.setdefault("CELERY_RESULT_BACKEND", "cache+memory://")

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def _bootstrap_runtime() -> None:
    from app.desktop_runtime.paths import configure_desktop_environment
    from app.desktop_runtime.migrate import _should_bootstrap_sqlite, bootstrap_sqlite_schema
    from sandbox_app.boot import ensure_sandbox_admin
    from sandbox_app.sandbox_settings import RUNTIME_ROOT, SANDBOX_RESET_ON_BOOT, default_mods_root

    runtime = str(RUNTIME_ROOT)
    configure_desktop_environment(runtime)
    os.environ["XCAGI_MODS_ROOT"] = str(default_mods_root())

    db_file = Path(runtime) / "data" / "xcagi.db"
    if SANDBOX_RESET_ON_BOOT and db_file.is_file():
        try:
            db_file.unlink()
            logging.info("SANDBOX_RESET_ON_BOOT: removed %s", db_file)
        except OSError as e:
            logging.warning("sandbox reset db failed: %s", e)

    if _should_bootstrap_sqlite(runtime):
        logging.info("sandbox: bootstrapping SQLite schema …")
        bootstrap_sqlite_schema(runtime)

    ensure_sandbox_admin()


_bootstrap_runtime()

from sandbox_app.app_factory import create_sandbox_app

app = create_sandbox_app()


def _listen_port() -> int:
    raw = (os.environ.get("SANDBOX_PORT") or os.environ.get("XCAGI_API_PORT") or "5099").strip()
    try:
        return int(raw)
    except ValueError:
        return 5099


def _listen_host() -> str:
    return (os.environ.get("SANDBOX_HOST") or os.environ.get("FASTAPI_HOST") or "0.0.0.0").strip()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "sandbox_run:app",
        host=_listen_host(),
        port=_listen_port(),
        reload=os.environ.get("SANDBOX_UVICORN_RELOAD", "").strip().lower()
        in {"1", "true", "yes", "on"},
    )
