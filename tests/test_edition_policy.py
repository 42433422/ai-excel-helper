# -*- coding: utf-8 -*-

from __future__ import annotations

import os

import pytest

from app.mod_sdk.edition_policy import (
    configure_edition_defaults,
    resolve_edition,
    seed_edition_mods_from_bundle,
    should_register_host_legacy_routes,
)
from app.mod_sdk.platform_shell import GENERIC_HOST_MOD_IDS, MINIMAL_HOST_MOD_IDS


@pytest.fixture(autouse=True)
def _isolate_edition_and_sku_env(monkeypatch):
    """全量套件中其它用例可能写入 SKU/EDITION，导致本文件断言 full。"""
    for key in (
        "XCAGI_PRODUCT_SKU",
        "XCAGI_EDITION",
        "XCAGI_GENERIC_EDITION",
        "XCAGI_MINIMAL_EDITION",
        "XCAGI_DEFAULT_EDITION",
        "XCAGI_PRODUCT_SKU_FILE",
        "XCAGI_RESOURCES_DIR",
        "XCAGI_DESKTOP_RESOURCES",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(
        "app.mod_sdk.product_skus.resolve_product_sku",
        lambda: None,
    )
    monkeypatch.setattr(
        "app.mod_sdk.host_profile._resolve_product_sku",
        lambda: None,
    )


def test_resolve_edition_generic(monkeypatch):
    monkeypatch.delenv("XCAGI_EDITION", raising=False)
    monkeypatch.setenv("XCAGI_GENERIC_EDITION", "1")
    monkeypatch.delenv("XCAGI_MINIMAL_EDITION", raising=False)
    assert resolve_edition() == "generic"


def test_resolve_edition_minimal(monkeypatch):
    monkeypatch.setenv("XCAGI_MINIMAL_EDITION", "1")
    monkeypatch.delenv("XCAGI_GENERIC_EDITION", raising=False)
    assert resolve_edition() == "minimal"


def test_legacy_routes_skipped_for_generic(monkeypatch):
    monkeypatch.setenv("XCAGI_GENERIC_EDITION", "1")
    monkeypatch.delenv("XCAGI_REGISTER_LEGACY_ROUTES", raising=False)
    assert should_register_host_legacy_routes() is False


def test_legacy_routes_for_full(monkeypatch):
    monkeypatch.delenv("XCAGI_GENERIC_EDITION", raising=False)
    monkeypatch.delenv("XCAGI_MINIMAL_EDITION", raising=False)
    monkeypatch.delenv("XCAGI_EDITION", raising=False)
    assert should_register_host_legacy_routes() is True


def test_configure_edition_defaults_desktop(monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.delenv("PYTEST_VERSION", raising=False)
    monkeypatch.delenv("XCAGI_GENERIC_EDITION", raising=False)
    monkeypatch.delenv("XCAGI_EDITION", raising=False)
    configure_edition_defaults(desktop=True)
    assert resolve_edition() == "generic"


def test_seed_skips_existing(tmp_path, monkeypatch):
    bundle = tmp_path / "bundle"
    mods = bundle / "xcagi-planner-bridge"
    mods.mkdir(parents=True)
    (mods / "manifest.json").write_text(
        '{"id":"xcagi-planner-bridge","name":"p"}', encoding="utf-8"
    )
    target = tmp_path / "user-mods"
    target.mkdir()
    (target / "xcagi-planner-bridge").mkdir()
    monkeypatch.setenv("XCAGI_BUNDLED_MODS_DIR", str(bundle))
    from app.infrastructure.mods.mod_manager import ModManager

    mm = ModManager(mods_root=str(target))
    monkeypatch.setattr(
        "app.infrastructure.mods.mod_manager.get_mod_manager",
        lambda: mm,
    )
    out = seed_edition_mods_from_bundle("minimal")
    row = next(r for r in out if r["mod_id"] == "xcagi-planner-bridge")
    assert row["status"] == "skipped"


def test_decoupling_adcdfg_complete():
    from app.mod_sdk.decoupling_progress import build_decoupling_progress_payload

    payload = build_decoupling_progress_payload(list(GENERIC_HOST_MOD_IDS))
    assert payload.get("adcdfg_complete") is True
    assert payload.get("composite_percent") == 100
    assert any(m["id"] == "T" for m in payload.get("milestones", []))


@pytest.mark.asyncio
async def test_bootstrap_edition_pack_smoke(monkeypatch, tmp_path):
    bundle = tmp_path / "bundle"
    for mid in MINIMAL_HOST_MOD_IDS:
        d = bundle / mid
        d.mkdir(parents=True)
        (d / "manifest.json").write_text(
            f'{{"id":"{mid}","name":"{mid}","version":"1.0.0"}}',
            encoding="utf-8",
        )
    target = tmp_path / "mods"
    target.mkdir()
    monkeypatch.setenv("XCAGI_BUNDLED_MODS_DIR", str(bundle))
    monkeypatch.setenv("XCAGI_MODS_ROOT", str(target))
    monkeypatch.setenv("XCAGI_MINIMAL_EDITION", "1")

    from app.infrastructure.mods.mod_manager import ModManager

    mm = ModManager(mods_root=str(target))
    monkeypatch.setattr(
        "app.infrastructure.mods.mod_manager.get_mod_manager",
        lambda: mm,
    )

    from app.mod_sdk.edition_bootstrap import bootstrap_edition_pack

    data = await bootstrap_edition_pack("minimal")
    assert data["edition"] == "minimal"
    assert data["expected_count"] == len(MINIMAL_HOST_MOD_IDS)
