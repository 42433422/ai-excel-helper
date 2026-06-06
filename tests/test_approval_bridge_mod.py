# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MOD_DIR = REPO / "mods" / "xcagi-approval-bridge"


def test_approval_manifest_facade_flag():
    data = json.loads((MOD_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert data.get("config", {}).get("approval_facade") is True


def test_approval_blueprints_delegate_routes():
    text = (MOD_DIR / "backend" / "blueprints.py").read_text(encoding="utf-8")
    assert "/requests" in text
    assert "/flows" in text
    assert "app.fastapi_routes.approval" in text


def test_list_approval_facade_registry_mod(monkeypatch):
    from app.mod_sdk import approval_compat as ac

    monkeypatch.setattr(ac, "is_approval_via_mod_enabled", lambda: True)
    data = ac.list_approval_facade_registry()
    from tests.mod_sdk_expectations import MOD_FACADE_EXECUTION_PATHS

    assert data.get("execution_path") in MOD_FACADE_EXECUTION_PATHS
    assert data.get("endpoint_count", 0) >= 10


def test_platform_shell_lists_approval_facade():
    from app.mod_sdk.platform_shell import BRIDGE_MOD_HOST_APIS

    prefixes = BRIDGE_MOD_HOST_APIS.get("xcagi-approval-bridge") or []
    assert any("xcagi-approval-bridge" in p for p in prefixes)
