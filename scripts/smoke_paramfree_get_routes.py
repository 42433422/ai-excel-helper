# -*- coding: utf-8 -*-
"""
枚举应用中所有「无路径模板参数」的 GET 路由并逐个请求，汇总 404/405/5xx。

用法（在仓库根）::

    set PYTHONPATH=%CD%
    python scripts/smoke_paramfree_get_routes.py

退出码：存在问题时为 1。
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path


def _quiet_loggers() -> None:
    logging.getLogger().setLevel(logging.ERROR)
    for name in (
        "app",
        "app.fastapi_app",
        "httpx",
        "httpcore",
        "sqlalchemy.engine",
        "uvicorn",
    ):
        logging.getLogger(name).setLevel(logging.ERROR)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, default=None, help="写入结果 JSON")
    args = parser.parse_args()

    _quiet_loggers()

    from fastapi.routing import APIRoute
    from fastapi.testclient import TestClient

    from app.fastapi_app import create_fastapi_app

    skip = frozenset({"/docs", "/openapi.json", "/redoc"})
    app = create_fastapi_app()
    client = TestClient(app, raise_server_exceptions=False)
    paths = sorted(
        {
            r.path
            for r in app.routes
            if isinstance(r, APIRoute)
            and "GET" in (r.methods or set())
            and "{" not in r.path
            and r.path not in skip
        }
    )
    bad404: list[str] = []
    bad405: list[str] = []
    bad5xx: list[dict[str, str | int]] = []
    for path in paths:
        r = client.get(path)
        if r.status_code == 404:
            bad404.append(path)
        elif r.status_code == 405:
            bad405.append(path)
        elif r.status_code >= 500:
            bad5xx.append({"path": path, "status": r.status_code, "snippet": (r.text or "")[:200]})

    payload = {
        "total_paths": len(paths),
        "bad404": bad404,
        "bad405": bad405,
        "bad5xx": bad5xx,
    }
    if args.json_out:
        args.json_out.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if bad404 or bad405 or bad5xx:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
