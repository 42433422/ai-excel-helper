#!/usr/bin/env python3
"""Scaffold 6 single-employee workflow Mods + visualization-bridge from xcagi-core-workflow-employees."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODS = ROOT / "mods"
SRC = MODS / "xcagi-core-workflow-employees"
VIZ_SRC_VIEW = SRC / "frontend" / "views" / "WorkflowVisualizationView.vue"

SPECS = [
    {
        "mod_id": "xcagi-workflow-employee-label-print",
        "employee_id": "label_print",
        "stem": "label_print",
        "label": "标签打印 AI 员工",
        "summary": "星标微信 → 意图命中「标签/打印」→ 对话执行打印。执行业务链在宿主；本 Mod 提供 run/status。",
        "copy_employee": True,
    },
    {
        "mod_id": "xcagi-workflow-employee-shipment-mgmt",
        "employee_id": "shipment_mgmt",
        "stem": "shipment_mgmt",
        "label": "出货管理 AI 员工",
        "summary": "对话开单 → 确认执行 → 开始打印 → 出货记录审计建议。",
        "copy_employee": True,
    },
    {
        "mod_id": "xcagi-workflow-employee-receipt-confirm",
        "employee_id": "receipt_confirm",
        "stem": "receipt_confirm",
        "label": "收货确认 AI 员工",
        "summary": "星标意图 → 收货/对账类客户反馈写入工作流进程；对话跟进确认。",
        "copy_employee": True,
    },
    {
        "mod_id": "xcagi-workflow-employee-wechat-msg",
        "employee_id": "wechat_msg",
        "stem": "wechat_msg",
        "label": "微信消息处理 AI 员工",
        "summary": "星标自动刷新 → 新消息 → 意图 API 或本地规则 → 任务列表。",
        "copy_employee": True,
    },
    {
        "mod_id": "xcagi-workflow-employee-wechat-phone",
        "employee_id": "wechat_phone",
        "stem": "wechat_phone",
        "label": "微信电话对接业务员",
        "summary": "副窗启用 → phone-agent start/stop → Win32 来电监控 → ASR/TTS（与 /status 轮询同步）。",
        "copy_employee": False,
        "phone_agent_api_base": "/api/mod/sz-qsm-pro/phone-agent",
        "phone_agent_status_poll": True,
        "phone_channel": "wechat",
    },
    {
        "mod_id": "xcagi-workflow-employee-real-phone",
        "employee_id": "real_phone",
        "stem": "real_phone",
        "label": "真实电话业务员",
        "summary": "ADB 设备连通 → 来电检测/接听 → 语音转写与回复（与状态轮询同步）。",
        "copy_employee": False,
        "workflow_placeholder": True,
        "phone_channel": "adb",
    },
]

BLUEPRINT_TEMPLATE = '''# -*- coding: utf-8 -*-
"""Single workflow employee Mod HTTP surface."""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter

logger = logging.getLogger(__name__)

MOD_ID = "{mod_id}"
EMPLOYEE_ID = "{employee_id}"
EMPLOYEE_STEM = "{stem}"
EMPLOYEE_LABEL = "{label}"


def _resolve_mod_path(_mod_id: str) -> Optional[str]:
    here = os.path.dirname(os.path.abspath(__file__))
    guess = os.path.dirname(here)
    if os.path.isfile(os.path.join(guess, "manifest.json")):
        return guess
    return None


def _load_employee_module(mod_id: str, stem: str):
    try:
        from app.mod_sdk.mods_bus import import_mod_backend_py  # type: ignore
    except ImportError:
        return None
    mod_path = _resolve_mod_path(mod_id)
    if not mod_path:
        return None
    try:
        return import_mod_backend_py(mod_path, mod_id, f"employees/{{stem}}")
    except Exception:
        logger.exception("load employee module failed mod=%s stem=%s", mod_id, stem)
        return None


def _unified_err(msg: str, **meta: Any) -> Dict[str, Any]:
    return {{
        "success": False,
        "data": {{
            "ok": False,
            "summary": msg[:400],
            "items": [],
            "warnings": [],
            "error": msg[:1000],
            "meta": meta,
        }},
        "error": msg[:500],
    }}


async def _build_ctx(mod_id: str, employee_id: str) -> Dict[str, Any]:
    ctx: Dict[str, Any] = {{
        "mod_id": mod_id,
        "employee_id": employee_id,
        "logger": logging.getLogger(f"mod.{{mod_id}}.emp.{{employee_id}}"),
        "host_base_url": os.environ.get("XCAGI_HOST_BASE_URL", "http://127.0.0.1:5000"),
        "call_llm": None,
        "http_get": None,
        "http_post": None,
    }}
    try:
        from app.mod_sdk.mod_employee_llm import mod_employee_complete  # type: ignore

        async def _call_llm(messages, *, max_tokens=1024, temperature=0.2, response_format=None):
            return await mod_employee_complete(
                messages, max_tokens=max_tokens, temperature=temperature, response_format=response_format
            )

        ctx["call_llm"] = _call_llm
    except Exception as exc:
        logger.warning("mod_employee_complete unavailable: %s", exc)
    return ctx


async def _dispatch_run(mod_id: str, emp_id: str, stem: str, payload: Optional[Dict[str, Any]]):
    module = _load_employee_module(mod_id, stem)
    if module is None or not hasattr(module, "run"):
        return _unified_err(
            "employee module not loaded",
            employee_id=emp_id,
            stem=stem,
        )
    ctx = await _build_ctx(mod_id, emp_id)
    try:
        run_fn = getattr(module, "run")
        out = run_fn(payload or {{}}, ctx)
        if asyncio.iscoroutine(out):
            out = await out
        return {{"success": True, "data": out}}
    except Exception as exc:  # noqa: BLE001
        logger.exception("employee run failed emp=%s", emp_id)
        return _unified_err(f"employee run failed: {{exc!s}}"[:300], employee_id=emp_id)


def register_fastapi_routes(app, mod_id: str) -> None:
    router = APIRouter(prefix=f"/api/mod/{{mod_id}}", tags=[f"mod-{{mod_id}}"])

    @router.get("/status")
    def mod_status():
        return {{
            "success": True,
            "data": {{
                "mod_id": mod_id,
                "role": "workflow_employee_single",
                "employee_id": EMPLOYEE_ID,
                "label": EMPLOYEE_LABEL,
            }},
        }}

    @router.get("/employees")
    async def list_employees():
        return {{
            "success": True,
            "data": [{{"id": EMPLOYEE_ID, "label": EMPLOYEE_LABEL, "api_base_path": f"employees/{{EMPLOYEE_ID}}"}}],
        }}

    @router.post(f"/employees/{{EMPLOYEE_ID}}/run")
    async def emp_run(payload: Dict[str, Any] | None = None):
        return await _dispatch_run(mod_id, EMPLOYEE_ID, EMPLOYEE_STEM, payload)

    @router.get(f"/employees/{{EMPLOYEE_ID}}/status")
    async def emp_status():
        return await _dispatch_run(mod_id, EMPLOYEE_ID, EMPLOYEE_STEM, {{"action": "status"}})

    app.include_router(router)
    logger.info("workflow employee mod registered mod_id=%s employee=%s", mod_id, EMPLOYEE_ID)


def mod_init():
    logger.info("%s mod_init employee=%s", MOD_ID, EMPLOYEE_ID)
'''

PHONE_STUB = '''"""Workflow employee stub — phone / placeholder."""

from __future__ import annotations

from typing import Any, Dict, Optional


def _ok(summary: str = "", *, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {{"ok": True, "summary": summary[:4000], "items": [], "warnings": [], "error": "", "meta": dict(meta or {{}})}}


async def run(payload: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    act = str((payload or {{}}).get("action") or "status").strip() or "status"
    return _ok(
        "{summary}",
        meta={{"employee_id": "{employee_id}", "action": act, "mod_role": "furniture"}},
    )
'''

VIZ_BRIDGE_MANIFEST = {
    "id": "xcagi-workflow-visualization-bridge",
    "name": "工作流可视化（流程全景）",
    "version": "1.0.0",
    "author": "成都修茈科技有限公司",
    "description": "仅提供流程全景物理页路由；工作流员工由商店安装的 6 个独立 Mod 注入。",
    "primary": False,
    "dependencies": {"xcagi": ">=8.0.0"},
    "backend": {"entry": "blueprints", "init": "mod_init"},
    "frontend": {
        "routes": "frontend/routes",
        "menu": [
            {
                "id": "mod-workflow-visualization",
                "label": "流程可视化",
                "icon": "fa-project-diagram",
                "path": "/mod/xcagi-workflow-visualization-bridge/workflow-visualization",
            }
        ],
        "menu_overrides": [{"key": "workflow-visualization", "hidden": True}],
    },
    "hooks": {},
    "comms": {"exports": []},
    "config": {
        "workflow_pages_via_mod": True,
        "views_physical": True,
        "physical_views": ["WorkflowVisualizationView.vue"],
        "phase": "R",
    },
}

VIZ_BLUEPRINT = """# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)
MOD_ID = "xcagi-workflow-visualization-bridge"


def register_fastapi_routes(app, mod_id: str) -> None:
    router = APIRouter(prefix=f"/api/mod/{mod_id}", tags=[f"mod-{mod_id}"])

    @router.get("/status")
    def mod_status():
        return {"success": True, "data": {"mod_id": mod_id, "role": "workflow_visualization_bridge"}}

    app.include_router(router)
    logger.info("workflow visualization bridge registered %s", mod_id)


def mod_init():
    logger.info("%s mod_init", MOD_ID)
"""

ROUTES_JS = """/**
 * 流程可视化 — 物理视图（无 workflow_employees）
 */
import {{ modView }} from '@/router/modViews'

const MOD_ID = '{mod_id}'
const PREFIX = `/mod/${{MOD_ID}}`

const modRoutes = [
  {{
    path: `${{PREFIX}}/workflow-visualization`,
    name: 'mod-workflow-visualization',
    component: modView(MOD_ID, 'WorkflowVisualizationView.vue'),
    meta: {{ title: '流程可视化', mod: MOD_ID }},
  }},
]

const modMenu = [
  {{
    id: 'mod-workflow-visualization',
    label: '流程可视化',
    icon: 'fa-project-diagram',
    path: `${{PREFIX}}/workflow-visualization`,
  }},
]

export {{ modRoutes, modMenu }}
"""


def write_manifest(spec: dict) -> dict:
    emp: dict = {
        "id": spec["employee_id"],
        "label": spec["label"],
        "panel_title": f"工作流 · {spec['label']}",
        "panel_summary": spec["summary"],
        "api_base_path": f"employees/{spec['employee_id']}",
    }
    if spec.get("phone_agent_api_base"):
        emp["phone_agent_api_base"] = spec["phone_agent_api_base"]
    if spec.get("phone_agent_status_poll"):
        emp["phone_agent_status_poll"] = True
    if spec.get("workflow_placeholder"):
        emp["workflow_placeholder"] = True
    if spec.get("phone_channel"):
        emp["phone_channel"] = spec["phone_channel"]
    return {
        "id": spec["mod_id"],
        "name": spec["label"],
        "version": "1.0.0",
        "author": "成都修茈科技有限公司",
        "description": spec["summary"],
        "primary": False,
        "dependencies": {"xcagi": ">=8.0.0"},
        "backend": {"entry": "blueprints", "init": "mod_init"},
        "frontend": {"routes": None},
        "hooks": {},
        "comms": {"exports": []},
        "config": {
            "workflow_employee_single": True,
            "employee_id": spec["employee_id"],
            "store_collection": "workflow_employee",
        },
        "workflow_employees": [emp],
    }


def scaffold_employee_mod(spec: dict) -> None:
    mod_dir = MODS / spec["mod_id"]
    if mod_dir.exists():
        shutil.rmtree(mod_dir)
    (mod_dir / "backend" / "employees").mkdir(parents=True)
    (mod_dir / "backend" / "__init__.py").write_text("", encoding="utf-8")
    (mod_dir / "backend" / "employees" / "__init__.py").write_text("", encoding="utf-8")
    (mod_dir / "backend" / "blueprints.py").write_text(
        BLUEPRINT_TEMPLATE.format(**spec),
        encoding="utf-8",
    )
    (mod_dir / "manifest.json").write_text(
        json.dumps(write_manifest(spec), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (mod_dir / "README.md").write_text(
        f"# {spec['mod_id']}\n\n单员工工作流 Mod：`{spec['employee_id']}`。从商店安装后出现在副窗与流程全景。\n",
        encoding="utf-8",
    )
    dest = mod_dir / "backend" / "employees" / f"{spec['stem']}.py"
    if spec.get("copy_employee"):
        shutil.copy2(SRC / "backend" / "employees" / f"{spec['stem']}.py", dest)
    else:
        dest.write_text(
            PHONE_STUB.format(
                summary=spec["summary"].replace('"', '\\"'),
                employee_id=spec["employee_id"],
            ),
            encoding="utf-8",
        )


def scaffold_viz_bridge() -> None:
    mod_id = "xcagi-workflow-visualization-bridge"
    mod_dir = MODS / mod_id
    if mod_dir.exists():
        shutil.rmtree(mod_dir)
    (mod_dir / "backend").mkdir(parents=True)
    (mod_dir / "frontend" / "views").mkdir(parents=True)
    (mod_dir / "backend" / "__init__.py").write_text("", encoding="utf-8")
    (mod_dir / "backend" / "blueprints.py").write_text(VIZ_BLUEPRINT, encoding="utf-8")
    (mod_dir / "manifest.json").write_text(
        json.dumps(VIZ_BRIDGE_MANIFEST, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    shutil.copy2(VIZ_SRC_VIEW, mod_dir / "frontend" / "views" / "WorkflowVisualizationView.vue")
    (mod_dir / "frontend" / "routes.js").write_text(
        ROUTES_JS.format(mod_id=mod_id), encoding="utf-8"
    )
    (mod_dir / "README.md").write_text(
        "# xcagi-workflow-visualization-bridge\n\n流程全景物理页；不含 workflow_employees。\n",
        encoding="utf-8",
    )


def deprecate_legacy_core_mod() -> None:
    readme = SRC / "README.md"
    text = readme.read_text(encoding="utf-8")
    if "已迁移" not in text:
        readme.write_text(
            "# 已迁移\n\n本包已拆分为 6 个独立商店 Mod（`xcagi-workflow-employee-*`）+ `xcagi-workflow-visualization-bridge`。\n"
            "请勿在新环境安装本包；开关键与员工 id 保持不变。\n\n---\n\n" + text,
            encoding="utf-8",
        )
    manifest_path = SRC / "manifest.json"
    mf = json.loads(manifest_path.read_text(encoding="utf-8"))
    mf["workflow_employees"] = []
    mf["description"] = (
        "【已废弃】请安装 6 个 xcagi-workflow-employee-* Mod 与 visualization-bridge。"
    )
    manifest_path.write_text(json.dumps(mf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    for spec in SPECS:
        scaffold_employee_mod(spec)
        print("scaffolded", spec["mod_id"])
    scaffold_viz_bridge()
    print("scaffolded xcagi-workflow-visualization-bridge")
    deprecate_legacy_core_mod()
    print("deprecated legacy core-workflow manifest")


if __name__ == "__main__":
    main()
