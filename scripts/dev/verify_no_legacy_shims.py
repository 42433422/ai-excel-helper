#!/usr/bin/env python3
"""CI：禁止重新引入 legacy_/xcagi_compat_* shim 文件（v10.0.3 破坏性清理）。"""

from __future__ import annotations

import sys
from pathlib import Path

ALLOWED = frozenset(
    {
        "xcagi_compat.py",
    }
)

ROOT = Path(__file__).resolve().parents[2] / "app" / "fastapi_routes"


def main() -> int:
    bad: list[str] = []
    for path in sorted(ROOT.glob("legacy_*.py")):
        if path.name not in ALLOWED:
            bad.append(path.name)
    for path in sorted(ROOT.glob("xcagi_compat*.py")):
        if path.name not in ALLOWED:
            bad.append(path.name)
    if bad:
        print("Disallowed legacy/compat shim files present:")
        for name in bad:
            print(f"  - {name}")
        print("Use app.fastapi_routes.domains.<domain>.* instead.")
        return 1
    print(f"OK: only allowed shims in {ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
