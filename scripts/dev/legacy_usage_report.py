"""Legacy 使用统计报告。

扫描 ``logs/legacy_usage.log`` JSONL 记录,汇总每个 ``app.legacy.*``
模块的调用方和出现次数,用于决定 Phase 1/3/4/5 是否可以安全删除对应文件。

默认行为:
- 日志路径取 ``--log`` 参数,未传时使用 ``$FHD_LEGACY_USAGE_LOG_DIR``
  或仓库根的 ``logs/legacy_usage.log``
- ``--since HOURS`` 只统计近 N 小时(默认 24)
- ``--json`` 以 JSON 输出(便于 CI 消费)

示例::

    python scripts/dev/legacy_usage_report.py --since 24
    python scripts/dev/legacy_usage_report.py --since 168 --json > legacy_usage.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterator


def _default_log_path() -> Path:
    base = os.environ.get("FHD_LEGACY_USAGE_LOG_DIR")
    if base:
        return Path(base) / "legacy_usage.log"
    return Path(__file__).resolve().parents[2] / "logs" / "legacy_usage.log"


def _iter_records(path: Path, since_ts: int) -> Iterator[dict]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = int(rec.get("ts", 0))
            if since_ts and ts < since_ts:
                continue
            yield rec


def build_report(path: Path, since_hours: int) -> dict:
    since_ts = int(time.time() - since_hours * 3600) if since_hours > 0 else 0
    module_counter: Counter = Counter()
    module_callers: dict[str, Counter] = defaultdict(Counter)
    symbols: dict[str, set[str]] = defaultdict(set)
    total = 0
    for rec in _iter_records(path, since_ts):
        mod = rec.get("module") or "unknown"
        caller = rec.get("caller") or "unknown"
        sym = rec.get("symbol")
        module_counter[mod] += 1
        module_callers[mod][caller] += 1
        if sym:
            symbols[mod].add(str(sym))
        total += 1

    report = {
        "log_path": str(path),
        "since_hours": since_hours,
        "total_events": total,
        "modules": [],
    }
    for mod, count in module_counter.most_common():
        report["modules"].append(
            {
                "module": mod,
                "count": count,
                "callers": sorted(module_callers[mod].items(), key=lambda kv: -kv[1]),
                "symbols": sorted(symbols[mod]),
            }
        )
    return report


def render_text(report: dict) -> str:
    lines = [
        f"Legacy usage report (log={report['log_path']}, "
        f"since_hours={report['since_hours']}, total_events={report['total_events']})",
        "",
    ]
    if not report["modules"]:
        lines.append("(no records in window — candidates for deletion, double-check via rg)")
        return "\n".join(lines)
    for entry in report["modules"]:
        lines.append(f"- {entry['module']}  count={entry['count']}")
        for caller, n in entry["callers"]:
            lines.append(f"    caller={caller}  n={n}")
        if entry["symbols"]:
            lines.append(f"    symbols={', '.join(entry['symbols'])}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Summarise app.legacy.* usage from logs/legacy_usage.log"
    )
    ap.add_argument("--log", type=Path, default=None, help="override log path")
    ap.add_argument(
        "--since", type=int, default=24, help="only include events within last N hours (0=all)"
    )
    ap.add_argument("--json", action="store_true", help="emit JSON instead of human-readable text")
    args = ap.parse_args(argv)

    path = args.log or _default_log_path()
    report = build_report(path, args.since)
    if args.json:
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        print(render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
