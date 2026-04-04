from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, List, Optional

import httpx

from app.services import get_ai_conversation_service

from .types import PlanGraph, WorkflowNode, validate_plan_graph

logger = logging.getLogger(__name__)

# 同步规划 LLM 复用 Client，减轻短时多次 DeepSeek 连接失败
_planner_http_client: Optional[httpx.Client] = None


def _get_planner_http_client() -> httpx.Client:
    global _planner_http_client
    if _planner_http_client is None:
        _planner_http_client = httpx.Client(
            timeout=httpx.Timeout(20.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )
    return _planner_http_client


def _filter_tool_registry_for_profile(
    tool_registry: Dict[str, Any],
    profile: str,
) -> Dict[str, Any]:
    """
    - normal：剔除 pro_only 工具与动作（普通界面走槽位/共享工具）。
    - pro_default：剔除 normal_only 工具与动作（全专业链路不暴露纯普通槽位工具）。
    """
    filtered: Dict[str, Any] = {}
    for tool_id, spec in tool_registry.items():
        if not isinstance(spec, dict):
            continue
        tool_av = str(spec.get("availability") or "shared").strip().lower()
        if profile == "normal" and tool_av == "pro_only":
            continue
        if profile == "pro_default" and tool_av == "normal_only":
            continue
        actions = spec.get("actions") or {}
        if not isinstance(actions, dict):
            continue
        kept_actions: Dict[str, Any] = {}
        for aname, ameta in actions.items():
            if not isinstance(ameta, dict):
                continue
            av = str(ameta.get("availability") or "shared").strip().lower()
            if profile == "normal" and av == "pro_only":
                continue
            if profile == "pro_default" and av == "normal_only":
                continue
            kept_actions[aname] = ameta
        if not kept_actions:
            continue
        new_spec = dict(spec)
        new_spec["actions"] = kept_actions
        filtered[tool_id] = new_spec
    return filtered


class LLMWorkflowPlanner:
    def __init__(self) -> None:
        self._ai_service = get_ai_conversation_service()

    def plan(
        self,
        user_id: str,
        message: str,
        tool_registry: Dict[str, Any],
        context: Dict[str, Any] | None = None,
    ) -> PlanGraph:
        context = dict(context or {})
        plan_id = uuid.uuid4().hex

        from app.application.normal_chat_dispatch import resolve_tool_execution_profile

        profile = resolve_tool_execution_profile(context)
        registry_for_plan = _filter_tool_registry_for_profile(tool_registry, profile)

        # 专业模式 ReAct/CoT 前：拉取用户记忆 RAG 命中摘要，注入到 context（只放摘要文本）。
        # 目的：让规划器在“选择工具/补全关键 params”时更贴近用户习惯，但避免把全量历史注入 prompt。
        try:
            from app.application import get_user_memory_rag_app_service

            rag = get_user_memory_rag_app_service()
            rag_res = rag.query(user_id=user_id, query_text=message, top_k=3)
            hits = (rag_res or {}).get("hits") if isinstance(rag_res, dict) else None
            if isinstance(hits, list) and hits:
                summary = rag.format_for_prompt(user_id=user_id, query_text=message, hits=hits, max_hits=4)
                context["user_memory_rag"] = {"summary": summary}
        except Exception as e:
            logger.warning("用户记忆 RAG 注入失败（不阻断主流程）: %s", e)

        planned = self._plan_with_react_multiagent(
            plan_id=plan_id,
            user_id=user_id,
            message=message,
            tool_registry=registry_for_plan,
            context=context,
        )
        if planned is not None:
            err = validate_plan_graph(planned)
            if err is None:
                return planned
            logger.warning("ReAct/CoT 计划校验失败，回退规则规划: %s", err)

        return self._fallback_plan(plan_id, message, registry_for_plan)

    def _plan_with_react_multiagent(
        self,
        plan_id: str,
        user_id: str,
        message: str,
        tool_registry: Dict[str, Any],
        context: Dict[str, Any],
    ) -> PlanGraph | None:
        """
        多步 ReAct/CoT 风格规划（简化实现）：
        1) 先用 LLM 生成候选 PlanGraph（DecomposerAgent）。
        2) 基于候选 PlanGraph 抽取低风险只读节点做 ToolProbe（真实工具调用）。
        3) 将探测结果注入 prompt 再次规划得到最终 PlanGraph（PlanComposerAgent）。
        4) validate_plan_graph；失败则降级 fallback（CriticAgent）。
        """

        # 0) 用现有 Planner 生成候选计划
        candidate = self._plan_with_llm(
            plan_id=plan_id,
            user_id=user_id,
            message=message,
            tool_registry=tool_registry,
            context=context,
        )
        if candidate is None:
            return None

        # 1) 抽取 probe：只探测 low-risk + idempotent 的节点
        runtime_context_for_probe = dict(context or {})
        runtime_context_for_probe["message"] = str(message or "")
        probe_requests: List[Dict[str, Any]] = []
        for node in (candidate.nodes or []):
            tid = str(node.tool_id or "").strip()
            act = str(node.action or "").strip()
            if not tid or not act:
                continue
            tool_spec = tool_registry.get(tid)
            if not isinstance(tool_spec, dict):
                continue
            actions = tool_spec.get("actions") or {}
            if not isinstance(actions, dict):
                continue
            meta = actions.get(act)
            if not isinstance(meta, dict):
                continue

            risk = str(meta.get("risk") or "").strip().lower()
            idempotent = bool(meta.get("idempotent", False))
            if risk != "low" or not idempotent:
                continue

            # 只对“查询类/列举类”探测，避免意义不明的 view/info 探测
            if act not in ("query", "exists", "list", "view", "refresh_contact_cache", "refresh_messages_cache"):
                continue

            probe_requests.append(
                {
                    "tool_id": tid,
                    "action": act,
                    "params": node.params or {},
                }
            )

        # 最多 3 个 probe，避免 prompt 过长/探测过多
        probe_requests = probe_requests[:3]

        # 2) 执行 ToolProbe（并注入检索词：对 products/customers.query 补 keyword）
        probe_outputs: List[Dict[str, Any]] = []

        task_agent = None
        try:
            from app.services.task_agent import TaskAgent

            task_agent = TaskAgent()
        except Exception:
            task_agent = None

        for pr in probe_requests:
            try:
                tool_id = str(pr.get("tool_id") or "").strip()
                action = str(pr.get("action") or "").strip()
                params = pr.get("params") if isinstance(pr.get("params"), dict) else {}

                # 安全约束校验：仅允许 low-risk & idempotent 的工具探测，并严格校验 required_params 非空
                tool_spec = tool_registry.get(tool_id) or {}
                actions = tool_spec.get("actions") or {}
                action_meta = actions.get(action) if isinstance(actions, dict) else None
                if not isinstance(action_meta, dict):
                    continue
                risk = str(action_meta.get("risk") or "").strip().lower()
                idempotent = bool(action_meta.get("idempotent", False))
                if risk != "low" or not idempotent:
                    continue

                required_params = action_meta.get("required_params") or []
                if not isinstance(required_params, list):
                    required_params = []
                missing_required = []
                for k in required_params:
                    if k not in (params or {}) or params.get(k) is None or str(params.get(k)).strip() == "":
                        missing_required.append(k)
                if missing_required:
                    continue

                # query 补检索词（避免探测空 keyword 导致无意义全量扫描）
                if tool_id == "products" and action == "query":
                    # node.params 优先；否则从 message 中尽量抽取
                    if not (params.get("keyword") or params.get("model_number") or params.get("unit_name")):
                        try:
                            from app.application.normal_chat_dispatch import route_normal_mode_message

                            rr = route_normal_mode_message(message)
                            if rr.get("intent") == "product_query":
                                slots = rr.get("slots") or {}
                                params.update(
                                    {
                                        "keyword": slots.get("keyword") or params.get("keyword") or "",
                                        "model_number": slots.get("model_number") or params.get("model_number") or "",
                                        "unit_name": slots.get("unit_name") or params.get("unit_name") or "",
                                    }
                                )
                        except Exception:
                            # fallback: 使用原消息作为 keyword
                            if not params.get("keyword"):
                                params["keyword"] = str(message or "").strip()[:80]

                if tool_id == "customers" and action == "query":
                    if not (params.get("keyword") or params.get("customer_name")) and task_agent is not None:
                        try:
                            cust_slots = task_agent._extract_customer_query_slots(str(message or ""))
                            if isinstance(cust_slots, dict):
                                params.update(cust_slots)
                        except Exception:
                            if not params.get("keyword"):
                                params["keyword"] = str(message or "").strip()[:80]

                from app.routes.tools import execute_registered_workflow_tool

                merged_params = dict(params or {})
                merged_params["_runtime_context"] = dict(runtime_context_for_probe)

                out = execute_registered_workflow_tool(tool_id=tool_id, action=action, params=merged_params)

                # 只保留概要信息，避免 prompt 爆长
                data_preview = ""
                if isinstance(out, dict):
                    if isinstance(out.get("data"), list):
                        data_preview = str(out.get("data")[:3])[:600]
                    elif out.get("data") is not None:
                        data_preview = str(out.get("data"))[:600]
                    elif out.get("raw") is not None:
                        data_preview = str(out.get("raw"))[:600]
                    else:
                        data_preview = str(out)[:600]

                if isinstance(out, dict) and out.get("success") is True:
                    probe_outputs.append(
                        {
                            "tool_id": tool_id,
                            "action": action,
                            "success": True,
                            "message": str((out or {}).get("message") or (out or {}).get("error") or ""),
                            "data_preview": data_preview,
                        }
                    )
            except Exception as e:
                # 降级策略：probe 失败不写入 prompt（保留 probe_outputs 空/部分成功即可）
                logger.warning("ToolProbe 探测失败（将跳过注入）: %s", e)
                continue

        # 3) 把探测结果塞回 context，再规划最终计划
        context_for_compose = dict(context or {})
        if probe_outputs:
            context_for_compose["tool_probe_outputs"] = probe_outputs

        final_plan = self._plan_with_llm(
            plan_id=plan_id,
            user_id=user_id,
            message=message,
            tool_registry=tool_registry,
            context=context_for_compose,
        )
        if final_plan is None:
            return None

        # 4) CriticAgent：validate_plan_graph + required_params 检查；失败则尝试修复一次
        err = validate_plan_graph(final_plan)
        if err is None:
            err = self._validate_required_params(final_plan, tool_registry)

        if err is None:
            return final_plan

        logger.warning("CriticAgent 校验失败，尝试 LLM 修复（最多 1 次）: %s", err)
        repaired = self._critic_repair_with_llm(
            plan_id=plan_id,
            user_id=user_id,
            message=message,
            tool_registry=tool_registry,
            context=context_for_compose,
            error=err,
            invalid_plan=final_plan,
        )
        if repaired is not None:
            err2 = validate_plan_graph(repaired)
            if err2 is None:
                err2 = self._validate_required_params(repaired, tool_registry)
            if err2 is None:
                return repaired

        logger.warning("CriticAgent 修复失败（回退 fallback）: %s", err)
        return None

    @staticmethod
    def _validate_required_params(plan: PlanGraph, tool_registry: Dict[str, Any]) -> Optional[str]:
        """检查节点 params 是否满足 tool_registry 的 required_params。"""
        for node in plan.nodes or []:
            tool_spec = (tool_registry or {}).get(str(node.tool_id) or "")
            if not isinstance(tool_spec, dict):
                continue
            actions = tool_spec.get("actions") or {}
            if not isinstance(actions, dict):
                continue
            action_meta = actions.get(str(node.action) or "")
            if not isinstance(action_meta, dict):
                continue
            required_params = action_meta.get("required_params") or []
            if not isinstance(required_params, list):
                required_params = []
            params = node.params or {}
            for key in required_params:
                if key not in params or params.get(key) is None or str(params.get(key)).strip() == "":
                    return f"节点 {node.node_id} 缺少 required_params: {key}"
        return None

    def _critic_repair_with_llm(
        self,
        plan_id: str,
        user_id: str,
        message: str,
        tool_registry: Dict[str, Any],
        context: Dict[str, Any],
        error: str,
        invalid_plan: PlanGraph,
    ) -> PlanGraph | None:
        """CriticAgent：LLM 修复无效 PlanGraph（只重试一次）。"""
        api_key = getattr(self._ai_service, "api_key", "") or ""
        if not api_key:
            return None

        try:
            tool_specs = []
            for tool_id, spec in tool_registry.items():
                actions = spec.get("actions") or {}
                action_specs = []
                for action_name, action_meta in actions.items():
                    if not isinstance(action_meta, dict):
                        continue
                    action_specs.append(
                        {
                            "action": action_name,
                            "risk": action_meta.get("risk", "low"),
                            "idempotent": bool(action_meta.get("idempotent", False)),
                            "required_params": action_meta.get("required_params", []),
                        }
                    )
                tool_specs.append(
                    {
                        "tool_id": tool_id,
                        "description": spec.get("description", ""),
                        "actions": action_specs,
                    }
                )

            invalid_dict = {
                "plan_id": invalid_plan.plan_id,
                "intent": invalid_plan.intent,
                "todo_steps": invalid_plan.todo_steps,
                "risk_level": invalid_plan.risk_level,
                "nodes": [
                    {
                        "node_id": n.node_id,
                        "tool_id": n.tool_id,
                        "action": n.action,
                        "params": n.params,
                        "risk": n.risk,
                        "idempotent": n.idempotent,
                        "description": n.description,
                        "depends_on": n.depends_on,
                    }
                    for n in (invalid_plan.nodes or [])
                ],
            }

            prompt = {
                "task": "修复一个无效的工作流 PlanGraph JSON，使其满足 validate_plan_graph 规则且满足 required_params 约束。",
                "rules": [
                    "只输出 JSON，不要 markdown。",
                    "node_id 必须唯一且非空。",
                    "所有 nodes 项必须包含 tool_id/action/params/risk/idempotent/description/depends_on 结构字段。",
                    "对于 required_params：必须在 params 中提供非空值（若无法从 user_message 推断，仍需给出最合理的非空占位/默认值，保证结构字段不缺失）。",
                ],
                "validation_error": error,
                "invalid_plan": invalid_dict,
                "user_message": message,
                "context": context,
                "tool_registry": tool_specs,
                "output_schema": {
                    "intent": "string",
                    "todo_steps": ["string"],
                    "risk_level": "low|medium|high",
                    "nodes": [
                        {
                            "node_id": "string",
                            "tool_id": "string",
                            "action": "string",
                            "params": {},
                            "risk": "low|medium|high",
                            "idempotent": "bool",
                            "description": "string",
                            "depends_on": ["node_id"],
                        }
                    ],
                },
            }

            messages = [
                {"role": "system", "content": "你是工作流计划修复器，只输出可执行 JSON。"},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ]

            api_url = getattr(self._ai_service, "api_url", "") or "https://api.deepseek.com/v1/chat/completions"
            response = _get_planner_http_client().post(
                api_url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": getattr(self._ai_service, "model", "") or "deepseek-chat",
                    "messages": messages,
                    "temperature": 0.2,
                    "max_tokens": 1000,
                },
            )
            if response.status_code >= 400:
                return None

            response_data = response.json()
            raw = (
                (response_data.get("choices") or [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            if not raw:
                return None

            raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            raw = self._strip_json_code_fence(raw)
            if not raw:
                return None
            parsed = json.loads(raw)

            nodes: List[WorkflowNode] = []
            for idx, node in enumerate(parsed.get("nodes", []), start=1):
                nodes.append(
                    WorkflowNode(
                        node_id=str(node.get("node_id") or f"node_{idx}"),
                        tool_id=str(node.get("tool_id") or ""),
                        action=str(node.get("action") or ""),
                        params=node.get("params") or {},
                        risk=str(node.get("risk") or "low"),
                        idempotent=bool(node.get("idempotent", False)),
                        description=str(node.get("description") or ""),
                        depends_on=[str(x) for x in (node.get("depends_on") or [])],
                    )
                )

            return PlanGraph(
                plan_id=plan_id,
                intent=str(parsed.get("intent") or invalid_plan.intent or "dynamic_workflow"),
                todo_steps=[str(x) for x in (parsed.get("todo_steps") or invalid_plan.todo_steps or [])],
                nodes=nodes,
                risk_level=str(parsed.get("risk_level") or invalid_plan.risk_level or "low"),
                metadata={"planner": "critic_repair", "message": message},
            )
        except Exception as e:
            logger.warning("CriticAgent 修复失败: %s", e)
            return None

    def _plan_with_llm(
        self,
        plan_id: str,
        user_id: str,
        message: str,
        tool_registry: Dict[str, Any],
        context: Dict[str, Any],
    ) -> PlanGraph | None:
        try:
            tool_specs = []
            for tool_id, spec in tool_registry.items():
                actions = spec.get("actions", {})
                action_specs = []
                for action_name, action_meta in actions.items():
                    action_specs.append(
                        {
                            "action": action_name,
                            "risk": action_meta.get("risk", "low"),
                            "idempotent": bool(action_meta.get("idempotent", False)),
                            "required_params": action_meta.get("required_params", []),
                        }
                    )
                tool_specs.append(
                    {
                        "tool_id": tool_id,
                        "description": spec.get("description", ""),
                        "actions": action_specs,
                    }
                )

            recent_messages = []
            conv_ctx = self._ai_service.get_context(user_id)
            if conv_ctx and conv_ctx.conversation_history:
                recent_messages = conv_ctx.conversation_history[-6:]

            prompt = {
                "task": "根据用户意图生成可执行工作流计划（JSON）。",
                "rules": [
                    "只输出 JSON，不要 markdown。",
                    "优先使用 tool_registry 中已有工具与 action。",
                    "如果步骤有依赖，写到 depends_on。",
                    "todo_steps 要贴合用户语义，不要模板化。",
                    "risk_level 按节点最高风险确定。",
                    "对 products.query / customers.query：必须在 params 填入 keyword 或 model_number 等检索词，"
                    "从用户话中提取（如「七彩乐园的9803」→ keyword 含单位+型号），禁止留空对象 {}。",
                    "如果 context 中包含 tool_probe_outputs 且其中 success=true，请优先使用其中 data_preview 的信息来补全 nodes.params。",
                    "若 context 中 tool_execution_profile 为 normal 或 ui_surface 为 normal 且 intent_channel 为 pro："
                    "仅可使用 availability 为 shared 或 normal_only 的工具；产品查询优先 normal_slot_dispatch.product_query 或 products.query。",
                    "若 context 为全专业链路（未带上述混合标记）：仅使用 shared 或 pro_only，勿选 normal_only。",
                ],
                "user_message": message,
                "recent_messages": recent_messages,
                "context": context,
                "tool_probe_outputs": (context or {}).get("tool_probe_outputs") if isinstance(context, dict) else [],
                "tool_registry": tool_specs,
                "output_schema": {
                    "intent": "string",
                    "todo_steps": ["string"],
                    "risk_level": "low|medium|high",
                    "nodes": [
                        {
                            "node_id": "string",
                            "tool_id": "string",
                            "action": "string",
                            "params": {},
                            "risk": "low|medium|high",
                            "idempotent": "bool",
                            "description": "string",
                            "depends_on": ["node_id"],
                        }
                    ],
                },
            }

            messages = [
                {"role": "system", "content": "你是工作流规划器，只输出可执行 JSON。"},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ]
            api_key = getattr(self._ai_service, "api_key", "") or ""
            api_url = getattr(self._ai_service, "api_url", "") or "https://api.deepseek.com/v1/chat/completions"
            model = getattr(self._ai_service, "model", "") or "deepseek-chat"
            if not api_key:
                return None

            response = _get_planner_http_client().post(
                api_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.1,
                    "max_tokens": 1200,
                },
            )
            if response.status_code >= 400:
                return None
            response_data = response.json()
            raw = (
                (response_data.get("choices") or [{}])[0]
                .get("message", {})
                .get("content", "")
                .strip()
            )
            if not raw:
                return None
            raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            parsed = json.loads(raw)

            nodes: List[WorkflowNode] = []
            for idx, node in enumerate(parsed.get("nodes", []), start=1):
                nodes.append(
                    WorkflowNode(
                        node_id=str(node.get("node_id") or f"node_{idx}"),
                        tool_id=str(node.get("tool_id") or ""),
                        action=str(node.get("action") or ""),
                        params=node.get("params") or {},
                        risk=str(node.get("risk") or "low"),
                        idempotent=bool(node.get("idempotent", False)),
                        description=str(node.get("description") or ""),
                        depends_on=[str(x) for x in (node.get("depends_on") or [])],
                    )
                )

            tool_probe_outputs = []
            user_memory_rag_summary = ""
            try:
                if isinstance(context, dict):
                    user_memory_rag = context.get("user_memory_rag")
                    if isinstance(user_memory_rag, dict):
                        user_memory_rag_summary = str(user_memory_rag.get("summary") or "").strip()
                    tpo = context.get("tool_probe_outputs")
                    if isinstance(tpo, list):
                        tool_probe_outputs = []
                        for item in tpo[:2]:
                            if not isinstance(item, dict):
                                continue
                            tool_probe_outputs.append(
                                {
                                    "tool_id": item.get("tool_id"),
                                    "action": item.get("action"),
                                    "success": bool(item.get("success")),
                                    "message": str(item.get("message") or "").strip()[:120],
                                    "data_preview": str(item.get("data_preview") or "").strip()[:160],
                                }
                            )
            except Exception:
                tool_probe_outputs = []
                user_memory_rag_summary = ""

            return PlanGraph(
                plan_id=plan_id,
                intent=str(parsed.get("intent") or "dynamic_workflow"),
                todo_steps=[str(x) for x in (parsed.get("todo_steps") or [])],
                nodes=nodes,
                risk_level=str(parsed.get("risk_level") or "low"),
                metadata={
                    "planner": "llm",
                    "message": message,
                    "user_memory_rag_summary": user_memory_rag_summary,
                    "tool_probe_outputs": tool_probe_outputs,
                },
            )
        except Exception as err:
            logger.warning("LLM 规划失败，回退规则规划: %s", err, exc_info=True)
            return None

    def _fallback_plan(
        self,
        plan_id: str,
        message: str,
        tool_registry: Dict[str, Any],
    ) -> PlanGraph:
        lower = (message or "").lower()
        nodes: List[WorkflowNode] = []
        todo = ["理解用户目标", "执行可用工具", "输出执行结果"]
        intent = "generic_workflow"

        if ("添加" in message or "新增" in message or "create" in lower) and ("产品" in message):
            intent = "add_product_to_unit"
            todo = [
                "意图分析：识别产品新增任务",
                "全局检查单位是否存在",
                "单位不存在则先创建",
                "新增产品并绑定单位",
                "返回执行明细",
            ]
            if "customers" in tool_registry:
                nodes.append(
                    WorkflowNode(
                        node_id="check_or_create_unit",
                        tool_id="customers",
                        action="ensure_exists",
                        params={},
                        risk="medium",
                        description="确保购买单位存在",
                    )
                )
            if "products" in tool_registry:
                nodes.append(
                    WorkflowNode(
                        node_id="create_product",
                        tool_id="products",
                        action="create",
                        params={},
                        risk="medium",
                        description="创建产品",
                        depends_on=["check_or_create_unit"] if nodes else [],
                    )
                )

        if not nodes:
            # 兜底：挑一个低风险查询，避免空图
            if "products" in tool_registry:
                nodes.append(
                    WorkflowNode(
                        node_id="query_products",
                        tool_id="products",
                        action="query",
                        params={"keyword": message},
                        risk="low",
                        description="查询相关产品",
                        idempotent=True,
                    )
                )
            elif "customers" in tool_registry:
                nodes.append(
                    WorkflowNode(
                        node_id="query_customers",
                        tool_id="customers",
                        action="query",
                        params={"keyword": message},
                        risk="low",
                        description="查询相关客户",
                        idempotent=True,
                    )
                )

        risk = "low"
        if any(node.risk == "high" for node in nodes):
            risk = "high"
        elif any(node.risk == "medium" for node in nodes):
            risk = "medium"

        return PlanGraph(
            plan_id=plan_id,
            intent=intent,
            todo_steps=todo,
            nodes=nodes,
            risk_level=risk,
            metadata={"planner": "fallback", "message": message},
        )
