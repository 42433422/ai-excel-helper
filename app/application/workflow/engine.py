from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Set

import httpx

from app.services import get_ai_conversation_service

from .types import NodeExecutionResult, PlanGraph, WorkflowRunResult, WorkflowNode

logger = logging.getLogger(__name__)

_sync_http_client: Optional[httpx.Client] = None


def _get_sync_http_client() -> httpx.Client:
    global _sync_http_client
    if _sync_http_client is None:
        _sync_http_client = httpx.Client(
            timeout=httpx.Timeout(20.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )
    return _sync_http_client


class WorkflowEngine:
    def __init__(self, tool_dispatcher) -> None:
        self._dispatch = tool_dispatcher

    def run(
        self,
        plan: PlanGraph,
        runtime_context: Dict[str, Any] | None = None,
        max_retries: int = 1,
        agentic_loop: bool = False,
        tool_registry: Dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> WorkflowRunResult:
        if agentic_loop and tool_registry:
            return self._run_agentic_loop(plan, runtime_context, max_retries, tool_registry, user_id)
        return self._run_batch(plan, runtime_context, max_retries)

    def _run_batch(
        self,
        plan: PlanGraph,
        runtime_context: Dict[str, Any] | None = None,
        max_retries: int = 1,
    ) -> WorkflowRunResult:
        runtime_context = dict(runtime_context or {})
        node_results: List[NodeExecutionResult] = []
        executed: Set[str] = set()

        pending: Dict[str, WorkflowNode] = {node.node_id: node for node in plan.nodes}
        stalled_rounds = 0

        while pending:
            progressed = False
            for node_id in list(pending.keys()):
                node = pending[node_id]
                if any(dep not in executed for dep in node.depends_on):
                    continue

                result = self._run_node(node, runtime_context, max_retries=max_retries)
                node_results.append(result)
                executed.add(node_id)
                pending.pop(node_id, None)
                progressed = True

                runtime_context.setdefault("node_outputs", {})
                runtime_context["node_outputs"][node_id] = result.output
                if not result.success:
                    return WorkflowRunResult(
                        plan_id=plan.plan_id,
                        success=False,
                        node_results=node_results,
                        final_context=runtime_context,
                        message=f"节点 {node_id} 执行失败: {result.error}",
                    )

            if not progressed:
                stalled_rounds += 1
                if stalled_rounds > 1:
                    unresolved = ",".join(pending.keys())
                    return WorkflowRunResult(
                        plan_id=plan.plan_id,
                        success=False,
                        node_results=node_results,
                        final_context=runtime_context,
                        message=f"工作流依赖无法继续解析: {unresolved}",
                    )

        return WorkflowRunResult(
            plan_id=plan.plan_id,
            success=True,
            node_results=node_results,
            final_context=runtime_context,
            message="工作流执行完成",
        )

    def _run_agentic_loop(
        self,
        plan: PlanGraph,
        runtime_context: Dict[str, Any] | None,
        max_retries: int,
        tool_registry: Dict[str, Any],
        user_id: str | None,
    ) -> WorkflowRunResult:
        """
        Agentic Loop：LLM 每步决定下一步做什么 → 执行 → 喂结果 → 再决定
        循环直到 LLM 说 done 或达到 max_steps。
        """
        runtime_context = dict(runtime_context or {})
        all_node_results: List[NodeExecutionResult] = []
        agent_history: List[Dict[str, Any]] = []
        max_steps = 10
        step = 0

        user_message = str(runtime_context.get("message") or "").strip()

        while step < max_steps:
            step += 1

            decision = self._llm_decide_next_step(
                user_message=user_message,
                tool_registry=tool_registry,
                runtime_context=runtime_context,
                agent_history=agent_history,
                user_id=user_id,
            )

            if decision is None:
                break

            action = decision.get("action", "")
            tool_id = decision.get("tool_id", "")
            params = decision.get("params") or {}
            reasoning = str(decision.get("reasoning", "")).strip()

            logger.info(
                "AgenticLoop step=%d action=%s.%s reasoning=%s",
                step, tool_id, action, reasoning[:100]
            )

            agent_history.append({
                "step": step,
                "role": "assistant",
                "tool_id": tool_id,
                "action": action,
                "params": params,
                "reasoning": reasoning,
            })

            if action == "done":
                break

            node_result = self._run_single_tool(
                tool_id=tool_id,
                action=action,
                params=params,
                runtime_context=runtime_context,
                max_retries=max_retries,
            )
            all_node_results.append(node_result)

            runtime_context.setdefault("node_outputs", {})
            runtime_context["node_outputs"][f"agent_step_{step}"] = node_result.output

            if not node_result.success:
                agent_history.append({
                    "step": step,
                    "role": "system",
                    "content": f"工具执行失败: {node_result.error}",
                })
            else:
                output_preview = self._summarize_output(node_result.output)
                agent_history.append({
                    "step": step,
                    "role": "system",
                    "content": f"结果: {output_preview}",
                })

        if step >= max_steps:
            logger.warning("AgenticLoop 达到最大步数限制 %d", max_steps)

        return WorkflowRunResult(
            plan_id=plan.plan_id,
            success=True,
            node_results=all_node_results,
            final_context=runtime_context,
            message=f"AgenticLoop 完成（{step} 步）",
        )

    def _llm_decide_next_step(
        self,
        user_message: str,
        tool_registry: Dict[str, Any],
        runtime_context: Dict[str, Any],
        agent_history: List[Dict[str, Any]],
        user_id: str | None,
    ) -> Optional[Dict[str, Any]]:
        """
        询问 LLM：下一步做什么（单步决策）。
        返回 {"action": "done"} 表示结束，或 {"tool_id": "...", "action": "...", "params": {...}, "reasoning": "..."}
        """
        ai_service = get_ai_conversation_service()
        api_key = getattr(ai_service, "api_key", "") or ""
        if not api_key:
            logger.warning("AgenticLoop 缺少 API_KEY，跳过")
            return None

        tool_specs = []
        for tid, spec in tool_registry.items():
            if not isinstance(spec, dict):
                continue
            actions = spec.get("actions") or {}
            action_list = []
            for aname, ameta in actions.items():
                if not isinstance(ameta, dict):
                    continue
                action_list.append({
                    "action": aname,
                    "risk": ameta.get("risk", "low"),
                    "idempotent": bool(ameta.get("idempotent", False)),
                    "required_params": ameta.get("required_params", []),
                })
            tool_specs.append({
                "tool_id": tid,
                "description": spec.get("description", ""),
                "actions": action_list,
            })

        history_lines = []
        for h in agent_history[-8:]:
            role = h.get("role", "")
            if role == "done":
                history_lines.append(f"Assistant: 已完成任务")
            elif role == "assistant":
                history_lines.append(
                    f"Assistant: 决定执行 {h.get('tool_id')}.{h.get('action')} "
                    f"(reasoning: {h.get('reasoning', '')[:80]})"
                )
            else:
                history_lines.append(f"System: {h.get('content', '')[:200]}")

        excel_analysis = runtime_context.get("excel_analysis")
        excel_info = ""
        if isinstance(excel_analysis, dict):
            fp = excel_analysis.get("file_path", "")
            excel_info = f"\n当前 Excel 文件: {fp}"

        prompt = {
            "task": "作为 Agent，决定下一步动作。",
            "rules": [
                "如果任务已完成，返回 {\"action\": \"done\"}。",
                "如果需要执行工具，返回 {\"tool_id\": \"...\", \"action\": \"...\", \"params\": {...}, \"reasoning\": \"...\"}。",
                "params 必须填写所有 required_params（不能留空）。",
                "优先使用低风险、幂等工具。",
                "只决定下一步，不要一次决定多步。",
            ],
            "user_message": user_message,
            "excel_context": excel_info,
            "recent_history": "\n".join(history_lines) if history_lines else "(首步决策)",
            "tool_registry": tool_specs,
            "output_schema": {
                "action": "done | execute",
                "tool_id": "string (当 action=execute 时)",
                "action_name": "string (当 action=execute 时)",
                "params": "{} (当 action=execute 时)",
                "reasoning": "string",
            },
        }

        messages = [
            {"role": "system", "content": "你是工作流 Agent，只输出 JSON。"},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ]

        try:
            api_url = getattr(ai_service, "api_url", "") or "https://api.deepseek.com/v1/chat/completions"
            model = getattr(ai_service, "model", "") or "deepseek-chat"

            response = _get_sync_http_client().post(
                api_url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.1,
                    "max_tokens": 600,
                },
            )
            if response.status_code >= 400:
                logger.warning("AgenticLoop LLM 调用失败: status=%d", response.status_code)
                return None

            raw = (
                (response.json().get("choices") or [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            if not raw:
                return None
            parsed = json.loads(raw)

            action = str(parsed.get("action") or "").strip().lower()
            if action == "done":
                return {"action": "done"}

            tool_id = str(parsed.get("tool_id") or "").strip()
            action_name = str(parsed.get("action_name") or parsed.get("action") or "").strip()
            params = parsed.get("params") if isinstance(parsed.get("params"), dict) else {}
            reasoning = str(parsed.get("reasoning") or "").strip()

            if not tool_id or not action_name:
                return None

            return {
                "action": "execute",
                "tool_id": tool_id,
                "action_name": action_name,
                "params": params,
                "reasoning": reasoning,
            }

        except Exception as e:
            logger.warning("AgenticLoop LLM 决策失败: %s", e, exc_info=True)
            return None

    @staticmethod
    def _summarize_output(output: Dict[str, Any]) -> str:
        if not isinstance(output, dict):
            return str(output)[:200]
        if output.get("success") is True:
            msg = str(output.get("message") or output.get("answer") or "").strip()
            if msg:
                return msg[:200]
            data = output.get("data")
            if data is not None:
                if isinstance(data, list):
                    return f"返回 {len(data)} 条数据"
                return str(data)[:200]
        err = str(output.get("error") or output.get("message") or "").strip()
        if err:
            return f"错误: {err[:100]}"
        return str(output)[:200]

    def _run_single_tool(
        self,
        tool_id: str,
        action: str,
        params: Dict[str, Any],
        runtime_context: Dict[str, Any],
        max_retries: int,
    ) -> NodeExecutionResult:
        merged_params = dict(params or {})
        merged_params["_runtime_context"] = runtime_context
        retries = 0
        last_error = ""

        while retries <= max_retries:
            try:
                output = self._dispatch(tool_id=tool_id, action=action, params=merged_params)
                if output.get("success", False):
                    return NodeExecutionResult(
                        node_id=f"agent_{tool_id}_{action}",
                        success=True,
                        tool_id=tool_id,
                        action=action,
                        output=output,
                        retries=retries,
                    )
                last_error = str(output.get("message") or output.get("error") or "unknown error")
            except Exception as err:
                last_error = str(err)
                logger.warning("AgenticLoop 工具执行失败 %s.%s: %s", tool_id, action, err, exc_info=True)
            retries += 1

        return NodeExecutionResult(
            node_id=f"agent_{tool_id}_{action}",
            success=False,
            tool_id=tool_id,
            action=action,
            error=last_error,
            retries=max(0, retries - 1),
        )

    @staticmethod
    def _has_non_empty_param(params: Dict[str, Any], keys: tuple[str, ...]) -> bool:
        for k in keys:
            v = params.get(k)
            if v is not None and str(v).strip():
                return True
        return False

    def _merge_runtime_fallback_params(
        self, node: WorkflowNode, merged_params: Dict[str, Any], runtime_context: Dict[str, Any]
    ) -> None:
        user_msg = str(runtime_context.get("message") or "").strip()
        if not user_msg:
            return
        if node.tool_id == "products" and node.action == "query":
            if not self._has_non_empty_param(
                merged_params,
                ("keyword", "model_number", "product_name", "name", "unit_name"),
            ):
                merged_params["keyword"] = user_msg
                logger.info(
                    "工作流 products.query 参数为空，已注入用户原话作为 keyword（前 80 字）: %s",
                    user_msg[:80],
                )
        elif node.tool_id == "customers" and node.action == "query":
            if not self._has_non_empty_param(
                merged_params,
                ("keyword", "unit_name", "customer_name", "name"),
            ):
                merged_params["keyword"] = user_msg
                logger.info(
                    "工作流 customers.query 参数为空，已注入用户原话作为 keyword: %s",
                    user_msg[:80],
                )

    def _run_node(
        self,
        node: WorkflowNode,
        runtime_context: Dict[str, Any],
        max_retries: int = 1,
    ) -> NodeExecutionResult:
        retries = 0
        last_error = ""
        while retries <= max_retries:
            try:
                merged_params = dict(node.params or {})
                merged_params["_runtime_context"] = runtime_context
                self._merge_runtime_fallback_params(node, merged_params, runtime_context)
                output = self._dispatch(
                    tool_id=node.tool_id,
                    action=node.action,
                    params=merged_params,
                )
                if output.get("success", False):
                    return NodeExecutionResult(
                        node_id=node.node_id,
                        success=True,
                        tool_id=node.tool_id,
                        action=node.action,
                        output=output,
                        retries=retries,
                    )
                last_error = str(output.get("message") or output.get("error") or "unknown error")
            except Exception as err:
                last_error = str(err)
                logger.warning("执行节点失败 node=%s err=%s", node.node_id, err, exc_info=True)
            retries += 1

        return NodeExecutionResult(
            node_id=node.node_id,
            success=False,
            tool_id=node.tool_id,
            action=node.action,
            error=last_error,
            retries=max(0, retries - 1),
        )
