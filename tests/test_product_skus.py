# -*- coding: utf-8 -*-

from __future__ import annotations

import pytest

from app.mod_sdk.erp_domain_compat import ERP_DOMAIN_BRIDGE_MOD_ID
from app.mod_sdk.host_profile import bundled_mod_ids_for_profile_sku
from app.mod_sdk.product_skus import (
    ENTERPRISE_HOST_MOD_IDS,
    PERSONAL_HOST_MOD_IDS,
    assert_bootstrap_edition_allowed,
    assert_mod_allowed_for_sku,
    bundled_mod_ids_for_sku,
    is_mod_blocked_for_sku,
)


def test_enterprise_includes_erp():
    assert ERP_DOMAIN_BRIDGE_MOD_ID in ENTERPRISE_HOST_MOD_IDS


def test_personal_blocks_erp(monkeypatch):
    monkeypatch.setenv("XCAGI_PRODUCT_SKU", "personal")
    assert is_mod_blocked_for_sku(ERP_DOMAIN_BRIDGE_MOD_ID)
    with pytest.raises(PermissionError):
        assert_mod_allowed_for_sku(ERP_DOMAIN_BRIDGE_MOD_ID)


def test_enterprise_allows_erp(monkeypatch):
    monkeypatch.setenv("XCAGI_PRODUCT_SKU", "enterprise")
    assert not is_mod_blocked_for_sku(ERP_DOMAIN_BRIDGE_MOD_ID)


def test_bootstrap_edition_blocked_for_personal(monkeypatch):
    monkeypatch.setenv("XCAGI_PRODUCT_SKU", "personal")
    with pytest.raises(PermissionError):
        assert_bootstrap_edition_allowed("generic")
    with pytest.raises(PermissionError):
        assert_bootstrap_edition_allowed("full")


def test_bundled_mod_ids_for_sku(monkeypatch):
    monkeypatch.setenv("XCAGI_PRODUCT_SKU", "personal")
    assert bundled_mod_ids_for_sku() == PERSONAL_HOST_MOD_IDS
    monkeypatch.setenv("XCAGI_PRODUCT_SKU", "enterprise")
    assert ERP_DOMAIN_BRIDGE_MOD_ID in bundled_mod_ids_for_sku()


@pytest.mark.parametrize(
    ("sku", "constant_ids"),
    [
        ("personal", PERSONAL_HOST_MOD_IDS),
        ("enterprise", ENTERPRISE_HOST_MOD_IDS),
    ],
)
def test_sku_constants_follow_host_profiles(sku, constant_ids):
    assert constant_ids == bundled_mod_ids_for_profile_sku(sku)
