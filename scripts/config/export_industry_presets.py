# -*- coding: utf-8 -*-
"""One-shot: export frontend industryPresets.ts → config/industry_presets.json"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TS = ROOT / "frontend" / "src" / "constants" / "industryPresets.ts"
OUT = ROOT / "config" / "industry_presets.json"


def _ts_object_to_json(text: str) -> dict:
    """Best-effort convert a TS object literal block to JSON."""
    s = text.strip()
    if s.endswith(","):
        s = s[:-1]
    s = re.sub(r"(\w+):", r'"\1":', s)
    s = s.replace("'", '"')
    s = re.sub(r",\s*}", "}", s)
    s = re.sub(r",\s*]", "]", s)
    return json.loads(s)


def main() -> None:
    ts = TS.read_text(encoding="utf-8")
    ids_m = re.search(r"export const INDUSTRY_PRESET_IDS = \[(.*?)\] as const", ts, re.S)
    if not ids_m:
        raise SystemExit("INDUSTRY_PRESET_IDS not found")
    ids = [x.strip().strip("'\"") for x in ids_m.group(1).split(",") if x.strip()]
    presets: dict[str, dict] = {}
    for pid in ids:
        pat = rf"  {re.escape(pid)}: \{{\n(.*?)\n  \}},"
        m = re.search(pat, ts, re.S)
        if not m:
            raise SystemExit(f"preset block not found: {pid}")
        presets[pid] = _ts_object_to_json("{" + m.group(1) + "}")
    payload = {"schema_version": 1, "preset_ids": ids, "presets": presets}
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT} ({len(presets)} presets)")


if __name__ == "__main__":
    main()
