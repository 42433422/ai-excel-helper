# -*- coding: utf-8 -*-
"""解耦进度聚合（供 GET /api/platform-shell/decoupling-progress）。"""

from __future__ import annotations

from typing import Any


def _safe(fn, default: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        out = fn()
        return out if isinstance(out, dict) else (default or {})
    except Exception:
        return default or {}


def build_decoupling_progress_payload(installed_mod_ids: list[str] | None = None) -> dict[str, Any]:
    installed = set(installed_mod_ids or [])

    milestones = [
        {"id": "A", "label": "前端壳化", "status": "done"},
        {"id": "B-F4", "label": "Planner 工具 Mod", "status": "done"},
        {"id": "C-H", "label": "ERP 领域 API/Handler", "status": "done"},
        {"id": "I", "label": "通用发行版", "status": "done"},
        {"id": "E-J", "label": "横切 API 门面", "status": "done"},
        {"id": "K-K+", "label": "业务页 Mod 化", "status": "done"},
        {"id": "L-L+", "label": "Repository 可插拔", "status": "done"},
        {"id": "M-M+", "label": "NeuroBus 门面", "status": "done"},
        {"id": "N", "label": "NeuroBus handler 注册外置", "status": "done"},
        {"id": "3b", "label": "办公 employee_pack 目录", "status": "done"},
        {"id": "K-CS", "label": "客服业务页 Mod 化", "status": "done"},
        {"id": "O", "label": "Vue 视图物理迁入 Mod（试点）", "status": "done"},
        {"id": "views物理迁出", "label": "Vue 视图全量迁入 Mod（ERP 等）", "status": "done"},
        {"id": "P", "label": "主对话物理迁入 planner-bridge", "status": "done"},
        {"id": "L++", "label": "ERP Repository 统一 Mod 工厂", "status": "done"},
        {"id": "neuro总线迁出", "label": "NeuroBus 订阅/处理器外置", "status": "done"},
        {"id": "Q", "label": "minimal 空壳发行（edition + build:minimal）", "status": "done"},
        {"id": "R", "label": "宿主路由扫尾 + Mod 物理视图 import 守卫", "status": "done"},
        {"id": "S", "label": "NeuroBus/Planner 运行时委托层", "status": "done"},
        {"id": "T", "label": "ADCDFG-A 锚定与计划文档", "status": "done"},
        {"id": "U", "label": "ADCDFG-B/F 默认 generic 发行构建", "status": "done"},
        {"id": "V", "label": "ADCDFG-C/E edition 策略与 legacy 路由裁剪", "status": "done"},
        {"id": "W", "label": "ADCDFG-D bootstrap-edition-pack + 桌面 Mod 种子", "status": "done"},
        {"id": "X", "label": "ADCDFG-G 全局限流与验收脚本", "status": "done"},
    ]

    bridges = {
        "erp": _safe(
            lambda: __import__(
                "app.mod_sdk.erp_domain_compat", fromlist=["list_erp_domains_registry"]
            ).list_erp_domains_registry()
        ),
        "approval": _safe(
            lambda: __import__(
                "app.mod_sdk.approval_compat", fromlist=["list_approval_facade_registry"]
            ).list_approval_facade_registry()
        ),
        "lan": _safe(
            lambda: __import__(
                "app.mod_sdk.lan_compat", fromlist=["list_lan_facade_registry"]
            ).list_lan_facade_registry()
        ),
        "model_payment": _safe(
            lambda: __import__(
                "app.mod_sdk.model_payment_compat", fromlist=["list_model_payment_facade_registry"]
            ).list_model_payment_facade_registry()
        ),
        "neuro_bus": _safe(
            lambda: __import__(
                "app.mod_sdk.neuro_bus_compat", fromlist=["list_neuro_bus_facade_registry"]
            ).list_neuro_bus_facade_registry()
        ),
        "neuro_bus_handlers": _safe(
            lambda: __import__(
                "app.mod_sdk.neuro_bus_handler_registry",
                fromlist=["list_neuro_bus_handler_registry"],
            ).list_neuro_bus_handler_registry()
        ),
        "employee_pack": _safe(
            lambda: __import__(
                "app.mod_sdk.employee_pack_compat", fromlist=["list_employee_pack_facade_registry"]
            ).list_employee_pack_facade_registry()
        ),
    }

    pages = {
        "erp": _safe(
            lambda: __import__(
                "app.mod_sdk.erp_pages_compat", fromlist=["list_erp_pages_registry"]
            ).list_erp_pages_registry()
        ),
        "approval": _safe(
            lambda: __import__(
                "app.mod_sdk.approval_pages_compat", fromlist=["list_approval_pages_registry"]
            ).list_approval_pages_registry()
        ),
        "planner": _safe(
            lambda: __import__(
                "app.mod_sdk.planner_pages_compat", fromlist=["list_planner_pages_registry"]
            ).list_planner_pages_registry()
        ),
        "customer_service": _safe(
            lambda: __import__(
                "app.mod_sdk.customer_service_pages_compat",
                fromlist=["list_customer_service_pages_registry"],
            ).list_customer_service_pages_registry()
        ),
        "office_employee": _safe(
            lambda: __import__(
                "app.mod_sdk.office_employee_pages_compat",
                fromlist=["list_office_employee_pages_registry"],
            ).list_office_employee_pages_registry()
        ),
        "workflow": _safe(
            lambda: __import__(
                "app.mod_sdk.workflow_pages_compat",
                fromlist=["list_workflow_pages_registry"],
            ).list_workflow_pages_registry()
        ),
    }

    repositories = _safe(
        lambda: __import__(
            "app.mod_sdk.erp_repository_registry", fromlist=["list_erp_repository_registry"]
        ).list_erp_repository_registry()
    )

    physical_views = _safe(
        lambda: __import__(
            "app.mod_sdk.mod_views_compat",
            fromlist=["list_mod_physical_views_registry"],
        ).list_mod_physical_views_registry()
    )

    from app.mod_sdk.platform_shell import (
        GENERIC_HOST_MOD_IDS,
        MINIMAL_HOST_MOD_IDS,
        build_platform_shell_payload,
    )

    generic_mods = list(GENERIC_HOST_MOD_IDS)
    minimal_mods = list(MINIMAL_HOST_MOD_IDS)
    generic_ready = all(mid in installed for mid in generic_mods)
    minimal_ready = all(mid in installed for mid in minimal_mods)
    shell_payload = _safe(lambda: build_platform_shell_payload(list(installed)), {})
    edition = shell_payload.get("edition") or "full"

    done_count = sum(1 for m in milestones if m["status"] == "done")
    total = len(milestones)
    percent = int(round(100 * done_count / total)) if total else 0

    return {
        "schema_version": 1,
        "milestones": milestones,
        "milestones_done": done_count,
        "milestones_total": total,
        "progress_percent": percent,
        "architecture_boundary_percent": 100,
        "implementation_extract_percent": 98,
        "openclaw_edition_percent": 100,
        "composite_percent": 100,
        "adcdfg_complete": True,
        "edition": edition,
        "editions": ["minimal", "generic", "full"],
        "minimal_pack_installed": minimal_ready,
        "minimal_mod_ids": minimal_mods,
        "generic_pack_installed": generic_ready,
        "generic_pack_mod_ids": generic_mods,
        "host_core_routes": [
            "chat",
            "mod-store",
            "settings",
            "workflow-employee-space",
            "desktop-runtime",
        ],
        "installed_mod_count": len(installed),
        "bridges": bridges,
        "pages": pages,
        "repositories": repositories,
        "physical_views": physical_views,
        "note": "ADCDFG 完成：默认 generic 壳发行、bootstrap-edition-pack、非 full 跳过 legacy_gaps；Phase 2D legacy 按域拆分与 DB 全迁为后续专项。",
    }


__all__ = ["build_decoupling_progress_payload"]
