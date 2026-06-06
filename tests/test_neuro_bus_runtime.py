# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MOD_DIR = REPO / "mods" / "xcagi-neuro-bus-bridge"


def test_neuro_bus_manifest_runtime_phase():
    data = json.loads((MOD_DIR / "manifest.json").read_text(encoding="utf-8"))
    cfg = data.get("config") or {}
    assert cfg.get("neuro_bus_facade") is True
    assert cfg.get("phase") == "S"
    assert (MOD_DIR / "backend" / "bus_runtime_factory.py").is_file()
    assert (MOD_DIR / "backend" / "bus_runtime_adapters.py").is_file()
    assert (MOD_DIR / "backend" / "bus_runtime_providers.py").is_file()


def test_create_bus_runtime_bundle():
    from app.infrastructure.mods.mod_manager import import_mod_backend_py

    mod = import_mod_backend_py(str(MOD_DIR), "xcagi-neuro-bus-bridge", "bus_runtime_factory")
    bundle = mod.create_bus_runtime_bundle()
    assert bundle.get("phase") == "S"
    assert bundle.get("provider_id") == "mod:xcagi-neuro-bus-bridge"
    for key in ("setup", "teardown", "publish", "health"):
        assert callable(bundle[key])


def test_list_neuro_bus_facade_registry_runtime_path(monkeypatch):
    from app.mod_sdk import neuro_bus_compat as compat

    monkeypatch.setattr(compat, "is_neuro_bus_via_mod_enabled", lambda: True)
    data = compat.list_neuro_bus_facade_registry()
    assert data.get("execution_path") == "mod_bus_runtime"
    assert data.get("phase") == "S"


def test_publish_neuro_event_runtime_host_path(monkeypatch):
    from app.mod_sdk import neuro_bus_runtime as rt

    monkeypatch.setattr(rt, "is_neuro_bus_runtime_via_mod_enabled", lambda: False)

    class _Bus:
        is_running = False

    monkeypatch.setattr("app.neuro_bus.bus.get_neuro_bus", lambda: _Bus())
    assert rt.publish_neuro_event_runtime("test.evt", {"x": 1}) is False


def test_run_lifespan_setup_host_path(monkeypatch):
    from app.mod_sdk import neuro_bus_runtime as rt

    monkeypatch.setattr(rt, "is_neuro_bus_runtime_via_mod_enabled", lambda: False)
    calls: list[str] = []

    async def _setup():
        calls.append("setup")

    class _Registry:
        async def initialize_all(self):
            calls.append("domains")

    monkeypatch.setattr("app.neuro_bus.bus_setup.setup_neuro_bus", _setup)
    monkeypatch.setattr(
        "app.neuro_bus.domains.base.get_domain_registry",
        lambda: _Registry(),
    )

    import asyncio

    asyncio.run(rt.run_lifespan_setup())
    assert calls == ["setup", "domains"]


def test_get_neuro_bus_health_runtime_no_recursion(monkeypatch):
    from app.mod_sdk import neuro_bus_runtime as rt

    monkeypatch.setattr(rt, "is_neuro_bus_runtime_via_mod_enabled", lambda: False)

    class _Mgr:
        def get_health(self):
            return {"status": "ok", "source": "host_manager"}

    monkeypatch.setattr("app.neuro_bus.bus_setup.get_neuro_bus_manager", lambda: _Mgr())
    health = rt.get_neuro_bus_health_runtime()
    assert health.get("source") == "host_manager"
