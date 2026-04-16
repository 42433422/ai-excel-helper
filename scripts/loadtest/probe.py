#!/usr/bin/env python3
"""
Lightweight concurrency probe using only the standard library.
Hits GET /api/health — use for baseline QPS; see docs/PERFORMANCE_LOAD_TESTING.md.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import sys
import time
import urllib.error
import urllib.request


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


def main() -> int:
    p = argparse.ArgumentParser(description="Concurrent GET probe for /api/health")
    p.add_argument("--url", default="http://127.0.0.1:8000/api/health", help="Full health URL")
    p.add_argument("--workers", type=int, default=50, help="Concurrent workers")
    p.add_argument("--total", type=int, default=500, help="Total requests")
    p.add_argument("--timeout", type=float, default=30.0, help="Per-request timeout (seconds)")
    args = p.parse_args()

    if args.workers < 1 or args.total < 1:
        print("workers and total must be >= 1", file=sys.stderr)
        return 2

    wall0 = time.perf_counter()
    latencies: list[float] = []
    codes: dict[int, int] = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(one_get, args.url, args.timeout) for _ in range(args.total)]
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

    print(f"url={args.url}")
    print(f"total={args.total} workers={args.workers} wall_s={wall:.3f} rps={args.total / wall:.1f}")
    print(f"status_codes={dict(sorted(codes.items()))} http_200={ok}")
    print(f"latency_ms p50={pct(0.5):.2f} p95={pct(0.95):.2f} p99={pct(0.99):.2f}")
    return 0 if ok == args.total else 1


if __name__ == "__main__":
    raise SystemExit(main())
