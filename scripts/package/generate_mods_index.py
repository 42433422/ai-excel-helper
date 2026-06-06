#!/usr/bin/env python3
"""构建时生成 mods-index.json，运行时 scan_mods 可跳过全量 listdir。"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    from app.infrastructure.mods.mod_manager import get_mod_manager

    mm = get_mod_manager()
    mm.invalidate_scan_cache()
    scanned = mm.scan_mods(use_cache=False)
    fp = mm._mods_scan_fingerprint()
    rows = []
    for meta in scanned:
        mod_path = meta.mod_path or ""
        manifest = os.path.join(mod_path, "manifest.json")
        mtime = os.path.getmtime(manifest) if os.path.isfile(manifest) else 0
        rows.append(
            {
                "id": meta.id,
                "mod_path": mod_path,
                "manifest_mtime": mtime,
            }
        )
    payload = {
        "version": 1,
        "fingerprint": fp,
        "mods_root": mm.mods_root,
        "mods": rows,
    }
    out = Path(mm.mods_root) / "mods-index.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out} ({len(rows)} mods)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
