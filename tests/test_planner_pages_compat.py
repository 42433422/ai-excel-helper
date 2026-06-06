# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MOD_DIR = REPO / "mods" / "xcagi-planner-bridge"


def test_planner_manifest_pages():
    data = json.loads((MOD_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert data.get("config", {}).get("planner_pages_via_mod") is True
    assert (MOD_DIR / "frontend" / "routes.js").is_file()


def test_list_planner_pages_registry():
    from app.mod_sdk.planner_pages_compat import list_planner_pages_registry

    reg = list_planner_pages_registry()
    assert reg.get("page_count") >= 3
    assert reg.get("chat_mod_path") == "/mod/xcagi-planner-bridge/chat"


def test_planner_pages_registry_physical():
    from app.mod_sdk.planner_pages_compat import list_planner_pages_registry

    reg = list_planner_pages_registry()
    manifest = json.loads((MOD_DIR / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("config", {}).get("views_physical"):
        assert reg.get("component_source") == "mod.frontend.views (P physical)"
        assert reg.get("views_physical") is True
