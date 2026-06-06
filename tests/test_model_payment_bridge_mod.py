# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MOD_DIR = REPO / "mods" / "xcagi-model-payment-bridge"


def test_model_payment_manifest_facade_flag():
    data = json.loads((MOD_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert data.get("config", {}).get("model_payment_facade") is True


def test_model_payment_blueprints_delegate_routes():
    text = (MOD_DIR / "backend" / "blueprints.py").read_text(encoding="utf-8")
    assert "/model-payment/plans" in text
    assert "/model-payment/checkout" in text
    assert "app.fastapi_routes.model_payment" in text


def test_list_model_payment_facade_registry_mod(monkeypatch):
    from app.mod_sdk import model_payment_compat as mpc

    monkeypatch.setattr(mpc, "is_model_payment_via_mod_enabled", lambda: True)
    data = mpc.list_model_payment_facade_registry()
    from tests.mod_sdk_expectations import MOD_FACADE_EXECUTION_PATHS

    assert data.get("execution_path") in MOD_FACADE_EXECUTION_PATHS
    assert data.get("endpoint_count", 0) >= 5


def test_platform_shell_lists_model_payment_facade():
    from app.mod_sdk.platform_shell import BRIDGE_MOD_HOST_APIS

    prefixes = BRIDGE_MOD_HOST_APIS.get("xcagi-model-payment-bridge") or []
    assert any("xcagi-model-payment-bridge" in p for p in prefixes)
