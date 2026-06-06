# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MOD_DIR = REPO / "mods" / "xcagi-customer-service-bridge"


def test_customer_service_manifest_pages():
    assert MOD_DIR.is_dir(), "sync platform mod first"
    data = json.loads((MOD_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert data.get("config", {}).get("customer_service_pages_via_mod") is True
    assert (MOD_DIR / "frontend" / "routes.js").is_file()


def test_list_customer_service_pages_registry():
    from app.mod_sdk.customer_service_pages_compat import list_customer_service_pages_registry

    reg = list_customer_service_pages_registry()
    assert reg.get("page_count") == 2
    assert "/enterprise-customer-service" in reg.get("host_pages", [])
