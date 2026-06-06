#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打包「宿主基础能力（预装员工）」为 .xcemp，供 MODstore / 离线分发。"""

from __future__ import annotations

import argparse
import json
import os
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PACK_ID = "xcagi-host-foundation-employee"
SRC_DIR = REPO_ROOT / "mods" / "_employees" / PACK_ID


def build_xcemp(out_dir: Path) -> Path:
    manifest = SRC_DIR / "manifest.json"
    if not manifest.is_file():
        raise SystemExit(f"缺少员工包目录：{SRC_DIR}")

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{PACK_ID}.xcemp"
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(SRC_DIR):
            for name in files:
                full = Path(root) / name
                arc = full.relative_to(SRC_DIR).as_posix()
                zf.write(full, arcname=arc)
    meta = {
        "id": PACK_ID,
        "artifact": "employee_pack",
        "store_collection": "host_foundation",
        "path": str(out_path),
    }
    (out_dir / f"{PACK_ID}.meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "dist" / "employee_packs",
        help="输出目录（默认 dist/employee_packs）",
    )
    args = parser.parse_args()
    out = build_xcemp(args.out)
    print(f"OK: {out}")


if __name__ == "__main__":
    main()
