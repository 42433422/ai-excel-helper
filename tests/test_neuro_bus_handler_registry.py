# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MOD_DIR = REPO / "mods" / "xcagi-neuro-bus-bridge"


def test_handler_catalog_has_core_domains():
    data = json.loads(
        (MOD_DIR / "config" / "neuro_handler_catalog.json").read_text(encoding="utf-8")
    )
    ids = {h["domain_id"] for h in data.get("handlers", []) if isinstance(h, dict)}
    assert "product" in ids
    assert "shipment" in ids


def test_handler_providers_list_specs():
    from app.infrastructure.mods.mod_manager import import_mod_backend_py

    mod = import_mod_backend_py(str(MOD_DIR), "xcagi-neuro-bus-bridge", "handler_providers")
    specs = mod.list_handler_specs()
    assert len(specs) >= 5
    assert any(s["domain_id"] == "shipment" for s in specs)


def test_handlers_via_mod_env(monkeypatch):
    from app.mod_sdk.neuro_bus_handler_registry import is_neuro_bus_handlers_via_mod_enabled

    monkeypatch.setenv("XCAGI_NEURO_BUS_HANDLERS_VIA_MOD", "1")
    assert is_neuro_bus_handlers_via_mod_enabled() is True


def test_list_neuro_bus_handler_registry():
    from app.mod_sdk.neuro_bus_handler_registry import list_neuro_bus_handler_registry

    reg = list_neuro_bus_handler_registry()
    assert reg.get("mod_id") == "xcagi-neuro-bus-bridge"
    assert "catalog" in reg


class _FakeBus:
    def __init__(self):
        self.subscriptions = []

    def subscribe(self, event_type, handler, *args, **kwargs):
        self.subscriptions.append(event_type)


def test_register_all_domain_handlers_registers_existing_modules():
    from app.infrastructure.mods.mod_manager import import_mod_backend_py

    mod = import_mod_backend_py(str(MOD_DIR), "xcagi-neuro-bus-bridge", "handler_providers")
    bus = _FakeBus()
    result = mod.register_all_domain_handlers(bus)
    assert result.get("handler_count", 0) >= 5
    assert "product" in result.get("registered", [])
    assert "shipment" in result.get("registered", [])
