"""
检查 127.0.0.1:8000 上是否为当前仓库的 FHD backend.http_app（含 XCAGI 兼容路由）。

用法:
  python scripts/check_api_8000.py
  python scripts/check_api_8000.py --url http://127.0.0.1:9000
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:8000", help="API 根地址，无尾部斜杠")
    args = p.parse_args()
    base = args.url.rstrip("/")

    def get(path: str) -> tuple[int, str]:
        req = urllib.request.Request(f"{base}{path}", method="GET")
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, r.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", errors="replace")
        except OSError as e:
            return -1, str(e)

    def post_json(path: str, body: dict) -> tuple[int, str]:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            f"{base}{path}",
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, r.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", errors="replace")
        except OSError as e:
            return -1, str(e)

    code, body = get("/api/fhd/identity")
    print(f"GET /api/fhd/identity -> {code}")
    if code != 200:
        print(
            "  Expected 200 with backend=fhd-http-app. If 404, port 8000 is NOT this repo's "
            "backend.http_app (stop the other process, then from repo root: python -m backend.http_app).",
        )
        if body:
            print(f"  body: {body[:500]}")
        return 1
    try:
        ident = json.loads(body)
    except json.JSONDecodeError:
        print("  Response is not JSON")
        return 1
    if ident.get("backend") != "fhd-http-app":
        print(f"  Wrong backend: {ident!r}")
        return 1
    print(f"  OK: {ident.get('backend')}, xcagi_compat={ident.get('xcagi_compat')}")

    c2, b2 = post_json("/api/state/client-mods-off", {"client_mods_off": False})
    print(f"POST /api/state/client-mods-off -> {c2} {b2[:200]!r}")
    if c2 != 200:
        return 1

    c3, b3 = get("/api/traditional-mode/list?path=")
    print(f"GET /api/traditional-mode/list?path= -> {c3}")
    if c3 != 200:
        print(f"  body: {b3[:300]}")
        return 1

    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
