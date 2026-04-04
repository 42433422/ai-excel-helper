from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .types import PlanGraph


@dataclass
class RiskDecision:
    requires_confirmation: bool
    reason: str
    blocking_nodes: List[str]


class HybridRiskGate:
    """
    混合门控：
    - low 自动执行
    - medium/high 默认确认
    - 可通过 context 显式放行（同会话记忆）
    """

    def evaluate(self, plan: PlanGraph, context: Dict[str, object]) -> RiskDecision:
        auto_approve = bool(context.get("workflow_auto_approve_high_risk", False))
        if auto_approve:
            return RiskDecision(
                requires_confirmation=False,
                reason="用户会话已开启高风险自动执行",
                blocking_nodes=[],
            )

        blocking_nodes: List[str] = []
        for node in plan.nodes:
            if node.risk in ("medium", "high"):
                blocking_nodes.append(node.node_id)

        if blocking_nodes:
            return RiskDecision(
                requires_confirmation=True,
                reason="计划包含中高风险写操作",
                blocking_nodes=blocking_nodes,
            )

        return RiskDecision(
            requires_confirmation=False,
            reason="计划仅包含低风险读操作",
            blocking_nodes=[],
        )
