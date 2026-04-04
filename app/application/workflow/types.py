from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

RiskLevel = Literal["low", "medium", "high"]


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ApprovalTrigger(str, Enum):
    ALWAYS = "always"
    NEVER = "never"
    CONDITIONAL = "conditional"


@dataclass
class ApprovalRule:
    tool_id: str
    action: str
    trigger: ApprovalTrigger = ApprovalTrigger.NEVER
    conditions: Dict[str, Any] = field(default_factory=dict)
    description: str = ""


@dataclass
class ApprovalRequest:
    request_id: str
    plan_id: str
    node_id: str
    tool_id: str
    action: str
    params: Dict[str, Any]
    status: ApprovalStatus
    created_at: datetime
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    approver_comment: str = ""


@dataclass
class WorkflowNode:
    node_id: str
    tool_id: str
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    risk: RiskLevel = "low"
    idempotent: bool = False
    description: str = ""
    depends_on: List[str] = field(default_factory=list)


@dataclass
class PlanGraph:
    plan_id: str
    intent: str
    todo_steps: List[str] = field(default_factory=list)
    nodes: List[WorkflowNode] = field(default_factory=list)
    risk_level: RiskLevel = "low"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NodeExecutionResult:
    node_id: str
    success: bool
    tool_id: str
    action: str
    output: Dict[str, Any] = field(default_factory=dict)
    error: str = ""
    retries: int = 0


@dataclass
class WorkflowRunResult:
    plan_id: str
    success: bool
    node_results: List[NodeExecutionResult] = field(default_factory=list)
    final_context: Dict[str, Any] = field(default_factory=dict)
    message: str = ""


def validate_plan_graph(plan: PlanGraph) -> Optional[str]:
    if not plan.plan_id:
        return "plan_id 不能为空"
    if not plan.intent:
        return "intent 不能为空"
    if not plan.nodes:
        return "nodes 不能为空"

    node_ids = {node.node_id for node in plan.nodes}
    if len(node_ids) != len(plan.nodes):
        return "node_id 不能重复"

    for node in plan.nodes:
        if not node.node_id:
            return "存在空 node_id"
        if not node.tool_id:
            return f"节点 {node.node_id} 缺少 tool_id"
        if not node.action:
            return f"节点 {node.node_id} 缺少 action"
        for dep in node.depends_on:
            if dep not in node_ids:
                return f"节点 {node.node_id} 依赖不存在: {dep}"
            if dep == node.node_id:
                return f"节点 {node.node_id} 不能依赖自身"

    return None
