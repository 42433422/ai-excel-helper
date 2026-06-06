# -*- coding: utf-8 -*-
"""xcagi-core-workflow-employees：Mod（房子）+ 四名员工（家具）静态与路由冒烟。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MOD_ID = "xcagi-core-workflow-employees"
EMPLOYEE_IDS = ("label_print", "shipment_mgmt", "receipt_confirm", "wechat_msg")

MOD_DIRS = [
    REPO_ROOT / "mods" / MOD_ID,
    REPO_ROOT / "XCAGI" / "mods" / MOD_ID,
]


@pytest.fixture(params=MOD_DIRS, ids=["mods", "XCAGI/mods"])
def mod_dir(request: pytest.FixtureRequest) -> Path:
    p: Path = request.param
    if not p.is_dir():
        pytest.skip(f"missing {p}")
    return p


def test_manifest_one_mod_four_employees(mod_dir: Path) -> None:
    manifest_path = mod_dir / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["id"] == MOD_ID
    assert data.get("artifact", "mod") == "mod" or "artifact" not in data
    wf = data.get("workflow_employees") or []
    ids = {e["id"] for e in wf}
    assert ids == set(EMPLOYEE_IDS)
    for e in wf:
        assert e.get("api_base_path", "").startswith("employees/")


def test_employee_modules_exist(mod_dir: Path) -> None:
    for emp in EMPLOYEE_IDS:
        py = mod_dir / "backend" / "employees" / f"{emp}.py"
        assert py.is_file(), py
        text = py.read_text(encoding="utf-8")
        assert "async def run" in text


def test_blueprints_registers_employee_routes(mod_dir: Path) -> None:
    bp = mod_dir / "backend" / "blueprints.py"
    text = bp.read_text(encoding="utf-8")
    assert "register_fastapi_routes" in text
    for emp in EMPLOYEE_IDS:
        assert emp in text
        assert "emp_run" in text or f"/employees/{emp}" in text


_EMPLOYEE_ACTIONS = {
    "label_print": ("status", "signal_ack"),
    "shipment_mgmt": ("status", "audit_summary"),
    "receipt_confirm": ("status", "feedback_ack"),
    "wechat_msg": ("status", "enqueue_ack"),
}


@pytest.mark.parametrize("emp", EMPLOYEE_IDS)
def test_employee_run_callable(mod_dir: Path, emp: str) -> None:
    """不启动 HTTP 服务，直接加载员工模块并调用 run。"""
    sys.path.insert(0, str(REPO_ROOT))
    try:
        from app.infrastructure.mods.mod_manager import import_mod_backend_py

        mod = import_mod_backend_py(str(mod_dir), MOD_ID, f"employees/{emp}")
        assert hasattr(mod, "run")
        import asyncio

        out = asyncio.run(mod.run({"action": "status"}, {}))
        assert out.get("ok") is True
        assert out.get("meta", {}).get("employee_id") == emp or emp in str(out.get("summary", ""))
    finally:
        if str(REPO_ROOT) in sys.path:
            sys.path.remove(str(REPO_ROOT))


@pytest.mark.parametrize("emp", EMPLOYEE_IDS)
@pytest.mark.parametrize("action", ["status", "extended"])
def test_employee_run_extended_actions(mod_dir: Path, emp: str, action: str) -> None:
    """Phase 2：signal_ack / audit_summary / feedback_ack / enqueue_ack 等 action 可调用。"""
    acts = _EMPLOYEE_ACTIONS[emp]
    if action == "status":
        payload = {"action": "status"}
    else:
        payload = {
            "action": acts[1],
            "line": "test-line",
            "detail": "test-detail",
            "contact": "test-contact",
            "purchaseUnit": "unit-a",
            "headline": "audit-headline",
        }
    sys.path.insert(0, str(REPO_ROOT))
    try:
        from app.infrastructure.mods.mod_manager import import_mod_backend_py

        mod = import_mod_backend_py(str(mod_dir), MOD_ID, f"employees/{emp}")
        import asyncio

        out = asyncio.run(mod.run(payload, {}))
        assert out.get("ok") is True
        assert out.get("meta", {}).get("employee_id") == emp
    finally:
        if str(REPO_ROOT) in sys.path:
            sys.path.remove(str(REPO_ROOT))
