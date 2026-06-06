# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]


def test_model_payment_pages_registry_physical():
    from app.mod_sdk.model_payment_pages_compat import list_model_payment_pages_registry

    reg = list_model_payment_pages_registry()
    manifest = json.loads(
        (REPO / "mods" / "xcagi-model-payment-bridge" / "manifest.json").read_text(encoding="utf-8")
    )
    if manifest.get("config", {}).get("views_physical"):
        assert reg.get("component_source") == "mod.frontend.views (O+ physical)"
        assert reg.get("views_physical") is True
