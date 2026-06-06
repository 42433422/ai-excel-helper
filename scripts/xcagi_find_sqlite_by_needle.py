#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在指定目录下扫描 .db（SQLite），查找 purchase_units.unit_name 或整张表文本是否包含关键字。
用于定位「深圳百木鼎…」等业务库文件（若曾以 SQLite 保存）。

用法:
  python scripts/xcagi_find_sqlite_by_needle.py --dir E:/FHD/424 --needle 百木鼎
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path


def _try_match(path: Path, needle: str) -> list[str]:
    out: list[str] = []
    try:
        conn = sqlite3.connect(str(path))
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='purchase_units'")
        if not cur.fetchone():
            conn.close()
            return out
        cur.execute("PRAGMA table_info(purchase_units)")
        cols = [r[1] for r in cur.fetchall()]
        name_col = "unit_name" if "unit_name" in cols else None
        if name_col:
            cur.execute(
                f"SELECT COUNT(*) FROM purchase_units WHERE {name_col} LIKE ?",
                (f"%{needle}%",),
            )
            n = cur.fetchone()[0]
            if n:
                out.append(f"purchase_units.{name_col} match count={n}")
        cur.execute(f"SELECT COUNT(*) FROM purchase_units")
        total = cur.fetchone()[0]
        out.append(f"purchase_units total rows={total}")
        conn.close()
    except sqlite3.Error as e:
        out.append(f"sqlite error: {e}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, default=Path(__file__).resolve().parent.parent / "424")
    ap.add_argument("--needle", required=True)
    args = ap.parse_args()
    root: Path = args.dir
    needle = args.needle.strip()
    if not root.is_dir():
        print("目录不存在:", root, file=sys.stderr)
        return 1
    hits = 0
    for p in sorted(root.glob("*.db")):
        notes = _try_match(p, needle)
        if any("match count=" in x for x in notes):
            hits += 1
            print(p)
            for line in notes:
                print(" ", line)
    if hits == 0:
        print(f"未在 {root} 的 *.db 中发现 purchase_units 含 {needle!r} 的行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
