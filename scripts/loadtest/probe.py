#!/usr/bin/env python3
"""
Lightweight concurrency probe using only the standard library.
Hits GET /api/health by default; use --suite desktop-mods for Mod 列表探针。
See docs/PERFORMANCE_LOAD_TESTING.md.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import sys
import time
import urllib.error
import urllib.request
from urllib.parse import urljoin


def one_get(url: str, timeout: float) -> tuple[int, float]:
    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            _ = resp.read()
            code = resp.status
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception:
        code = -1
    dt = time.perf_counter() - t0
    return code, dt


def run_probe(url: str, workers: int, total: int, timeout: float) -> int:
    wall0 = time.perf_counter()
    latencies: list[float] = []
    codes: dict[int, int] = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(one_get, url, timeout) for _ in range(total)]
        for f in concurrent.futures.as_completed(futs):
            code, dt = f.result()
            latencies.append(dt)
            codes[code] = codes.get(code, 0) + 1

    wall = time.perf_counter() - wall0
    latencies.sort()
    ok = codes.get(200, 0)

    def pct(p: float) -> float:
        if not latencies:
            return 0.0
        i = min(int(round((len(latencies) - 1) * p)), len(latencies) - 1)
        return latencies[i] * 1000

    print(f"url={url}")
    print(f"total={total} workers={workers} wall_s={wall:.3f} rps={total / wall:.1f}")
    print(f"status_codes={dict(sorted(codes.items()))} http_200={ok}")
    print(f"latency_ms p50={pct(0.5):.2f} p95={pct(0.95):.2f} p99={pct(0.99):.2f}")
    return 0 if ok == total else 1


def main() -> int:
    p = argparse.ArgumentParser(description="Concurrent GET probe for XCAGI API")
    p.add_argument(
        "--base", default="http://127.0.0.1:8000", help="API origin without trailing path"
    )
    p.add_argument("--url", default="", help="Full URL (overrides --base and --path)")
    p.add_argument("--path", default="/api/health", help="Path when using --base")
    p.add_argument(
        "--suite",
        choices=["health", "desktop-mods"],
        default="health",
        help="Preset path sets",
    )
    p.add_argument("--workers", type=int, default=50, help="Concurrent workers")
    p.add_argument("--total", type=int, default=500, help="Total requests per URL")
    p.add_argument("--timeout", type=float, default=30.0, help="Per-request timeout (seconds)")
    args = p.parse_args()

    if args.workers < 1 or args.total < 1:
        print("workers and total must be >= 1", file=sys.stderr)
        return 2

    base = args.base.rstrip("/")
    if args.suite == "desktop-mods":
        paths = ["/api/health", "/api/mods/", "/api/mods/loading-status", "/api/desktop/status"]
    else:
        paths = [args.path if args.path.startswith("/") else f"/{args.path}"]

    exit_code = 0
    for path in paths:
        url = args.url.strip() if args.url.strip() else urljoin(base + "/", path.lstrip("/"))
        print(f"\n--- probe {path} ---")
        code = run_probe(url, args.workers, args.total, args.timeout)
        if code != 0:
            exit_code = code
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
