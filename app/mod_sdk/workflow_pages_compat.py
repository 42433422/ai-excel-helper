# -*- coding: utf-8 -*-
"""里程碑 R：核心工作流 Mod 业务页（流程可视化）。"""

from __future__ import annotations

from typing import Any

CORE_WORKFLOW_MOD_ID = "xcagi-core-workflow-employees"
MOD_PAGE_PREFIX = f"/mod/{CORE_WORKFLOW_MOD_ID}"

HOST_PAGES = ["/workflow-visualization"]


def list_workflow_pages_registry() -> dict[str, Any]:
    return {
        "ok": True,
        "mod_id": CORE_WORKFLOW_MOD_ID,
        "mod_page_prefix": MOD_PAGE_PREFIX,
        "host_pages": HOST_PAGES,
        "page_count": len(HOST_PAGES),
        "pages_via_mod": True,
        "component_source": "mod.frontend.views (R physical)",
        "views_physical": True,
        "phase": "R",
    }


__all__ = ["HOST_PAGES", "MOD_PAGE_PREFIX", "CORE_WORKFLOW_MOD_ID", "list_workflow_pages_registry"]
