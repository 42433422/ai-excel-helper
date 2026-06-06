# -*- coding: utf-8 -*-
"""可交付状态聚合：供验收、前端首启引导与技术支持诊断。"""

from __future__ import annotations

import os
from typing import Any

from app.mod_sdk.edition_policy import bundled_mods_dir, resolve_edition
from app.mod_sdk.platform_shell import (
    GENERIC_HOST_MOD_IDS,
    MINIMAL_HOST_MOD_IDS,
    build_platform_shell_payload,
)
from app.mod_sdk.product_skus import (
    ENTERPRISE_HOST_MOD_IDS,
    PERSONAL_HOST_MOD_IDS,
    bundled_mod_ids_for_sku,
    resolve_product_sku,
)


def _installed_mod_ids() -> list[str]:
    try:
        from app.infrastructure.mods.mod_manager import get_mod_manager

        mm = get_mod_manager()
        ids = [m.id for m in (mm.list_loaded_mods() or []) if getattr(m, "id", None)]
        if ids:
            return ids
        return [m.id for m in mm.scan_mods() if getattr(m, "id", None)]
    except Exception:
        return []


def build_deliverable_status(installed_mod_ids: list[str] | None = None) -> dict[str, Any]:
    from app.mod_sdk.host_foundation import (
        host_foundation_bridges_ready,
        host_foundation_employee_present,
        try_materialize_host_foundation_if_needed,
    )

    materialize_hint: dict[str, Any] | None = None
    # 仅真实探测时自动展开；单测传入 installed_mod_ids 或 PYTEST 时不改磁盘。
    in_pytest = bool(os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("PYTEST_VERSION"))
    if (
        not in_pytest
        and installed_mod_ids is None
        and host_foundation_employee_present()
        and not host_foundation_bridges_ready()
    ):
        materialize_hint = try_materialize_host_foundation_if_needed()
        if materialize_hint and materialize_hint.get("ready"):
            installed_mod_ids = None

    installed = list(installed_mod_ids or _installed_mod_ids())
    installed_set = set(installed)
    shell = build_platform_shell_payload(installed)
    edition = shell.get("edition") or resolve_edition()
    product_sku = resolve_product_sku()
    minimal_ready = bool(shell.get("minimal_pack_installed"))
    generic_ready = bool(shell.get("generic_pack_installed"))

    sku_expected = bundled_mod_ids_for_sku()
    if sku_expected:
        expected = list(sku_expected)
    elif product_sku == "personal":
        expected = list(PERSONAL_HOST_MOD_IDS)
    elif product_sku == "enterprise":
        expected = list(ENTERPRISE_HOST_MOD_IDS)
    else:
        expected = list(MINIMAL_HOST_MOD_IDS if edition == "minimal" else GENERIC_HOST_MOD_IDS)
        if edition == "full":
            expected = []

    missing = [mid for mid in expected if mid not in installed_set]
    blockers: list[dict[str, Any]] = []
    pack_ready = not missing

    from app.mod_sdk.host_profile import get_profile_validation_errors

    profile_errors = get_profile_validation_errors(product_sku)
    for err in profile_errors:
        blockers.append(
            {
                "code": "PROFILE_SCHEMA_MISMATCH",
                "message": err,
            }
        )
        pack_ready = False

    if product_sku == "enterprise":
        from app.mod_sdk.erp_domain_compat import ERP_DOMAIN_BRIDGE_MOD_ID

        if ERP_DOMAIN_BRIDGE_MOD_ID not in installed_set:
            blockers.append(
                {
                    "code": "ENTERPRISE_ERP_MISSING",
                    "message": "企业版 ERP 基准模块未就绪",
                    "missing_mod_ids": [ERP_DOMAIN_BRIDGE_MOD_ID],
                }
            )
            pack_ready = False
    elif product_sku == "personal":
        if missing:
            blockers.append(
                {
                    "code": "SKU_PACK_INCOMPLETE",
                    "message": f"{product_sku} 版内置 Mod 包未装齐",
                    "missing_mod_ids": missing,
                }
            )
            pack_ready = False
    elif edition == "generic" and not generic_ready:
        from app.mod_sdk.host_foundation import host_foundation_employee_present

        msg = "通用行业 Mod 包未装齐，请打开扩展市场或执行 bootstrap-edition-pack"
        if host_foundation_employee_present():
            msg = (
                "已安装「宿主基础能力·预装员工」（一个员工包 Mod）；"
                "请点击「一键装齐」将内部 bridge 展开到本机 mods 目录（对话/审批/客服等路由依赖这些目录）。"
            )
        blockers.append(
            {
                "code": "GENERIC_PACK_INCOMPLETE",
                "message": msg,
                "missing_mod_ids": missing,
            }
        )
        pack_ready = False
    elif edition == "minimal" and not minimal_ready:
        blockers.append(
            {
                "code": "MINIMAL_PACK_INCOMPLETE",
                "message": "空壳宿主 Mod 包未装齐",
                "missing_mod_ids": missing,
            }
        )
        pack_ready = False

    bundle = bundled_mods_dir()
    bundle_missing = []
    if bundle and expected:
        for mid in expected:
            if not (bundle / mid).is_dir():
                bundle_missing.append(mid)

    mods_routes = True
    try:
        from app.fastapi_app import get_fastapi_app

        app = get_fastapi_app()
        mods_routes = bool(getattr(app.state, "mods_routes_loaded", False))
    except Exception:
        mods_routes = False

    if not mods_routes and expected:
        blockers.append(
            {
                "code": "MOD_ROUTES_NOT_MOUNTED",
                "message": "Mod HTTP 路由未挂载，请重启应用",
            }
        )

    if product_sku:
        edition_ready = pack_ready
    else:
        edition_ready = (
            edition == "full"
            or (edition == "generic" and generic_ready)
            or (edition == "minimal" and minimal_ready)
        )
    deliverable = edition_ready and not any(
        b["code"] in ("MOD_ROUTES_NOT_MOUNTED",) for b in blockers
    )

    product_flow_step = "daily_use"
    if product_sku == "personal":
        product_flow_step = "industry_mod" if deliverable else "host_pack"
    elif edition == "full" or product_sku == "enterprise":
        product_flow_step = "daily_use" if deliverable else "host_pack"
    elif not edition_ready:
        product_flow_step = "host_pack"
    elif deliverable:
        product_flow_step = "industry_mod"

    host_employee = host_foundation_employee_present()
    host_bridges = host_foundation_bridges_ready()

    return {
        "schema_version": 1,
        "deliverable": deliverable,
        "host_foundation_employee_installed": host_employee,
        "host_foundation_bridges_ready": host_bridges,
        "host_foundation_materialize": materialize_hint,
        "product_flow": {
            "recommended_step": product_flow_step,
            "steps": [
                {"id": "install", "label": "安装宿主"},
                {"id": "first_launch", "label": "首次启动"},
                {"id": "host_pack", "label": "宿主包就绪"},
                {"id": "industry_mod", "label": "行业 MOD（可选）"},
                {"id": "daily_use", "label": "日常使用"},
            ],
            "ui_route": "/onboarding",
        },
        "edition": edition,
        "product_sku": product_sku,
        "edition_ready": edition_ready,
        "minimal_pack_installed": minimal_ready,
        "generic_pack_installed": generic_ready,
        "installed_mod_count": len(installed_set),
        "expected_mod_ids": expected,
        "missing_mod_ids": missing,
        "bundled_mods_dir": str(bundle) if bundle else None,
        "bundled_mods_missing": bundle_missing,
        "mods_routes_loaded": mods_routes,
        "platform_shell_mode": shell.get("platform_shell_mode"),
        "blockers": blockers,
        "next_actions": _next_actions(edition, blockers, deliverable),
        "desktop_mode": (os.environ.get("XCAGI_DESKTOP_MODE") or "").strip().lower()
        in {"1", "true", "yes"},
    }


def _next_actions(
    edition: str,
    blockers: list[dict[str, Any]],
    deliverable: bool,
) -> list[str]:
    if deliverable:
        return ["open_chat", "install_industry_mod_from_store"]
    actions = []
    if any(b.get("code") == "GENERIC_PACK_INCOMPLETE" for b in blockers):
        actions.append("POST /api/mod-store/bootstrap-edition-pack?edition=generic")
        actions.append("open_mod_store")
    if any(b.get("code") == "MINIMAL_PACK_INCOMPLETE" for b in blockers):
        actions.append("POST /api/mod-store/bootstrap-edition-pack?edition=minimal")
        actions.append("open_mod_store")
    if edition == "generic":
        actions.append("verify_bundled_mods_in_installer")
    return actions


__all__ = ["build_deliverable_status"]
