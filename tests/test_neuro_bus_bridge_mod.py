# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MOD_DIR = REPO / "mods" / "xcagi-neuro-bus-bridge"


def test_neuro_bus_manifest_facade_flag():
    data = json.loads((MOD_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert data.get("config", {}).get("neuro_bus_facade") is True
    assert data.get("config", {}).get("neuro_bus_handlers_via_mod") is True
    assert (MOD_DIR / "config" / "neuro_handler_catalog.json").is_file()
    assert (MOD_DIR / "backend" / "handler_providers.py").is_file()


def test_neuro_bus_blueprints_delegate():
    text = (MOD_DIR / "backend" / "blueprints.py").read_text(encoding="utf-8")
    assert "/neurobus/health" in text
    assert "/events/publish" in text
    assert "/handlers/registry" in text
    assert "get_neurobus_health" in text


def test_list_neuro_bus_facade_registry(monkeypatch):
    from app.mod_sdk import neuro_bus_compat as nbc

    monkeypatch.setattr(nbc, "is_neuro_bus_via_mod_enabled", lambda: True)
    data = nbc.list_neuro_bus_facade_registry()
    from tests.mod_sdk_expectations import MOD_FACADE_EXECUTION_PATHS, NEURO_BUS_PHASES

    assert data.get("execution_path") in MOD_FACADE_EXECUTION_PATHS
    assert data.get("phase") in NEURO_BUS_PHASES
    assert "POST /events/publish" in (data.get("endpoints") or [])
