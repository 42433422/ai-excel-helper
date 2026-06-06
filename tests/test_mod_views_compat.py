# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_physical_views_on_disk():
    from app.mod_sdk.mod_views_compat import PHYSICAL_VIEW_MODS

    for mod_id, files in PHYSICAL_VIEW_MODS.items():
        mod_dir = REPO / "mods" / mod_id
        assert mod_dir.is_dir(), f"sync mod {mod_id} first"
        for vf in files:
            assert (mod_dir / "frontend" / "views" / vf).is_file()


def test_list_mod_physical_views_registry():
    from app.mod_sdk.mod_views_compat import list_mod_physical_views_registry

    reg = list_mod_physical_views_registry()
    assert reg.get("phase") == "O+"
    assert reg.get("pilot_mod_count", 0) >= 6
    mods = {m["mod_id"]: m for m in reg.get("mods") or []}
    assert mods["xcagi-lan-license-bridge"]["views_physical"] is True
    assert mods["xcagi-approval-bridge"]["views_physical"] is True
    assert mods["xcagi-planner-bridge"]["views_physical"] is True
    assert mods["xcagi-erp-domain-bridge"]["views_physical"] is True
    assert mods["xcagi-model-payment-bridge"]["views_physical"] is True


def test_customer_service_pages_registry_physical():
    from app.mod_sdk.customer_service_pages_compat import list_customer_service_pages_registry

    reg = list_customer_service_pages_registry()
    manifest = json.loads(
        (REPO / "mods" / "xcagi-customer-service-bridge" / "manifest.json").read_text(
            encoding="utf-8"
        )
    )
    if manifest.get("config", {}).get("views_physical"):
        assert reg.get("component_source") == "mod.frontend.views"
