#!/usr/bin/env python3
"""将 ``location ^~ /fhd-api/`` 内的 ``proxy_pass`` 从 5099 改为 5100（仅改这一块，不动 /sandbox/、/api/xcmax/ 等）。"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "conf",
        nargs="?",
        default="/etc/nginx/conf.d/xiu-ci.com.conf",
        help="Nginx 站点 conf 路径",
    )
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    path = Path(args.conf)
    if not path.is_file():
        print(f"not found: {path}", file=sys.stderr)
        return 2
    text = path.read_text(encoding="utf-8")
    # 注释行里的 5099 → 5100（仅匹配 fhd-api 说明行）
    text2, n1 = re.subn(
        r"(#\s*FHD\s*/\s*XCmax:.*fhd-api/.*)\b5099\b",
        r"\g<1>5100",
        text,
        count=1,
    )
    # location 块内第一处 proxy_pass …5099/（fhd-api 块）
    text3, n2 = re.subn(
        r"(location\s+\^~\s+/fhd-api/\s*\{[^}]*?proxy_pass\s+http://127\.0\.0\.1:)5099(/)",
        r"\g<1>5100\2",
        text2,
        count=1,
        flags=re.DOTALL,
    )
    if n2 != 1:
        print(f"expected 1 proxy_pass change in /fhd-api/ block, got {n2}", file=sys.stderr)
        return 3
    if text3 == text:
        print("no changes needed")
        return 0
    if args.dry_run:
        print(text3[text3.find("location ^~ /fhd-api/") : text3.find("location ^~ /fhd-api/") + 400])
        return 0
    bak = path.with_suffix(path.suffix + f".bak.fhd5100.{datetime.now():%Y%m%d_%H%M%S}")
    shutil.copy2(path, bak)
    path.write_text(text3, encoding="utf-8")
    print(f"updated {path}; backup {bak}; comment patches: {n1}, location block: {n2}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
