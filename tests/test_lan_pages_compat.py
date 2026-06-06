# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MOD_DIR = REPO / "mods" / "xcagi-lan-license-bridge"


def test_lan_manifest_pages_flag():
    data = json.loads((MOD_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert data.get("config", {}).get("lan_pages_via_mod") is True
    assert (MOD_DIR / "frontend" / "routes.js").is_file()
