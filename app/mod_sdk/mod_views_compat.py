# -*- coding: utf-8 -*-
"""里程碑 O / O+：Mod 包内物理 Vue 视图注册表。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

PHYSICAL_VIEW_MODS: dict[str, list[str]] = {
    "xcagi-lan-license-bridge": ["LanGateView.vue"],
    "xcagi-customer-service-bridge": [
        "EnterpriseCustomerServiceView.vue",
        "InternalCustomerServiceView.vue",
    ],
    "xcagi-approval-bridge": [
        "ApprovalHubView.vue",
        "ApprovalWorkspaceView.vue",
        "ApprovalFlowManagementView.vue",
        "ApprovalRulesView.vue",
    ],
    "xcagi-planner-bridge": [
        "ChatView.vue",
        "AIEcosystemView.vue",
        "BrainView.vue",
        "ChatDebugView.vue",
    ],
    "xcagi-model-payment-bridge": [
        "ModelPaymentView.vue",
        "KittenFinanceView.vue",
    ],
    "xcagi-office-employee-pack-bridge": [
        "ToolsView.vue",
        "OtherToolsView.vue",
    ],
    "xcagi-core-workflow-employees": [
        "WorkflowVisualizationView.vue",
    ],
    "xcagi-erp-domain-bridge": [
        "ProductsView.vue",
        "CustomersView.vue",
        "OrdersView.vue",
        "CreateOrderView.vue",
        "ShipmentRecordsView.vue",
        "WechatContactsView.vue",
        "MaterialsView.vue",
        "TraditionalModeView.vue",
        "BusinessDockingView.vue",
        "DataSourcesView.vue",
        "PrintView.vue",
        "PrinterListView.vue",
        "TemplatePreviewView.vue",
        "LabelEditorView.vue",
        "PurchaseView.vue",
        "InventoryView.vue",
    ],
}


def _truthy_env(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _resolve_mod_dir(mod_id: str) -> Path | None:
    try:
        from app.infrastructure.mods.mod_manager import get_mod_manager

        meta = get_mod_manager().get_mod(mod_id)
        if meta and meta.mod_path and (Path(meta.mod_path) / "manifest.json").is_file():
            return Path(meta.mod_path)
    except Exception:
        pass
    trial = Path(__file__).resolve().parents[2] / "mods" / mod_id
    return trial if (trial / "manifest.json").is_file() else None


def is_mod_views_physical_enabled(mod_id: str) -> bool:
    if _truthy_env("XCAGI_DISABLE_MOD_PHYSICAL_VIEWS"):
        return False
    if _truthy_env("XCAGI_MOD_PHYSICAL_VIEWS"):
        return mod_id in PHYSICAL_VIEW_MODS
    mod_dir = _resolve_mod_dir(mod_id)
    if not mod_dir:
        return False
    try:
        cfg = (
            json.loads((mod_dir / "manifest.json").read_text(encoding="utf-8")).get("config") or {}
        )
        return isinstance(cfg, dict) and cfg.get("views_physical") is True
    except Exception:
        return False


def list_mod_physical_views_registry() -> dict[str, Any]:
    mods: list[dict[str, Any]] = []
    for mod_id, files in PHYSICAL_VIEW_MODS.items():
        mod_dir = _resolve_mod_dir(mod_id)
        physical_paths = []
        if mod_dir:
            for vf in files:
                p = mod_dir / "frontend" / "views" / vf
                physical_paths.append(
                    {
                        "view_file": vf,
                        "exists_on_disk": p.is_file(),
                        "mod_relative": f"frontend/views/{vf}",
                    }
                )
        mods.append(
            {
                "mod_id": mod_id,
                "views_physical": is_mod_views_physical_enabled(mod_id),
                "view_files": files,
                "physical_paths": physical_paths,
                "component_source": "mod.frontend.views",
                "host_shim_pattern": "frontend/src/views/<View>.vue re-exports mod physical file",
            }
        )
    enabled = [m["mod_id"] for m in mods if m.get("views_physical")]
    return {
        "ok": True,
        "phase": "O+",
        "pilot_mod_count": len(PHYSICAL_VIEW_MODS),
        "enabled_mod_ids": enabled,
        "mods": mods,
        "note": "宿主 views 薄 shim + Mod routes 优先 modView；业务 Mod 页 O+ 已全量物理迁出。",
    }


__all__ = [
    "PHYSICAL_VIEW_MODS",
    "is_mod_views_physical_enabled",
    "list_mod_physical_views_registry",
]
