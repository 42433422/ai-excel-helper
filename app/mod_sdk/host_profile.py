# -*- coding: utf-8 -*-
"""宿主配置 Profile：从 FHD/config 加载 SKU / bridge / 行业 / 工作流员工目录，替代散落硬编码。"""

from __future__ import annotations

import json
import logging
import os
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.mod_sdk.product_skus import ProductSku

logger = logging.getLogger(__name__)


def _resolve_product_sku() -> str | None:
    """轻量 SKU 解析：勿 import product_skus（与 platform_shell 模块初始化互引）。"""
    raw = os.environ.get("XCAGI_PRODUCT_SKU", "").strip().lower()
    if raw in ("personal", "enterprise"):
        return raw
    for env_key in ("XCAGI_PRODUCT_SKU_FILE",):
        p = os.environ.get(env_key, "").strip()
        if p:
            doc = _load_json(Path(p).expanduser())
            if doc:
                sku = str(doc.get("sku") or doc.get("product_sku") or "").strip().lower()
                if sku in ("personal", "enterprise"):
                    return sku
    for env_key in ("XCAGI_RESOURCES_DIR", "XCAGI_DESKTOP_RESOURCES"):
        base = os.environ.get(env_key, "").strip()
        if base:
            doc = _load_json(Path(base) / "product-sku.json")
            if doc:
                sku = str(doc.get("sku") or doc.get("product_sku") or "").strip().lower()
                if sku in ("personal", "enterprise"):
                    return sku
    return None


PROFILE_SCHEMA_VERSION = 1
INDUSTRY_PRESETS_SCHEMA_VERSION = 1
WORKFLOW_CATALOG_SCHEMA_VERSION = 1

# --- Legacy fallbacks (match pre-profile constants) ---
_LEGACY_BRIDGE_MOD_HOST_APIS: dict[str, list[str]] = {
    "xcagi-approval-bridge": [
        "/api/mod/xcagi-approval-bridge/requests",
        "/api/approval",
    ],
    "xcagi-lan-license-bridge": [
        "/api/mod/xcagi-lan-license-bridge/lan",
        "/api/lan",
    ],
    "xcagi-model-payment-bridge": [
        "/api/mod/xcagi-model-payment-bridge/model-payment",
        "/api/model-payment",
    ],
    "xcagi-planner-bridge": [
        "/api/mod/xcagi-planner-bridge/chat",
        "/mod/xcagi-planner-bridge/ai-ecosystem",
        "/mod/xcagi-planner-bridge/brain",
        "/api/ai/chat",
        "/api/ai/intent",
    ],
    "xcagi-neuro-bus-bridge": [
        "/api/mod/xcagi-neuro-bus-bridge/neurobus",
        "/api/mod/xcagi-neuro-bus-bridge/handlers",
        "/api/neurobus",
        "/api/neuro",
    ],
    "xcagi-erp-domain-bridge": [
        "/api/mod/xcagi-erp-domain-bridge/products",
        "/api/mod/xcagi-erp-domain-bridge/customers",
        "/api/mod/xcagi-erp-domain-bridge/shipment",
        "/api/mod/xcagi-erp-domain-bridge/wechat",
        "/api/mod/xcagi-erp-domain-bridge/wechat_contacts",
    ],
    "xcagi-office-employee-pack-bridge": [
        "/api/mod/xcagi-office-employee-pack-bridge/catalog",
        "/api/mods/",
    ],
    "xcagi-customer-service-bridge": [
        "/api/mod/xcagi-customer-service-bridge/status",
        "/mod/xcagi-customer-service-bridge/enterprise-customer-service",
        "/mod/xcagi-customer-service-bridge/internal-customer-service",
    ],
}

_LEGACY_MINIMAL_HOST_MOD_IDS: tuple[str, ...] = (
    "xcagi-planner-bridge",
    "xcagi-neuro-bus-bridge",
    "xcagi-office-employee-pack-bridge",
)

_LEGACY_GENERIC_HOST_MOD_IDS: tuple[str, ...] = (
    "xcagi-planner-bridge",
    "xcagi-erp-domain-bridge",
    "xcagi-workflow-visualization-bridge",
    "xcagi-approval-bridge",
    "xcagi-lan-license-bridge",
    "xcagi-model-payment-bridge",
    "xcagi-neuro-bus-bridge",
    "xcagi-office-employee-pack-bridge",
    "xcagi-customer-service-bridge",
)

_LEGACY_PROTECTED: tuple[str, ...] = ("taiyangniao-pro", "sz-qsm-pro")
_LEGACY_CORE_WORKFLOW = "xcagi-workflow-visualization-bridge"
_LEGACY_PLATFORM_PREFIXES: list[str] = [
    "/api/print",
    "/api/shipment",
    "/api/mods",
    "/api/mod-store",
    "/api/wechat",
    "/api/products",
    "/api/customers",
    "/api/orders",
    "/api/inventory",
    "/api/ocr",
    "/api/auth",
    "/api/system",
]

_LEGACY_SKU_BUNDLED: dict[str, tuple[str, ...]] = {
    "personal": _LEGACY_MINIMAL_HOST_MOD_IDS,
    "enterprise": _LEGACY_GENERIC_HOST_MOD_IDS
    + ("xcagi-planner-excel-tools", "wechat-contacts-ai-employee"),
}

_LEGACY_STAGE: dict[str, tuple[str, ...]] = {
    "personal": (
        "xcagi-planner-bridge",
        "xcagi-neuro-bus-bridge",
        "xcagi-office-employee-pack-bridge",
    ),
    "enterprise": (
        "xcagi-planner-bridge",
        "xcagi-erp-domain-bridge",
        "xcagi-core-workflow-employees",
        "xcagi-approval-bridge",
        "xcagi-lan-license-bridge",
        "xcagi-model-payment-bridge",
        "xcagi-neuro-bus-bridge",
        "xcagi-office-employee-pack-bridge",
        "xcagi-customer-service-bridge",
        "xcagi-planner-excel-tools",
        "wechat-contacts-ai-employee",
    ),
}


def resolve_fhd_config_dir() -> Path | None:
    """FHD 仓库 config/ 目录（源码树或 XCAGI_FHD_ROOT）。"""
    for raw in (os.environ.get("XCAGI_FHD_ROOT"), os.environ.get("XCAGI_REPO_ROOT")):
        if raw:
            p = Path(raw).expanduser().resolve() / "config"
            if p.is_dir():
                return p
    here = Path(__file__).resolve()
    for parent in here.parents:
        trial = parent / "config"
        if trial.is_dir() and (trial / "host_profiles").is_dir():
            return trial
    return None


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(base)
    for key, val in overlay.items():
        if key in out and isinstance(out[key], dict) and isinstance(val, dict):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = val
    return out


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        logger.debug("host_profile: failed to read %s", path, exc_info=True)
        return None


def _validate_profile_schema(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    ver = data.get("schema_version")
    if ver is not None and int(ver) != PROFILE_SCHEMA_VERSION:
        errors.append(
            f"PROFILE_SCHEMA_MISMATCH: expected schema_version {PROFILE_SCHEMA_VERSION}, got {ver}"
        )
    for key in ("sku", "package_stage_ids", "sku_bundled_mod_ids", "bridge_api_map"):
        if key not in data:
            errors.append(f"profile missing required key: {key}")
    return errors


@lru_cache(maxsize=8)
def _load_merged_profile(sku: str) -> dict[str, Any] | None:
    cfg = resolve_fhd_config_dir()
    if cfg is None:
        return None
    base = _load_json(cfg / "host_profiles" / "_base.json")
    overlay = _load_json(cfg / "host_profiles" / f"{sku}.json")
    if not base or not overlay:
        return None
    merged = _deep_merge(base, overlay)
    merged["sku"] = sku
    return merged


def get_profile_validation_errors(sku: str | None = None) -> list[str]:
    key = sku or _resolve_product_sku()
    if not key:
        return []
    data = _load_merged_profile(key)
    if data is None:
        return []
    return _validate_profile_schema(data)


def load_host_profile(sku: str | None = None) -> dict[str, Any]:
    """返回当前 SKU 的合并 profile；缺失文件时返回 legacy 合成结构。"""
    key = sku or _resolve_product_sku() or "enterprise"
    data = _load_merged_profile(key)
    if data is not None:
        errs = _validate_profile_schema(data)
        if errs:
            logger.warning("host_profile validation: %s", "; ".join(errs))
        return data
    return _legacy_profile_for_sku(key)


def _legacy_profile_for_sku(sku: str) -> dict[str, Any]:
    edition_map = {"personal": "minimal", "enterprise": "full"}
    ed = edition_map.get(sku, "full")
    erp = "xcagi-erp-domain-bridge"
    blocked = [erp] if sku == "personal" else []
    return {
        "schema_version": PROFILE_SCHEMA_VERSION,
        "sku": sku,
        "runtime_edition": ed,
        "frontend_edition": ed,
        "workflow_delivery": "monolith",
        "workflow_monolith_mod_id": "xcagi-core-workflow-employees",
        "workflow_split_mod_ids": list(_LEGACY_GENERIC_HOST_MOD_IDS),
        "package_stage_ids": list(_LEGACY_STAGE.get(sku, _LEGACY_STAGE["enterprise"])),
        "sku_bundled_mod_ids": list(
            _LEGACY_SKU_BUNDLED.get(sku, _LEGACY_SKU_BUNDLED["enterprise"])
        ),
        "blocked_mod_ids": blocked,
        "excluded_from_bundle": list(
            {"taiyangniao-pro", "sz-qsm-pro", "_employees", "industry-solutions"}
        ),
        "minimal_host_mod_ids": list(_LEGACY_MINIMAL_HOST_MOD_IDS),
        "generic_host_mod_ids": list(_LEGACY_GENERIC_HOST_MOD_IDS),
        "bridge_api_map": deepcopy(_LEGACY_BRIDGE_MOD_HOST_APIS),
        "platform_shell_api_prefixes": list(_LEGACY_PLATFORM_PREFIXES),
        "protected_client_mod_ids": list(_LEGACY_PROTECTED),
        "core_workflow_mod_id": _LEGACY_CORE_WORKFLOW,
        "client_mod_policies": {
            "client_primary_erp_mod_id": "taiyangniao-pro",
            "suppress_generic_shell_mod_ids": ["taiyangniao-pro"],
            "protected_ids": list(_LEGACY_PROTECTED),
        },
        "employee_registry_rules": {
            "workflow_employee_id_prefixes": ["xcagi-workflow-employee-"],
            "exclude_id_suffixes": ["-bridge"],
            "exclude_artifact_types": ["employee_pack"],
            "exclude_mod_ids": ["xcagi-host-foundation-employee"],
            "non_workflow_desk_employee_patterns": [
                "^host_foundation$",
                "-(?:generate|full-read)-employee$",
            ],
        },
        "editions": {
            "minimal": {"legacy_routes_enabled": False},
            "generic": {"legacy_routes_enabled": False},
            "full": {"legacy_routes_enabled": True},
        },
        "sku_aux_mod_ids": ["xcagi-planner-excel-tools", "wechat-contacts-ai-employee"],
        "erp_domain_bridge_mod_id": erp,
        "_source": "legacy_fallback",
    }


@lru_cache(maxsize=1)
def load_industry_presets_document() -> dict[str, Any]:
    cfg = resolve_fhd_config_dir()
    if cfg:
        doc = _load_json(cfg / "industry_presets.json")
        if doc and isinstance(doc.get("presets"), dict):
            return doc
    return {
        "schema_version": INDUSTRY_PRESETS_SCHEMA_VERSION,
        "preset_ids": ["通用"],
        "presets": {},
    }


@lru_cache(maxsize=1)
def load_workflow_employee_catalog() -> dict[str, Any]:
    cfg = resolve_fhd_config_dir()
    if cfg:
        doc = _load_json(cfg / "workflow_employee_catalog.json")
        if doc:
            return doc
    return {
        "schema_version": WORKFLOW_CATALOG_SCHEMA_VERSION,
        "workflow_viz_bridge_mod_id": _LEGACY_CORE_WORKFLOW,
        "legacy_monolith_mod_id": "xcagi-core-workflow-employees",
        "split_mod_entries": [],
        "default_mod_ids": [],
        "default_employee_ids": [],
    }


def get_bridge_mod_host_apis() -> dict[str, list[str]]:
    prof = load_host_profile()
    m = prof.get("bridge_api_map")
    if isinstance(m, dict) and m:
        return {str(k): list(v) if isinstance(v, list) else [] for k, v in m.items()}
    return deepcopy(_LEGACY_BRIDGE_MOD_HOST_APIS)


def get_minimal_host_mod_ids() -> tuple[str, ...]:
    prof = load_host_profile()
    ids = prof.get("minimal_host_mod_ids")
    if isinstance(ids, list) and ids:
        return tuple(str(x) for x in ids)
    return _LEGACY_MINIMAL_HOST_MOD_IDS


def get_generic_host_mod_ids() -> tuple[str, ...]:
    prof = load_host_profile()
    ids = prof.get("generic_host_mod_ids")
    if isinstance(ids, list) and ids:
        return tuple(str(x) for x in ids)
    return _LEGACY_GENERIC_HOST_MOD_IDS


def get_protected_client_mod_ids() -> tuple[str, ...]:
    prof = load_host_profile()
    ids = prof.get("protected_client_mod_ids")
    if isinstance(ids, list) and ids:
        return tuple(str(x) for x in ids)
    return _LEGACY_PROTECTED


def get_core_workflow_mod_id() -> str:
    prof = load_host_profile()
    return str(prof.get("core_workflow_mod_id") or _LEGACY_CORE_WORKFLOW)


def get_platform_shell_api_prefixes() -> list[str]:
    prof = load_host_profile()
    ids = prof.get("platform_shell_api_prefixes")
    if isinstance(ids, list) and ids:
        return [str(x) for x in ids]
    return list(_LEGACY_PLATFORM_PREFIXES)


def get_client_mod_policies() -> dict[str, Any]:
    prof = load_host_profile()
    pol = prof.get("client_mod_policies")
    if isinstance(pol, dict):
        return pol
    return {
        "client_primary_erp_mod_id": "taiyangniao-pro",
        "suppress_generic_shell_mod_ids": ["taiyangniao-pro"],
        "protected_ids": list(_LEGACY_PROTECTED),
    }


def get_employee_registry_rules() -> dict[str, Any]:
    prof = load_host_profile()
    rules = prof.get("employee_registry_rules")
    if isinstance(rules, dict):
        return rules
    return load_host_profile()["employee_registry_rules"]


def bundled_mod_ids_for_profile_sku(sku: str | None = None) -> tuple[str, ...]:
    key = sku or _resolve_product_sku()
    if not key:
        return ()
    prof = load_host_profile(key)
    ids = prof.get("sku_bundled_mod_ids")
    if isinstance(ids, list) and ids:
        return tuple(str(x) for x in ids)
    return _LEGACY_SKU_BUNDLED.get(key, ())


def package_stage_mod_ids_for_sku(sku: str | None = None) -> tuple[str, ...]:
    key = sku or _resolve_product_sku()
    if not key:
        key = "enterprise"
    prof = load_host_profile(key)  # type: ignore[arg-type]
    ids = prof.get("package_stage_ids")
    if isinstance(ids, list) and ids:
        return tuple(str(x) for x in ids)
    return _LEGACY_STAGE.get(key, _LEGACY_STAGE["enterprise"])


def workflow_delivery_mod_ids_for_package(sku: str | None = None) -> tuple[str, ...]:
    """按 workflow_delivery 解析安装包应包含的工作流 Mod（monolith 或 split 列表）。"""
    prof = load_host_profile(sku)
    delivery = str(prof.get("workflow_delivery") or "monolith").strip().lower()
    if delivery == "split":
        split_ids = prof.get("workflow_split_mod_ids")
        if isinstance(split_ids, list) and split_ids:
            return tuple(str(x) for x in split_ids)
    mono = str(prof.get("workflow_monolith_mod_id") or "xcagi-core-workflow-employees")
    return (mono,)


def edition_legacy_routes_enabled(edition: str | None = None) -> bool:
    from app.mod_sdk.edition_policy import resolve_edition

    prof = load_host_profile()
    ed = (edition or resolve_edition() or "full").strip().lower()
    editions = prof.get("editions")
    if isinstance(editions, dict):
        block = editions.get(ed)
        if isinstance(block, dict) and "legacy_routes_enabled" in block:
            return bool(block["legacy_routes_enabled"])
    return ed == "full"


def scan_workflow_employee_catalog_from_mods(mods_root: Path | None = None) -> dict[str, Any]:
    """扫描 mods 目录补充 workflow_employee_catalog（运行时）。"""
    doc = dict(load_workflow_employee_catalog())
    root = mods_root
    if root is None:
        from app.mod_sdk.edition_policy import bundled_mods_dir

        root = bundled_mods_dir()
    if root is None or not root.is_dir():
        return doc
    entries: list[dict[str, Any]] = []
    for manifest_path in sorted(root.glob("xcagi-workflow-employee-*/manifest.json")):
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        wf_list = data.get("workflow_employees") or []
        wf = wf_list[0] if wf_list else {}
        cfg = data.get("config") if isinstance(data.get("config"), dict) else {}
        entries.append(
            {
                "mod_id": str(data.get("id") or manifest_path.parent.name),
                "employee_id": str(wf.get("id") or cfg.get("employee_id") or ""),
                "label": str(wf.get("label") or data.get("name") or ""),
                "panel_title": wf.get("panel_title"),
                "panel_summary": wf.get("panel_summary"),
            }
        )
    if entries:
        doc["split_mod_entries"] = entries
        doc["default_mod_ids"] = [e["mod_id"] for e in entries if e.get("mod_id")]
        doc["default_employee_ids"] = [e["employee_id"] for e in entries if e.get("employee_id")]
    return doc


def build_host_profile_api_payload() -> dict[str, Any]:
    prof = load_host_profile()
    return {
        "schema_version": prof.get("schema_version", PROFILE_SCHEMA_VERSION),
        "profile": prof,
        "validation_errors": get_profile_validation_errors(),
        "industry_presets_meta": {
            "schema_version": load_industry_presets_document().get("schema_version"),
            "preset_count": len(load_industry_presets_document().get("presets") or {}),
        },
        "workflow_catalog_meta": {
            "schema_version": load_workflow_employee_catalog().get("schema_version"),
            "delivery": prof.get("workflow_delivery"),
        },
    }


__all__ = [
    "PROFILE_SCHEMA_VERSION",
    "resolve_fhd_config_dir",
    "load_host_profile",
    "get_profile_validation_errors",
    "load_industry_presets_document",
    "load_workflow_employee_catalog",
    "get_bridge_mod_host_apis",
    "get_minimal_host_mod_ids",
    "get_generic_host_mod_ids",
    "get_protected_client_mod_ids",
    "get_core_workflow_mod_id",
    "get_platform_shell_api_prefixes",
    "get_client_mod_policies",
    "get_employee_registry_rules",
    "bundled_mod_ids_for_profile_sku",
    "package_stage_mod_ids_for_sku",
    "workflow_delivery_mod_ids_for_package",
    "edition_legacy_routes_enabled",
    "scan_workflow_employee_catalog_from_mods",
    "build_host_profile_api_payload",
]
