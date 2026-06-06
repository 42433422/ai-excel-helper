# -*- coding: utf-8 -*-
"""输出指定 SKU 的 package_stage_ids（JSON 数组），供 PowerShell stage 脚本调用。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.mod_sdk.host_profile import package_stage_mod_ids_for_sku  # noqa: E402


def main() -> None:
    sku = (sys.argv[1] if len(sys.argv) > 1 else "enterprise").strip().lower()
    ids = list(package_stage_mod_ids_for_sku(sku))  # type: ignore[arg-type]
    print(json.dumps(ids, ensure_ascii=False))


if __name__ == "__main__":
    main()
