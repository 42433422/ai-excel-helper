# -*- coding: utf-8 -*-
"""通用化宿主壳：阶段 4 能力清单（业务在 Mod / 宿主 API 底座）。"""

from __future__ import annotations

import os
from typing import Any

from app.mod_sdk.host_profile import (
    get_bridge_mod_host_apis,
    get_core_workflow_mod_id,
    get_generic_host_mod_ids,
    get_minimal_host_mod_ids,
    get_platform_shell_api_prefixes,
    get_protected_client_mod_ids,
)

# 向后兼容：模块级常量由 profile 解析（缺文件时 fallback 与旧版一致）
BRIDGE_MOD_HOST_APIS: dict[str, list[str]] = get_bridge_mod_host_apis()
PLATFORM_SHELL_API_PREFIXES: list[str] = get_platform_shell_api_prefixes()
PROTECTED_CLIENT_MOD_IDS: tuple[str, ...] = get_protected_client_mod_ids()
CORE_WORKFLOW_MOD_ID: str = get_core_workflow_mod_id()
MINIMAL_HOST_MOD_IDS: tuple[str, ...] = get_minimal_host_mod_ids()
GENERIC_HOST_MOD_IDS: tuple[str, ...] = get_generic_host_mod_ids()


def refresh_platform_shell_constants() -> None:
    """SKU 或 profile 变更后刷新模块级常量（测试 / 热加载）。"""
    global BRIDGE_MOD_HOST_APIS, PLATFORM_SHELL_API_PREFIXES
    global PROTECTED_CLIENT_MOD_IDS, CORE_WORKFLOW_MOD_ID
    global MINIMAL_HOST_MOD_IDS, GENERIC_HOST_MOD_IDS
    from app.mod_sdk import host_profile as hp

    hp._load_merged_profile.cache_clear()
    hp.load_industry_presets_document.cache_clear()
    hp.load_workflow_employee_catalog.cache_clear()
    BRIDGE_MOD_HOST_APIS = get_bridge_mod_host_apis()
    PLATFORM_SHELL_API_PREFIXES = get_platform_shell_api_prefixes()
    PROTECTED_CLIENT_MOD_IDS = get_protected_client_mod_ids()
    CORE_WORKFLOW_MOD_ID = get_core_workflow_mod_id()
    MINIMAL_HOST_MOD_IDS = get_minimal_host_mod_ids()
    GENERIC_HOST_MOD_IDS = get_generic_host_mod_ids()


def _resolve_edition() -> str:
    from app.mod_sdk.edition_policy import resolve_edition

    return resolve_edition()


def build_platform_shell_payload(installed_mod_ids: list[str] | None = None) -> dict[str, Any]:
    bridges_map = get_bridge_mod_host_apis()
    minimal_ids = get_minimal_host_mod_ids()
    generic_ids = get_generic_host_mod_ids()
    protected = get_protected_client_mod_ids()
    shell_prefixes = get_platform_shell_api_prefixes()
    core_wf = get_core_workflow_mod_id()

    installed = set(installed_mod_ids or [])
    bridges = []
    for mod_id, prefixes in bridges_map.items():
        bridges.append(
            {
                "mod_id": mod_id,
                "role": "host_api_bridge",
                "host_api_prefixes": prefixes,
                "installed": mod_id in installed,
            }
        )
    shell_mode = (os.environ.get("XCAGI_PLATFORM_SHELL") or "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    edition = _resolve_edition()
    minimal_ready = all(mid in installed for mid in minimal_ids)
    generic_ready = all(mid in installed for mid in generic_ids)

    from app.mod_sdk.host_profile import build_host_profile_api_payload, load_host_profile

    prof = load_host_profile()
    return {
        "schema_version": 1,
        "edition": edition,
        "core_workflow_mod_id": core_wf,
        "protected_client_mod_ids": list(protected),
        "minimal_host_mod_ids": list(minimal_ids),
        "generic_host_mod_ids": list(generic_ids),
        "minimal_pack_installed": minimal_ready,
        "generic_pack_installed": generic_ready,
        "shell_api_prefixes": shell_prefixes,
        "bridge_mods": bridges,
        "platform_shell_mode": shell_mode or edition in ("minimal", "generic"),
        "frontend_shell_hint": (
            "npm run build:minimal — OpenClaw shell (chat + mod-store); "
            "build:generic — full industry mod pack. ?full=1 for legacy ERP."
        ),
        "policy": "new_business_features_should_ship_as_mod_or_employee_pack",
        "host_profile": {
            "sku": prof.get("sku"),
            "workflow_delivery": prof.get("workflow_delivery"),
            "schema_version": prof.get("schema_version"),
        },
        "profile_validation_errors": build_host_profile_api_payload().get("validation_errors")
        or [],
    }
