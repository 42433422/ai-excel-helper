from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.application.workflow.types import (
    ApprovalRequest,
    ApprovalRule,
    ApprovalStatus,
    ApprovalTrigger,
    PlanGraph,
    WorkflowNode,
)
from resources.config.approval_config import ApprovalConfig, get_approval_config, reload_approval_config

logger = logging.getLogger(__name__)


class ApprovalService:
    def __init__(self):
        self._config: ApprovalConfig = get_approval_config()
        self._pending_requests: Dict[str, ApprovalRequest] = {}
        self._pending_workflows: Dict[str, Dict[str, Any]] = {}

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

    def _evaluate_conditions(self, conditions: Dict[str, Any], node: WorkflowNode) -> bool:
        if not conditions:
            return False

        for key, expected in conditions.items():
            actual = node.params.get(key)
            if actual is None:
                return False
            if isinstance(expected, dict):
                op = expected.get("op", "eq")
                value = expected.get("value")
                if op == "gt" and not (actual > value):
                    return False
                elif op == "gte" and not (actual >= value):
                    return False
                elif op == "lt" and not (actual < value):
                    return False
                elif op == "lte" and not (actual <= value):
                    return False
                elif op == "neq" and actual == value:
                    return False
                elif op == "eq" and actual != value:
                    return False
                elif op == "contains" and value not in str(actual):
                    return False
            elif actual != expected:
                return False
        return True

    def get_approval_required_nodes(self, plan: PlanGraph) -> List[WorkflowNode]:
        if not self._config.enabled:
            return []

        required_nodes: List[WorkflowNode] = []
        for node in plan.nodes:
            if self.check_node_requires_approval(node):
                required_nodes.append(node)
        return required_nodes

    def create_approval_request(
        self,
        plan_id: str,
        node: WorkflowNode,
        runtime_context: Optional[Dict[str, Any]] = None,
        plan: Optional["PlanGraph"] = None,
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
        return request

    def get_pending_workflow(self, request_id: str) -> Optional[Dict[str, Any]]:
        return self._pending_workflows.get(request_id)

    def remove_pending_workflow(self, request_id: str) -> Optional[Dict[str, Any]]:
        return self._pending_workflows.pop(request_id, None)

    def get_pending_request(self, request_id: str) -> Optional[ApprovalRequest]:
        return self._pending_requests.get(request_id)

    def get_pending_request_by_plan(self, plan_id: str) -> Optional[ApprovalRequest]:
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

    def get_pending_approval_info(self, plan_id: str) -> Optional[Dict[str, Any]]:
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


_approval_service: Optional[ApprovalService] = None


def get_approval_service() -> ApprovalService:
    global _approval_service
    if _approval_service is None:
        _approval_service = ApprovalService()
    return _approval_service


def reload_approval_service() -> ApprovalService:
    global _approval_service
    if _approval_service is not None:
        _approval_service.reload_config()
    return get_approval_service()
