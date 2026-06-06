# -*- coding: utf-8 -*-

from __future__ import annotations

import pytest

from app.mod_sdk.deliverable_status import build_deliverable_status
from app.mod_sdk.erp_domain_compat import ERP_DOMAIN_BRIDGE_MOD_ID
from app.mod_sdk.platform_shell import GENERIC_HOST_MOD_IDS, MINIMAL_HOST_MOD_IDS
from app.mod_sdk.product_skus import (
    ENTERPRISE_HOST_MOD_IDS,
    PERSONAL_HOST_MOD_IDS,
)


@pytest.fixture(autouse=True)
def _isolate_sku_env(monkeypatch):
    for key in (
        "XCAGI_PRODUCT_SKU",
        "XCAGI_EDITION",
        "XCAGI_GENERIC_EDITION",
        "XCAGI_MINIMAL_EDITION",
        "XCAGI_PRODUCT_SKU_FILE",
        "XCAGI_RESOURCES_DIR",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr("app.mod_sdk.product_skus.resolve_product_sku", lambda: None)


def test_deliverable_generic_when_pack_complete():
    data = build_deliverable_status(list(GENERIC_HOST_MOD_IDS))
    assert data["edition"] in ("generic", "full", "minimal")
    assert data["generic_pack_installed"] is True
    assert data["deliverable"] is True
    assert data["blockers"] == []


def test_deliverable_generic_blocked_when_incomplete(monkeypatch):
    monkeypatch.setenv("XCAGI_GENERIC_EDITION", "1")
    monkeypatch.delenv("XCAGI_EDITION", raising=False)
    monkeypatch.delenv("XCAGI_MINIMAL_EDITION", raising=False)
    monkeypatch.delenv("XCAGI_PRODUCT_SKU", raising=False)
    data = build_deliverable_status(["xcagi-planner-bridge"])
    assert data["generic_pack_installed"] is False
    assert data["deliverable"] is False
    assert any(b["code"] == "GENERIC_PACK_INCOMPLETE" for b in data["blockers"])


def test_deliverable_minimal_pack(monkeypatch):
    monkeypatch.setenv("XCAGI_MINIMAL_EDITION", "1")
    monkeypatch.delenv("XCAGI_GENERIC_EDITION", raising=False)
    monkeypatch.delenv("XCAGI_PRODUCT_SKU", raising=False)
    data = build_deliverable_status(list(MINIMAL_HOST_MOD_IDS))
    assert data["minimal_pack_installed"] is True
    assert data["deliverable"] is True


def test_deliverable_status_api_route(client):
    r = client.get("/api/platform-shell/deliverable-status")
    assert r.status_code == 200
    body = r.json()
    assert body.get("success") is True
    data = body.get("data", {})
    assert "deliverable" in data
    pf = data.get("product_flow") or {}
    assert pf.get("ui_route") == "/onboarding"
    assert "recommended_step" in pf


def test_deliverable_product_flow_recommended_host_pack(monkeypatch):
    monkeypatch.setenv("XCAGI_GENERIC_EDITION", "1")
    data = build_deliverable_status(["xcagi-planner-bridge"])
    assert data["product_flow"]["recommended_step"] == "host_pack"


def test_deliverable_personal_sku(monkeypatch):
    monkeypatch.setenv("XCAGI_PRODUCT_SKU", "personal")
    monkeypatch.setenv("XCAGI_MINIMAL_EDITION", "1")
    data = build_deliverable_status(list(PERSONAL_HOST_MOD_IDS))
    assert data["product_sku"] == "personal"
    assert data["deliverable"] is True
    assert ERP_DOMAIN_BRIDGE_MOD_ID not in data["expected_mod_ids"]


def test_deliverable_enterprise_requires_erp(monkeypatch):
    monkeypatch.setenv("XCAGI_PRODUCT_SKU", "enterprise")
    data = build_deliverable_status(
        [m for m in ENTERPRISE_HOST_MOD_IDS if m != ERP_DOMAIN_BRIDGE_MOD_ID]
    )
    assert data["deliverable"] is False
    assert any(b["code"] == "ENTERPRISE_ERP_MISSING" for b in data["blockers"])


def test_deliverable_personal_sku_no_erp(monkeypatch):
    monkeypatch.setenv("XCAGI_PRODUCT_SKU", "personal")
    monkeypatch.setenv("XCAGI_MINIMAL_EDITION", "1")
    from app.mod_sdk.product_skus import PERSONAL_HOST_MOD_IDS

    data = build_deliverable_status(list(PERSONAL_HOST_MOD_IDS))
    assert data["deliverable"] is True
    assert ERP_DOMAIN_BRIDGE_MOD_ID not in data["expected_mod_ids"]
