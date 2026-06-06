# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MOD_DIR = REPO / "mods" / "xcagi-lan-license-bridge"


def test_lan_manifest_facade_flag():
    data = json.loads((MOD_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert data.get("config", {}).get("lan_facade") is True


def test_lan_blueprints_delegate_routes():
    text = (MOD_DIR / "backend" / "blueprints.py").read_text(encoding="utf-8")
    assert "/lan/activate" in text
    assert "/lan/admin/keys" in text
    assert "app.fastapi_routes.lan_routes" in text


def test_list_lan_facade_registry_mod(monkeypatch):
    from app.mod_sdk import lan_compat as lc

    monkeypatch.setattr(lc, "is_lan_via_mod_enabled", lambda: True)
    data = lc.list_lan_facade_registry()
    from tests.mod_sdk_expectations import MOD_FACADE_EXECUTION_PATHS

    assert data.get("execution_path") in MOD_FACADE_EXECUTION_PATHS
    assert data.get("endpoint_count", 0) >= 10


def test_platform_shell_lists_lan_facade():
    from app.mod_sdk.platform_shell import BRIDGE_MOD_HOST_APIS

    prefixes = BRIDGE_MOD_HOST_APIS.get("xcagi-lan-license-bridge") or []
    assert any("xcagi-lan-license-bridge" in p for p in prefixes)
