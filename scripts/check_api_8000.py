"""
检查给定 URL 上是否为当前仓库的 XCAGI FastAPI 主栈（历史脚本名保留）。

默认探测 ``http://127.0.0.1:5000``（``XCAGI/run.py``）。兼容旧习惯可传 ``--url http://127.0.0.1:8000``。

用法:
  python scripts/check_api_8000.py
  python scripts/check_api_8000.py --url http://127.0.0.1:5000
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--url", default="http://127.0.0.1:5000", help="API 根地址，无尾部斜杠")
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

    code, body = get("/api/ping")
    print(f"GET /api/ping -> {code}")
    if code != 200:
        print(
            "  Expected 200 JSON with pong. Start the app: cd XCAGI && python run.py",
        )
        if body:
            print(f"  body: {body[:500]}")
        return 1
    try:
        ping = json.loads(body)
    except json.JSONDecodeError:
        print("  Response is not JSON")
        return 1
    if not ping.get("pong"):
        print(f"  Unexpected ping payload: {ping!r}")
        return 1
    print(f"  OK: service=xcagi-fastapi (ping {ping!r})")

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
