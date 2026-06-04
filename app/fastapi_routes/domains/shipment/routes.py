"""Migrated from legacy_workflow.py (v10)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from app.fastapi_routes.domains.misc.helpers import _dispatch_tool_for_approval

logger = logging.getLogger(__name__)

router = APIRouter(tags=["legacy-workflow"], deprecated=True)


@router.get("/api/ai/approval/pending")
def ai_approval_pending():
    from app.application.workflow import get_approval_service

    approval_service = get_approval_service()
    all_pending = []
    for req in approval_service._pending_requests.values():
        all_pending.append(
            {
                "request_id": req.request_id,
                "plan_id": req.plan_id,
                "node_id": req.node_id,
                "tool_id": req.tool_id,
                "action": req.action,
                "status": req.status.value,
                "created_at": req.created_at.isoformat() if req.created_at else None,
            }
        )
    return {"success": True, "data": {"pending_approvals": all_pending}}


@router.get("/api/ai/config/approval")
def ai_config_approval_get():
    from resources.config.approval_config import get_approval_config

    c = get_approval_config()
    return {
        "success": True,
        "enabled": c.enabled,
        "rules": c.rules,
        "attendance_policy": getattr(c, "attendance_policy", None) or {},
    }


@router.post("/api/ai/config/approval")
def ai_config_approval_post(body: dict = Body(default_factory=dict)):
    try:
        payload = body or {}
        enabled = payload.get("enabled", True)
        rules = payload.get("rules", [])
        from resources.config.approval_config import get_approval_config, reload_approval_config

        config = get_approval_config()
        config.enabled = enabled
        config.rules = rules
        if "attendance_policy" in payload and isinstance(payload["attendance_policy"], dict):
            from resources.config.approval_config import normalize_attendance_policy

            config.attendance_policy = normalize_attendance_policy(payload["attendance_policy"])
        config.save()
        reload_approval_config()
        from app.application.workflow import reload_approval_service

        reload_approval_service()
        return {"success": True, "message": "保存成功"}
    except Exception as e:
        logger.exception("save approval config: %s", e)
        return JSONResponse({"success": False, "message": f"保存失败：{str(e)}"}, status_code=500)


@router.post("/api/ai/approval/request")
def ai_approval_request(body: dict = Body(default_factory=dict)):
    try:
        payload = body or {}
        plan_id = payload.get("plan_id") or ""
        node_id = payload.get("node_id") or ""
        tool_id = payload.get("tool_id") or ""
        action = payload.get("action") or ""
        params = payload.get("params") or {}
        if not plan_id or not node_id:
            return JSONResponse(
                {"success": False, "message": "缺少 plan_id 或 node_id"}, status_code=400
            )
        from app.application.workflow import WorkflowNode, get_approval_service

        approval_service = get_approval_service()
        node = WorkflowNode(node_id=node_id, tool_id=tool_id, action=action, params=params)
        approval_req = approval_service.create_approval_request(plan_id=plan_id, node=node)
        return {
            "success": True,
            "message": "审批请求已创建",
            "data": {
                "request_id": approval_req.request_id,
                "plan_id": approval_req.plan_id,
                "node_id": approval_req.node_id,
                "tool_id": approval_req.tool_id,
                "action": approval_req.action,
                "status": approval_req.status.value,
                "created_at": (
                    approval_req.created_at.isoformat() if approval_req.created_at else None
                ),
            },
        }
    except Exception as e:
        logger.exception("approval request: %s", e)
        return JSONResponse(
            {"success": False, "message": f"创建审批请求失败：{str(e)}"}, status_code=500
        )


@router.post("/api/ai/approval/approve")
def ai_approval_approve(body: dict = Body(default_factory=dict)):
    try:
        payload = body or {}
        request_id = payload.get("request_id") or ""
        plan_id = payload.get("plan_id") or ""
        comment = payload.get("comment") or ""
        from app.application.workflow import WorkflowEngine, get_approval_service

        approval_service = get_approval_service()
        actual_request_id = None
        if request_id:
            success = approval_service.approve(request_id, comment)
            actual_request_id = request_id
        elif plan_id:
            pending_req = approval_service.get_pending_request_by_plan(plan_id)
            if not pending_req:
                return JSONResponse(
                    {"success": False, "message": "没有待审批的请求"}, status_code=404
                )
            success = approval_service.approve(pending_req.request_id, comment)
            actual_request_id = pending_req.request_id
        else:
            return JSONResponse(
                {"success": False, "message": "缺少 request_id 或 plan_id"}, status_code=400
            )

        if not success:
            return JSONResponse({"success": False, "message": "审批失败"}, status_code=400)

        workflow_data = (
            approval_service.get_pending_workflow(actual_request_id) if actual_request_id else None
        )
        run_result_data = None
        if workflow_data:
            plan_obj = workflow_data.get("plan")
            runtime_ctx = workflow_data.get("runtime_context", {})
            if plan_obj:
                engine = WorkflowEngine(tool_dispatcher=_dispatch_tool_for_approval)
                run_result = engine.run(plan=plan_obj, runtime_context=runtime_ctx, max_retries=1)
                run_result_data = {
                    "plan_id": plan_obj.plan_id,
                    "intent": plan_obj.intent,
                    "nodes_executed": len(run_result.node_results),
                    "nodes_total": len(plan_obj.nodes),
                    "has_errors": any(bool(r.error) for r in run_result.node_results),
                    "results_summary": [
                        {
                            "node_id": r.node_id,
                            "success": r.success,
                            "output": str(r.output)[:200] if r.output else None,
                        }
                        for r in run_result.node_results[:5]
                    ],
                }
                approval_service.remove_pending_workflow(actual_request_id)

        response_data: dict[str, Any] = {
            "status": "approved",
            "workflow_executed": workflow_data is not None,
        }
        if run_result_data:
            response_data["workflow_result"] = run_result_data
        return {
            "success": True,
            "message": "审批已通过" + ("，工作流已执行" if workflow_data else ""),
            "data": response_data,
        }
    except Exception as e:
        logger.exception("approval approve: %s", e)
        return JSONResponse({"success": False, "message": f"审批失败：{str(e)}"}, status_code=500)


@router.post("/api/ai/approval/reject")
def ai_approval_reject(body: dict = Body(default_factory=dict)):
    try:
        payload = body or {}
        request_id = payload.get("request_id") or ""
        plan_id = payload.get("plan_id") or ""
        comment = payload.get("comment") or ""
        from app.application.workflow import get_approval_service

        approval_service = get_approval_service()
        if request_id:
            success = approval_service.reject(request_id, comment)
        elif plan_id:
            pending_req = approval_service.get_pending_request_by_plan(plan_id)
            if not pending_req:
                return JSONResponse(
                    {"success": False, "message": "没有待审批的请求"}, status_code=404
                )
            success = approval_service.reject(pending_req.request_id, comment)
        else:
            return JSONResponse(
                {"success": False, "message": "缺少 request_id 或 plan_id"}, status_code=400
            )
        if success:
            return {"success": True, "message": "审批已拒绝", "data": {"status": "rejected"}}
        return JSONResponse({"success": False, "message": "审批拒绝失败"}, status_code=400)
    except Exception as e:
        logger.exception("approval reject: %s", e)
        return JSONResponse(
            {"success": False, "message": f"审批拒绝失败：{str(e)}"}, status_code=500
        )
