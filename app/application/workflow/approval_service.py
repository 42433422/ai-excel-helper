from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from app.application.workflow.types import (
    ApprovalRequest,
    ApprovalStatus,
    PlanGraph,
    WorkflowNode,
)
from resources.config.approval_config import (
    ApprovalConfig,
    get_approval_config,
    reload_approval_config,
)

logger = logging.getLogger(__name__)


class ApprovalService:
    def __init__(self):
        self._config: ApprovalConfig = get_approval_config()
        self._pending_requests: dict[str, ApprovalRequest] = {}
        self._pending_workflows: dict[str, dict[str, Any]] = {}

    def reload_config(self) -> None:
        self._config = reload_approval_config()

    def is_approval_enabled(self) -> bool:
        return self._config.enabled

    def check_node_requires_approval(self, node: WorkflowNode) -> bool:
        if not self._config.enabled:
            return False

        for rule in self._config.rules:
            if rule.get("tool_id") == node.tool_id and rule.get("action") == node.action:
                trigger = rule.get("trigger", "never")
                if trigger == "always":
                    return True
                elif trigger == "conditional":
                    return self._evaluate_conditions(rule.get("conditions", {}), node)
        return False

    def _evaluate_conditions(self, conditions: dict[str, Any], node: WorkflowNode) -> bool:
        if not conditions:
            return False

        for key, expected in conditions.items():
            actual = node.params.get(key)
            if actual is None:
                return False
            if isinstance(expected, dict):
                op = expected.get("op", "eq")
                value = expected.get("value")
                if (
                    op == "gt"
                    and not (actual > value)
                    or op == "gte"
                    and not (actual >= value)
                    or op == "lt"
                    and not (actual < value)
                    or op == "lte"
                    and not (actual <= value)
                    or op == "neq"
                    and actual == value
                    or op == "eq"
                    and actual != value
                    or op == "contains"
                    and value not in str(actual)
                ):
                    return False
            elif actual != expected:
                return False
        return True

    def get_approval_required_nodes(self, plan: PlanGraph) -> list[WorkflowNode]:
        if not self._config.enabled:
            return []

        required_nodes: list[WorkflowNode] = []
        for node in plan.nodes:
            if self.check_node_requires_approval(node):
                required_nodes.append(node)
        return required_nodes

    def create_approval_request(
        self,
        plan_id: str,
        node: WorkflowNode,
        runtime_context: dict[str, Any] | None = None,
        plan: PlanGraph | None = None,
    ) -> ApprovalRequest:
        request_id = uuid.uuid4().hex
        request = ApprovalRequest(
            request_id=request_id,
            plan_id=plan_id,
            node_id=node.node_id,
            tool_id=node.tool_id,
            action=node.action,
            params=node.params.copy() if node.params else {},
            status=ApprovalStatus.PENDING,
            created_at=datetime.now(),
        )
        self._pending_requests[request_id] = request
        if plan is not None:
            self._pending_workflows[request_id] = {
                "plan": plan,
                "runtime_context": runtime_context or {},
                "plan_id": plan_id,
            }
        logger.info(f"创建审批请求: {request_id} for {node.tool_id}.{node.action}")

        # 同时持久化到 DB（防止重启丢失，且与 /api/approval/requests 工作台共享可见性）
        self._persist_request_to_db(request)
        return request

    def _persist_request_to_db(self, request: ApprovalRequest) -> None:
        """将内存审批请求写入 DB approval_requests 表（幂等）。"""
        import json as _json

        try:
            from sqlalchemy import text

            from app.db.session import get_db

            with get_db() as db:
                existing = db.execute(
                    text("SELECT id FROM approval_requests WHERE request_no = :rno LIMIT 1"),
                    {"rno": request.request_id},
                ).fetchone()
                if not existing:
                    db.execute(
                        text(
                            "INSERT INTO approval_requests "
                            "(request_no, flow_id, business_type, title, description, applicant_id, status, created_at) "
                            "VALUES (:rno, NULL, 'workflow_tool', :title, :desc, NULL, 'pending', :created)"
                        ),
                        {
                            "rno": request.request_id,
                            "title": f"{request.tool_id}.{request.action}",
                            "desc": _json.dumps(
                                request.params or {}, ensure_ascii=False, default=str
                            )[:500],
                            "created": (request.created_at or datetime.now()).isoformat(),
                        },
                    )
        except Exception as e:
            logger.debug("AI 审批持久化到 DB 失败（非致命）: %s", e)

    def get_pending_workflow(self, request_id: str) -> dict[str, Any] | None:
        return self._pending_workflows.get(request_id)

    def remove_pending_workflow(self, request_id: str) -> dict[str, Any] | None:
        return self._pending_workflows.pop(request_id, None)

    def get_pending_request(self, request_id: str) -> ApprovalRequest | None:
        return self._pending_requests.get(request_id)

    def get_pending_request_by_plan(self, plan_id: str) -> ApprovalRequest | None:
        for req in self._pending_requests.values():
            if req.plan_id == plan_id and req.status == ApprovalStatus.PENDING:
                return req
        return None

    def approve(self, request_id: str, comment: str = "") -> bool:
        request = self._pending_requests.get(request_id)
        if not request:
            logger.warning(f"审批请求不存在: {request_id}")
            return False
        if request.status != ApprovalStatus.PENDING:
            logger.warning(f"审批请求状态不是pending: {request_id}, status={request.status}")
            return False

        request.status = ApprovalStatus.APPROVED
        request.approved_at = datetime.now()
        request.approver_comment = comment
        logger.info(f"审批通过: {request_id}")
        return True

    def reject(self, request_id: str, comment: str = "") -> bool:
        request = self._pending_requests.get(request_id)
        if not request:
            logger.warning(f"审批请求不存在: {request_id}")
            return False
        if request.status != ApprovalStatus.PENDING:
            logger.warning(f"审批请求状态不是pending: {request_id}, status={request.status}")
            return False

        request.status = ApprovalStatus.REJECTED
        request.rejected_at = datetime.now()
        request.approver_comment = comment
        logger.info(f"审批拒绝: {request_id}")
        return True

    def cancel(self, request_id: str) -> bool:
        request = self._pending_requests.get(request_id)
        if not request:
            return False
        request.status = ApprovalStatus.CANCELLED
        logger.info(f"审批取消: {request_id}")
        return True

    def is_approved(self, plan_id: str) -> bool:
        request = self.get_pending_request_by_plan(plan_id)
        return request is not None and request.status == ApprovalStatus.APPROVED

    def is_rejected(self, plan_id: str) -> bool:
        request = self.get_pending_request_by_plan(plan_id)
        return request is not None and request.status == ApprovalStatus.REJECTED

    def get_pending_approval_info(self, plan_id: str) -> dict[str, Any] | None:
        request = self.get_pending_request_by_plan(plan_id)
        if not request:
            return None
        return {
            "request_id": request.request_id,
            "plan_id": request.plan_id,
            "node_id": request.node_id,
            "tool_id": request.tool_id,
            "action": request.action,
            "params": request.params,
            "status": request.status.value,
            "created_at": request.created_at.isoformat() if request.created_at else None,
        }


from app.neuro_bus.neuro_application_instrumentation import instrument_approval_service_class

instrument_approval_service_class(ApprovalService)

_approval_service: ApprovalService | None = None


def get_approval_service() -> ApprovalService:
    global _approval_service
    if _approval_service is None:
        _approval_service = ApprovalService()
    return _approval_service


def process_approval_timeouts() -> dict[str, Any]:
    """
    扫描 DB 中超时的审批请求并自动处理（超时动作：auto_reject / auto_approve / escalate）。

    供定时任务或 /api/approval/process-timeouts 端点调用。
    """
    results: list[dict] = []
    try:
        from datetime import datetime as _dt

        from sqlalchemy import and_

        from app.db.models.approval import ApprovalFlow, ApprovalRequest, ApprovalStatus
        from app.db.session import get_db

        now = _dt.utcnow()
        with get_db() as db:
            expired = (
                db.query(ApprovalRequest)
                .filter(
                    and_(
                        ApprovalRequest.status == ApprovalStatus.PENDING,
                        ApprovalRequest.expired_at != None,  # noqa: E711
                        ApprovalRequest.expired_at < now,
                    )
                )
                .all()
            )
            for req in expired:
                flow = db.query(ApprovalFlow).filter(ApprovalFlow.id == req.flow_id).first()
                timeout_action = "auto_reject"
                if flow:
                    node = next(
                        (n for n in (flow.nodes or []) if n.id == req.current_node_id), None
                    )
                    if node:
                        timeout_action = getattr(node, "timeout_action", None) or "auto_reject"

                if timeout_action == "auto_approve":
                    req.status = ApprovalStatus.APPROVED
                    note = "超时自动通过"
                else:
                    req.status = ApprovalStatus.REJECTED
                    note = "超时自动拒绝"

                results.append({"request_id": req.id, "action": timeout_action, "note": note})
                logger.info("审批超时处理: request_id=%s, action=%s", req.id, timeout_action)

            if results:
                db.commit()
    except Exception as e:
        logger.error("审批超时处理失败: %s", e, exc_info=True)
        return {"success": False, "error": str(e), "processed": 0}

    return {"success": True, "processed": len(results), "results": results}


def reload_approval_service() -> ApprovalService:
    global _approval_service
    if _approval_service is not None:
        _approval_service.reload_config()
    return get_approval_service()
