# -*- coding: utf-8 -*-
"""桌面双 SKU 发行：personal / enterprise。"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Literal

from app.mod_sdk.erp_domain_compat import ERP_DOMAIN_BRIDGE_MOD_ID
from app.mod_sdk.host_profile import (
    bundled_mod_ids_for_profile_sku,
    load_host_profile,
    package_stage_mod_ids_for_sku,
)
from app.mod_sdk.platform_shell import GENERIC_HOST_MOD_IDS, MINIMAL_HOST_MOD_IDS

logger = logging.getLogger(__name__)

ProductSku = Literal["personal", "enterprise"]

SKU_AUX_MOD_IDS: tuple[str, ...] = (
    "xcagi-planner-excel-tools",
    "wechat-contacts-ai-employee",
    "lan-gate-ai-employee",
)


def _profile_or_legacy_mod_ids(sku: ProductSku, legacy: tuple[str, ...]) -> tuple[str, ...]:
    profile_ids = bundled_mod_ids_for_profile_sku(sku)
    return tuple(profile_ids) if profile_ids else legacy


PERSONAL_HOST_MOD_IDS: tuple[str, ...] = _profile_or_legacy_mod_ids(
    "personal", MINIMAL_HOST_MOD_IDS
)

ENTERPRISE_HOST_MOD_IDS: tuple[str, ...] = _profile_or_legacy_mod_ids(
    "enterprise",
    GENERIC_HOST_MOD_IDS + SKU_AUX_MOD_IDS,
)

SKU_BUNDLED_MOD_IDS: dict[ProductSku, tuple[str, ...]] = {
    "personal": PERSONAL_HOST_MOD_IDS,
    "enterprise": ENTERPRISE_HOST_MOD_IDS,
}

SKU_FRONTEND_EDITION: dict[ProductSku, str] = {
    "personal": "minimal",
    "enterprise": "full",
}

SKU_RUNTIME_EDITION: dict[ProductSku, str] = {
    "personal": "minimal",
    "enterprise": "full",
}

SKU_BLOCKED_MOD_IDS: dict[ProductSku, frozenset[str]] = {
    "personal": frozenset({ERP_DOMAIN_BRIDGE_MOD_ID}),
    "enterprise": frozenset(),
}

SKU_EXCLUDED_FROM_BUNDLE: frozenset[str] = frozenset(
    {
        "taiyangniao-pro",
        "sz-qsm-pro",
        "_employees",
        "industry-solutions",
    }
)

_ERP_BLOCKED_MESSAGE = "ERP 模块仅在企业版中提供，请下载 XCAGI 企业版安装包。"


def normalize_product_sku(raw: str | None) -> ProductSku | None:
    if not raw:
        return None
    key = raw.strip().lower()
    if key in ("personal", "enterprise"):
        return key  # type: ignore[return-value]
    return None


def _read_product_sku_file() -> ProductSku | None:
    candidates: list[Path] = []
    for raw in (os.environ.get("XCAGI_PRODUCT_SKU_FILE"),):
        if raw:
            candidates.append(Path(raw).expanduser())
    for env_key in ("XCAGI_RESOURCES_DIR", "XCAGI_DESKTOP_RESOURCES"):
        raw = os.environ.get(env_key)
        if raw:
            candidates.append(Path(raw) / "product-sku.json")
    try:
        import sys

        if getattr(sys, "frozen", False):
            meipass = Path(getattr(sys, "_MEIPASS", ""))
            if meipass:
                candidates.append(meipass / "product-sku.json")
    except Exception:
        pass
    for path in candidates:
        try:
            if not path.is_file():
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            sku = normalize_product_sku(str(data.get("sku") or data.get("product_sku") or ""))
            if sku:
                return sku
        except Exception:
            logger.debug("product-sku.json read failed: %s", path, exc_info=True)
    return None


def resolve_product_sku() -> ProductSku | None:
    """进程 SKU：环境变量优先，其次安装资源 product-sku.json。"""
    sku = normalize_product_sku(os.environ.get("XCAGI_PRODUCT_SKU"))
    if sku:
        return sku
    return _read_product_sku_file()


def bundled_mod_ids_for_sku(sku: ProductSku | None = None) -> tuple[str, ...]:
    key = sku or resolve_product_sku()
    if key:
        profile_ids = bundled_mod_ids_for_profile_sku(key)
        if profile_ids:
            return profile_ids
        return SKU_BUNDLED_MOD_IDS[key]
    return ()


def package_stage_mod_ids(sku: ProductSku | None = None) -> tuple[str, ...]:
    """安装包 stage 白名单（与 config/host_profiles 一致）。"""
    key = sku or resolve_product_sku()
    if key:
        return package_stage_mod_ids_for_sku(key)
    return ()


def blocked_mod_ids_for_sku(sku: ProductSku | None = None) -> frozenset[str]:
    key = sku or resolve_product_sku()
    if not key:
        return frozenset()
    prof = load_host_profile(key)
    blocked = prof.get("blocked_mod_ids")
    if isinstance(blocked, list):
        return frozenset(str(x) for x in blocked)
    return SKU_BLOCKED_MOD_IDS.get(key, frozenset())


def is_mod_blocked_for_sku(mod_id: str, sku: ProductSku | None = None) -> bool:
    key = sku or resolve_product_sku()
    if not key:
        return False
    return mod_id in blocked_mod_ids_for_sku(key)


def assert_mod_allowed_for_sku(mod_id: str, sku: ProductSku | None = None) -> None:
    if is_mod_blocked_for_sku(mod_id, sku):
        raise PermissionError(_ERP_BLOCKED_MESSAGE)


def assert_bootstrap_edition_allowed(requested_edition: str | None) -> None:
    """个人 SKU 禁止通过 API 请求会误导为「全量/ERP」的 edition 参数。"""
    sku = resolve_product_sku()
    if not sku or sku == "enterprise":
        return
    ed = (requested_edition or "").strip().lower()
    if not ed:
        return
    if ed == "full":
        raise PermissionError("当前安装为企业/个人 SKU 限制版，不可 bootstrap full edition 包。")
    if sku == "personal" and ed == "generic":
        raise PermissionError("个人版仅支持 minimal 宿主包，不可 bootstrap generic edition。")


def configure_sku_edition_env(sku: ProductSku | None = None) -> ProductSku | None:
    """根据 SKU 设置 XCAGI_EDITION / DEFAULT_EDITION 等环境变量。"""
    key = sku or resolve_product_sku()
    if not key:
        return None
    os.environ.setdefault("XCAGI_PRODUCT_SKU", key)
    runtime = SKU_RUNTIME_EDITION[key]
    os.environ.setdefault("XCAGI_DEFAULT_EDITION", runtime)
    os.environ.setdefault("XCAGI_EDITION", runtime)
    os.environ.setdefault("XCAGI_PLATFORM_SHELL", "1")
    if runtime == "minimal":
        os.environ.setdefault("XCAGI_MINIMAL_EDITION", "1")
    elif runtime == "generic":
        os.environ.setdefault("XCAGI_GENERIC_EDITION", "1")
    return key


__all__ = [
    "ProductSku",
    "SKU_AUX_MOD_IDS",
    "ENTERPRISE_HOST_MOD_IDS",
    "PERSONAL_HOST_MOD_IDS",
    "SKU_BUNDLED_MOD_IDS",
    "SKU_FRONTEND_EDITION",
    "SKU_RUNTIME_EDITION",
    "SKU_BLOCKED_MOD_IDS",
    "SKU_EXCLUDED_FROM_BUNDLE",
    "normalize_product_sku",
    "resolve_product_sku",
    "bundled_mod_ids_for_sku",
    "package_stage_mod_ids",
    "blocked_mod_ids_for_sku",
    "is_mod_blocked_for_sku",
    "assert_mod_allowed_for_sku",
    "assert_bootstrap_edition_allowed",
    "configure_sku_edition_env",
]
