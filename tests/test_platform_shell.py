# -*- coding: utf-8 -*-

from __future__ import annotations

import pytest

from app.mod_sdk.platform_shell import (
    BRIDGE_MOD_HOST_APIS,
    CORE_WORKFLOW_MOD_ID,
    MINIMAL_HOST_MOD_IDS,
    PROTECTED_CLIENT_MOD_IDS,
    build_platform_shell_payload,
)


@pytest.fixture(autouse=True)
def _isolate_edition_and_sku_env(monkeypatch):
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


def test_build_platform_shell_payload(monkeypatch):
    monkeypatch.delenv("XCAGI_GENERIC_EDITION", raising=False)
    monkeypatch.delenv("XCAGI_MINIMAL_EDITION", raising=False)
    monkeypatch.delenv("XCAGI_EDITION", raising=False)
    data = build_platform_shell_payload(["xcagi-approval-bridge", "taiyangniao-pro"])
    assert data["core_workflow_mod_id"] == CORE_WORKFLOW_MOD_ID
    assert set(data["protected_client_mod_ids"]) == set(PROTECTED_CLIENT_MOD_IDS)
    bridges = {b["mod_id"]: b for b in data["bridge_mods"]}
    assert bridges["xcagi-approval-bridge"]["installed"] is True
    assert bridges["xcagi-planner-bridge"]["installed"] is False
    assert (
        bridges["xcagi-approval-bridge"]["host_api_prefixes"]
        == BRIDGE_MOD_HOST_APIS["xcagi-approval-bridge"]
    )
    assert "platform_shell_mode" in data
    assert "frontend_shell_hint" in data
    assert data.get("edition") == "full"
    assert "generic_host_mod_ids" in data


def test_build_platform_shell_generic_edition(monkeypatch):
    monkeypatch.setenv("XCAGI_GENERIC_EDITION", "1")
    data = build_platform_shell_payload([])
    assert data.get("edition") == "generic"
    assert data.get("platform_shell_mode") is True
    assert "xcagi-planner-bridge" in data.get("generic_host_mod_ids", [])


def test_build_platform_shell_minimal_edition(monkeypatch):
    monkeypatch.setenv("XCAGI_MINIMAL_EDITION", "1")
    data = build_platform_shell_payload(list(MINIMAL_HOST_MOD_IDS))
    assert data.get("edition") == "minimal"
    assert data.get("minimal_pack_installed") is True
    assert data.get("minimal_host_mod_ids") == list(MINIMAL_HOST_MOD_IDS)
