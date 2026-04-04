# -*- coding: utf-8 -*-
"""
AI 聊天应用服务

编排 AI 聊天业务逻辑：
- 处理即时工具执行（products/customers/shipments/shipment_generate）
- 构建统一响应格式
- 处理确认流程
"""

import asyncio
import json
import logging
import re
import uuid
from typing import Any, Dict, Optional

import httpx

from app.application.workflow import (
    HybridRiskGate,
    LLMWorkflowPlanner,
    WorkflowEngine,
    get_approval_service,
)
from app.services import get_ai_conversation_service

logger = logging.getLogger(__name__)


class AIChatApplicationService:
    """
    AI 聊天应用服务

    编排 AI 对话和即时工具执行，负责：
    - 聊天主流程处理
    - 即时工具执行（source=pro 和普通模式）
    - 响应格式构建
    """

    def __init__(self):
        self.ai_service = get_ai_conversation_service()
        self.workflow_planner = LLMWorkflowPlanner()
        self.risk_gate = HybridRiskGate()
        self.workflow_engine = WorkflowEngine(tool_dispatcher=self._dispatch_workflow_tool)
        self.approval_service = get_approval_service()
        self._pending_workflows: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def _is_pro_source(source: Optional[str]) -> bool:
        """兼容 pro 来源字段的多种写法。"""
        normalized = str(source or "").strip().lower().replace("-", "_")
        return normalized in {"pro", "pro_mode", "promode"}

    @staticmethod
    def _merge_tool_runtime_context(
        user_id: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        runtime_ctx: Dict[str, Any] = {"user_id": user_id, "message": message}
        if isinstance(context, dict):
            for key in ("ui_surface", "intent_channel", "tool_execution_profile"):
                if key in context and context[key] is not None:
                    runtime_ctx[key] = context[key]
            # 透传 Excel 分析上下文，支持自然语言按 sheet 入模板库
            for key in ("excel_analysis", "last_excel_analysis_context"):
                if key in context and isinstance(context[key], dict):
                    runtime_ctx[key] = context[key]
        return runtime_ctx

    def process_chat(
        self,
        user_id: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
        file_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理聊天请求

        Args:
            user_id: 用户 ID
            message: 用户消息
            context: 额外上下文
            source: 来源标识（pro 表示专业模式）
            file_context: 文件上下文（用于确认流程）

        Returns:
            处理结果字典
        """
        if not message:
            return {
                "success": False,
                "message": "消息内容不能为空",
            }

        self._handle_confirmation_flow(user_id, message, file_context)
        workflow_result = self._try_handle_dynamic_workflow(
            user_id=user_id,
            message=message,
            source=source,
            context=context or {},
            file_context=file_context or {},
        )
        if workflow_result is not None:
            return workflow_result

        enriched_context = dict(context or {})
        if isinstance(file_context, dict):
            excel_file_path = file_context.get("file_path") or file_context.get("original_file_path")
            if excel_file_path:
                excel_analysis_obj = {
                    "file_path": str(excel_file_path).strip(),
                }
                sheet_name = file_context.get("sheet_name")
                if sheet_name:
                    excel_analysis_obj["sheet_name"] = str(sheet_name).strip()
                enriched_context["excel_analysis"] = excel_analysis_obj

        prepared_context = self._inject_excel_vector_context(message=message, context=enriched_context)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            ai_result = loop.run_until_complete(
                self.ai_service.chat(user_id, message, prepared_context, source=source)
            )
        finally:
            loop.close()

        logger.info(f"用户 {user_id} 消息：{message[:50]}... -> {ai_result.get('action', 'unknown')}")

        response_data = self._build_response(ai_result, source, message)

        return response_data

    def _inject_excel_vector_context(
        self,
        message: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        若请求携带 excel_index_id，则做一次语义检索并将结果写入 excel_vector_context。
        与 context 中已有的 excel_analysis（专用 extract-grid 等）可同时存在，二者一并进入下游提示词。
        """
        if not isinstance(context, dict):
            return {}

        excel_index_id = (
            str(context.get("excel_index_id") or context.get("excel_vector_index_id") or "").strip()
        )
        if not excel_index_id:
            return context

        top_k_raw = context.get("excel_top_k", 5)
        try:
            top_k = int(top_k_raw)
        except Exception:
            top_k = 5

        try:
            from app.application import get_excel_vector_search_app_service

            search_service = get_excel_vector_search_app_service()
            result = search_service.query(
                index_id=excel_index_id,
                query_text=message,
                top_k=top_k,
            )
            if result.get("success"):
                enriched = dict(context)
                enriched["excel_vector_context"] = {
                    "index_id": excel_index_id,
                    "query": message,
                    "hits": result.get("hits", []),
                }
                return enriched
        except Exception as err:
            logger.warning("注入 Excel 向量上下文失败: %s", err, exc_info=True)

        return context

    @staticmethod
    def _is_number_text(value: str) -> bool:
        text = str(value or "").strip()
        if not text:
            return False
        try:
            float(text.replace(",", ""))
            return True
        except Exception:
            return False

    @staticmethod
    def _model_like_score(value: str) -> float:
        text = str(value or "").strip()
        if not text:
            return 0.0
        has_digit = any(ch.isdigit() for ch in text)
        has_alpha = any(ch.isalpha() for ch in text)
        compact = text.replace("-", "").replace("_", "")
        if len(compact) < 2 or len(compact) > 24:
            return 0.0
        if has_digit and has_alpha:
            return 1.0
        if has_digit and len(compact) <= 12:
            return 0.6
        return 0.0

    def _infer_excel_column_roles(self, records: list[Dict[str, Any]]) -> tuple[Dict[str, str], float]:
        if not records:
            return {}, 0.0
        keys = [k for k in records[0].keys() if str(k).strip()]
        if not keys:
            return {}, 0.0

        stats: Dict[str, Dict[str, float]] = {}
        for key in keys:
            values = [str((row or {}).get(key) or "").strip() for row in records]
            non_empty = [v for v in values if v]
            if not non_empty:
                continue
            count = float(len(non_empty))
            numeric_ratio = sum(1 for v in non_empty if self._is_number_text(v)) / count
            model_ratio = sum(self._model_like_score(v) for v in non_empty) / count
            unique_ratio = len(set(non_empty)) / count
            avg_len = sum(len(v) for v in non_empty) / count
            repeat_ratio = 1.0 - unique_ratio
            stats[key] = {
                "numeric_ratio": numeric_ratio,
                "model_ratio": model_ratio,
                "unique_ratio": unique_ratio,
                "avg_len": avg_len,
                "repeat_ratio": repeat_ratio,
            }

        if not stats:
            return {}, 0.0

        score_map = {
            "unit_price": lambda s: s["numeric_ratio"] * 0.9 + (1.0 - s["avg_len"] / 20.0) * 0.1,
            "model_number": lambda s: s["model_ratio"] * 0.8 + s["unique_ratio"] * 0.2,
            "unit_name": lambda s: (1.0 - s["numeric_ratio"]) * 0.35 + s["repeat_ratio"] * 0.5 + (1.0 - min(s["avg_len"], 20.0) / 20.0) * 0.15,
            "product_name": lambda s: (1.0 - s["numeric_ratio"]) * 0.45 + s["unique_ratio"] * 0.35 + min(s["avg_len"], 30.0) / 30.0 * 0.2,
        }

        ranked_by_role: Dict[str, list[tuple[str, float]]] = {}
        for role, fn in score_map.items():
            ranked_by_role[role] = sorted(
                [(k, float(fn(v))) for k, v in stats.items()],
                key=lambda x: x[1],
                reverse=True,
            )

        # 避免角色冲突：如果推断冲突，优先保留最强语义的列，其他角色留空。
        used: set[str] = set()
        resolved: Dict[str, str] = {}
        confidences: list[float] = []
        for role in ("unit_price", "model_number", "unit_name", "product_name"):
            ranked = ranked_by_role.get(role) or []
            key = str((ranked[0][0] if ranked else "") or "").strip()
            if key and key not in used:
                resolved[role] = key
                used.add(key)
                top_score = ranked[0][1] if ranked else 0.0
                next_score = ranked[1][1] if len(ranked) > 1 else 0.0
                # 置信度由绝对分和领先差共同决定
                role_conf = max(0.0, min(1.0, top_score * 0.7 + max(0.0, top_score - next_score) * 0.3))
                confidences.append(role_conf)
            else:
                resolved[role] = ""
                confidences.append(0.0)
        confidence = sum(confidences) / float(len(confidences) or 1)
        return resolved, confidence

    def _infer_excel_column_roles_with_llm(self, records: list[Dict[str, Any]]) -> Dict[str, str]:
        if not records:
            return {}
        try:
            api_key = str(getattr(self.ai_service, "api_key", "") or "").strip()
            api_url = str(getattr(self.ai_service, "api_url", "") or "https://api.deepseek.com/v1/chat/completions")
            model = str(getattr(self.ai_service, "model", "") or "deepseek-chat")
            if not api_key:
                return {}

            keys = [str(k).strip() for k in records[0].keys() if str(k).strip()]
            columns = []
            for key in keys[:30]:
                samples = []
                for row in records[:12]:
                    val = str((row or {}).get(key) or "").strip()
                    if val:
                        samples.append(val[:40])
                    if len(samples) >= 6:
                        break
                columns.append({"column": key, "samples": samples})

            prompt = {
                "task": "判断 Excel 列语义角色",
                "roles": ["unit_name", "product_name", "model_number", "unit_price"],
                "columns": columns,
                "rules": [
                    "只输出 JSON",
                    "每个角色映射一个列名，不确定时填空字符串",
                    "不要编造不存在的列名",
                ],
                "output_schema": {
                    "unit_name": "column_name_or_empty",
                    "product_name": "column_name_or_empty",
                    "model_number": "column_name_or_empty",
                    "unit_price": "column_name_or_empty",
                },
            }
            resp = httpx.post(
                api_url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "你是表格列语义识别器，只输出 JSON。"},
                        {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
                    ],
                    "temperature": 0.0,
                    "max_tokens": 300,
                },
                timeout=10.0,
            )
            if resp.status_code >= 400:
                return {}
            content = (
                ((resp.json().get("choices") or [{}])[0].get("message") or {}).get("content") or ""
            ).strip()
            if not content:
                return {}
            content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            parsed = json.loads(content)
            roles = {}
            for role in ("unit_name", "product_name", "model_number", "unit_price"):
                key = str(parsed.get(role) or "").strip()
                roles[role] = key if key in keys else ""
            return roles
        except Exception as err:
            logger.debug("LLM 列角色推断失败: %s", err)
            return {}

    def _extract_excel_import_records(self, excel_analysis: Dict[str, Any]) -> list[Dict[str, Any]]:
        records: list[Dict[str, Any]] = []
        preview_data = excel_analysis.get("preview_data") or {}
        sample_rows = preview_data.get("sample_rows") or []
        if isinstance(sample_rows, list):
            for row in sample_rows:
                if isinstance(row, dict):
                    records.append(dict(row))

        grid_rows = ((preview_data.get("grid_preview") or {}).get("rows") or [])
        if isinstance(grid_rows, list) and len(grid_rows) >= 2:
            header = grid_rows[0]
            if isinstance(header, list):
                header_keys = [str(h or "").strip() for h in header]
                for row in grid_rows[1:]:
                    if not isinstance(row, list):
                        continue
                    item: Dict[str, Any] = {}
                    for idx, key in enumerate(header_keys):
                        if not key:
                            continue
                        item[key] = row[idx] if idx < len(row) else None
                    if any(str(v or "").strip() for v in item.values()):
                        records.append(item)

        # 某些表格第一行是“真实表头”，但被解析为数据行（键名为 Unnamed:*）
        if records:
            first = records[0]
            if isinstance(first, dict):
                keys = list(first.keys())
                key_unnamed_ratio = 0.0
                if keys:
                    unnamed_count = sum(1 for k in keys if str(k).startswith("Unnamed:"))
                    key_unnamed_ratio = unnamed_count / len(keys)
                header_values = [str(first.get(k) or "").strip() for k in keys]
                label_like_ratio = (
                    sum(1 for v in header_values if v and not self._is_number_text(v)) / float(len(header_values) or 1)
                )
                if key_unnamed_ratio >= 0.5 and label_like_ratio >= 0.5 and len(records) >= 2:
                    rebuilt: list[Dict[str, Any]] = []
                    for row in records[1:]:
                        if not isinstance(row, dict):
                            continue
                        mapped: Dict[str, Any] = {}
                        for idx, key in enumerate(keys):
                            header = header_values[idx] if idx < len(header_values) else ""
                            if not header:
                                continue
                            mapped[header] = row.get(key)
                        if any(str(v or "").strip() for v in mapped.values()):
                            rebuilt.append(mapped)
                    if rebuilt:
                        records = rebuilt

        inferred_roles, role_conf = self._infer_excel_column_roles(records)
        if role_conf < 0.55:
            llm_roles = self._infer_excel_column_roles_with_llm(records)
            # 低置信度时优先采用 LLM 非空结果，空值回退特征推断
            for role in ("unit_name", "product_name", "model_number", "unit_price"):
                if llm_roles.get(role):
                    inferred_roles[role] = llm_roles[role]
        unit_key = inferred_roles.get("unit_name", "")
        product_key = inferred_roles.get("product_name", "")
        model_key = inferred_roles.get("model_number", "")
        price_key = inferred_roles.get("unit_price", "")

        dedup: set[tuple[str, str, str]] = set()
        normalized: list[Dict[str, Any]] = []
        for row in records:
            unit_name = str((row or {}).get(unit_key) or "").strip() if unit_key else ""
            product_name = str((row or {}).get(product_key) or "").strip() if product_key else ""
            model_number = str((row or {}).get(model_key) or "").strip().upper() if model_key else ""
            price_text = str((row or {}).get(price_key) or "").strip() if price_key else ""
            try:
                unit_price = float(price_text) if price_text else 0.0
            except Exception:
                unit_price = 0.0
            if not unit_name:
                continue
            if not product_name and not model_number:
                continue
            dedup_key = (unit_name, product_name, model_number)
            if dedup_key in dedup:
                continue
            dedup.add(dedup_key)
            normalized.append(
                {
                    "unit_name": unit_name,
                    "product_name": product_name or model_number,
                    "model_number": model_number,
                    "unit_price": unit_price,
                }
            )
        return normalized

    @staticmethod
    def _excel_analysis_payload_present(context: Optional[Dict[str, Any]]) -> bool:
        """请求里是否带有可用的 excel_analysis（与 extract-grid 结构一致）。"""
        ea = (context or {}).get("excel_analysis") if isinstance(context, dict) else None
        if not isinstance(ea, dict) or not ea:
            return False
        if str(ea.get("summary") or "").strip():
            return True
        fields = ea.get("fields")
        if isinstance(fields, list) and len(fields) > 0:
            return True
        pd = ea.get("preview_data") if isinstance(ea.get("preview_data"), dict) else {}
        if isinstance(pd.get("sample_rows"), list) and len(pd.get("sample_rows")) > 0:
            return True
        grid = (pd.get("grid_preview") or {}).get("rows") if isinstance(pd, dict) else None
        return isinstance(grid, list) and len(grid) >= 2

    @staticmethod
    def _looks_like_short_excel_import_command(text: str) -> bool:
        """
        用户常用短指令（如「加入数据库」）。无 excel_analysis 时若落入 DeepSeek / planner 会长时间无响应。
        """
        t = str(text or "").strip()
        if not t:
            return False
        exact = {
            "加入数据库",
            "加入库",
            "入库",
            "添加到库",
            "写入数据库",
            "导入数据库",
        }
        if t in exact:
            return True
        if len(t) > 40:
            return False
        return any(
            k in t
            for k in (
                "加入数据库",
                "导入数据库",
                "添加到库",
                "写入数据库",
            )
        )

    def _try_handle_dynamic_workflow(
        self,
        user_id: str,
        message: str,
        source: Optional[str],
        context: Dict[str, Any],
        file_context: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if not self._is_pro_source(source):
            return None

        text = str(message or "").strip()
        if not text:
            return None

        merged_file_ctx = {}
        if isinstance(context, dict):
            merged_file_ctx.update(context.get("file_analysis") or {})
            merged_file_ctx.update(context.get("file_context") or {})
        if isinstance(file_context, dict):
            merged_file_ctx.update(file_context)

        import_intent = any(k in text for k in ("导入", "入库", "添加到数据库", "写入数据库"))
        if import_intent and (merged_file_ctx.get("suggested_use") == "unit_products_db"):
            saved_name = str(merged_file_ctx.get("saved_name") or "").strip()
            unit_name = str(
                merged_file_ctx.get("unit_name")
                or merged_file_ctx.get("unit_name_guess")
                or ""
            ).strip()
            if not saved_name:
                return {
                    "success": True,
                    "message": "处理完成",
                    "response": "已识别导入意图，但缺少源文件上下文。请先上传并分析 .db 文件。",
                    "data": {"text": "请先上传并分析 .db 文件。", "action": "followup", "data": {}},
                }
            if not unit_name:
                return {
                    "success": True,
                    "message": "处理完成",
                    "response": "已识别导入意图，请补充购买单位名称后继续导入。",
                    "data": {
                        "text": "请补充购买单位名称后继续导入。",
                        "action": "followup",
                        "data": {"missing_fields": ["unit_name"]},
                    },
                }

            todo_lines = [
                "检查购买单位是否存在，不存在则自动创建",
                "读取源库 products 表并映射字段",
                "按单位+型号/名称去重后导入产品",
                "返回导入结果（新增/跳过/失败）",
            ]
            try:
                from app.application import get_unit_products_import_app_service

                service = get_unit_products_import_app_service()
                result = service.import_unit_products(
                    saved_name=saved_name,
                    unit_name=unit_name,
                    create_purchase_unit=True,
                    skip_duplicates=True,
                )
                if not result.get("success"):
                    return {
                        "success": False,
                        "message": result.get("message") or "导入失败",
                    }
                response_text = (
                    "导入完成：\n"
                    f"- 购买单位：{result.get('unit_name')}\n"
                    f"- 是否新建单位：{'是' if result.get('created_unit') else '否'}\n"
                    f"- 导入产品数：{result.get('imported', 0)}\n"
                    f"- 跳过重复：{result.get('skipped_duplicates', 0)}"
                )
                return {
                    "success": True,
                    "message": "处理完成",
                    "response": response_text,
                    "data": {
                        "text": response_text,
                        "action": "workflow_done",
                        "data": {
                            "intent": "import_unit_products_db",
                            "thinking_steps": "已识别文件导入意图并执行单位+产品自动入库流程",
                            "todo": todo_lines,
                            "result": result,
                        },
                    },
                }
            except Exception as err:
                logger.error("文件导入工作流执行失败: %s", err, exc_info=True)
                return {
                    "success": False,
                    "message": f"导入失败：{str(err)}",
                }

        # 无分析结果时短指令勿走 LLM（混合 normal 画像下否则会长时间阻塞在 DeepSeek）
        if not self._excel_analysis_payload_present(context) and self._looks_like_short_excel_import_command(
            text
        ):
            return {
                "success": True,
                "message": "处理完成",
                "response": (
                    "未检测到 Excel 分析上下文。请先点击工具栏「分析 Excel」上传并分析表格，再发送「加入数据库」等指令。\n"
                    "若已分析过，可能是会话切换或页面刷新导致上下文丢失——请重新分析一次。"
                ),
                "data": {
                    "text": "未检测到 Excel 分析上下文，请先分析 Excel。",
                    "action": "followup",
                    "data": {"intent": "excel_import_missing_context"},
                },
            }

        excel_analysis = (context or {}).get("excel_analysis") if isinstance(context, dict) else None
        if (
            isinstance(excel_analysis, dict)
            and any(k in text for k in ("数据库", "入库", "导入", "添加到库"))
        ):
            fields = excel_analysis.get("fields") or []
            field_names = []
            for item in fields[:10]:
                if isinstance(item, dict):
                    field_names.append(str(item.get("label") or item.get("name") or "").strip())
                else:
                    field_names.append(str(item).strip())
            field_names = [x for x in field_names if x]
            summary = str(excel_analysis.get("summary") or "").strip()
            todo_lines = [
                "解析 Excel 数据并映射单位/产品/型号/价格字段",
                "检查购买单位是否存在，不存在则创建",
                "检查产品是否存在，缺失则创建并绑定单位",
                "返回导入结果（新增单位/新增产品/跳过重复）",
            ]
            records = self._extract_excel_import_records(excel_analysis)
            if not records:
                followup_text = (
                    "我已读取到 Excel 上下文，但未解析到可入库的单位/产品记录。\n"
                    f"已识别字段: {'、'.join(field_names) if field_names else '未识别到字段'}"
                )
                if summary:
                    followup_text += f"\n上下文摘要:\n{summary[:500]}"
                return {
                    "success": True,
                    "message": "处理完成",
                    "response": followup_text,
                    "data": {
                        "text": followup_text,
                        "action": "followup",
                        "data": {
                            "intent": "excel_import_to_db",
                            "thinking_steps": "已完成字段识别，但记录提取为空",
                            "todo": todo_lines,
                        },
                    },
                }

            try:
                from app.bootstrap import get_products_service
                products_service = get_products_service()
                customer_service = None
                customer_service_error = ""
                try:
                    from app.bootstrap import get_customer_app_service

                    customer_service = get_customer_app_service()
                except Exception as customer_err:
                    customer_service_error = str(customer_err)
                    logger.warning("购买单位服务不可用，降级为仅产品入库: %s", customer_err)

                created_units = 0
                created_products = 0
                skipped_products = 0
                touched_units: set[str] = set()

                for row in records:
                    unit_name = str(row.get("unit_name") or "").strip()
                    product_name = str(row.get("product_name") or "").strip()
                    model_number = str(row.get("model_number") or "").strip().upper()
                    unit_price = float(row.get("unit_price") or 0.0)
                    touched_units.add(unit_name)

                    if customer_service is not None:
                        matched = customer_service.match_purchase_unit(unit_name)
                        if not matched:
                            create_unit = customer_service.create({"customer_name": unit_name})
                            if create_unit.get("success"):
                                created_units += 1

                    exists_result = products_service.get_products(
                        unit_name=unit_name,
                        model_number=model_number or None,
                        keyword=(product_name or model_number or None),
                        page=1,
                        per_page=5,
                    )
                    existed = False
                    if exists_result.get("success"):
                        rows = exists_result.get("data") or []
                        for item in rows:
                            item_name = str(item.get("name") or item.get("product_name") or "").strip()
                            item_model = str(item.get("model_number") or "").strip().upper()
                            if model_number and item_model == model_number:
                                existed = True
                                break
                            if product_name and item_name == product_name:
                                existed = True
                                break
                    if existed:
                        skipped_products += 1
                        continue

                    create_product = products_service.create_product(
                        {
                            "name": product_name or model_number,
                            "product_name": product_name or model_number,
                            "product_code": model_number or None,
                            "model_number": model_number or None,
                            "unit_price": unit_price,
                            "price": unit_price,
                            "unit": unit_name,
                        }
                    )
                    if create_product.get("success"):
                        created_products += 1

                units_hint = ""
                if touched_units:
                    preview = "、".join(sorted(touched_units))[:200]
                    units_hint = f"\n- Excel 中的购买单位：{preview}"
                explain_customers = ""
                if created_units == 0 and touched_units:
                    explain_customers = (
                        "\n说明：上述购买单位在数据库中均已存在（或已精确/模糊匹配到已有客户），"
                        "因此「客户总数」不会增加；若新增了产品，请到产品页按对应单位筛选查看。"
                    )
                elif created_units > 0:
                    explain_customers = (
                        "\n说明：已新建购买单位，客户列表中的客户总数应相应增加。"
                    )

                response_text = (
                    "已按聊天请求完成 Excel 入库：\n"
                    f"- 解析记录数：{len(records)}\n"
                    f"- 涉及购买单位数：{len(touched_units)}\n"
                    f"- 新增购买单位：{created_units}\n"
                    f"- 新增产品：{created_products}\n"
                    f"- 跳过重复产品：{skipped_products}"
                    f"{units_hint}"
                    f"{explain_customers}"
                )
                if customer_service is None and customer_service_error:
                    response_text += "\n- 购买单位服务不可用，已降级为仅产品入库"
                return {
                    "success": True,
                    "message": "处理完成",
                    "response": response_text,
                    "data": {
                        "text": response_text,
                        "action": "workflow_done",
                        "data": {
                            "intent": "excel_import_to_db",
                            "thinking_steps": "已基于 Excel 上下文完成字段映射、单位校验与产品入库执行",
                            "todo": todo_lines,
                            "result": {
                                "records": len(records),
                                "touched_units": len(touched_units),
                                "created_units": created_units,
                                "created_products": created_products,
                                "skipped_products": skipped_products,
                                "unit_service_available": customer_service is not None,
                                "unit_service_error": customer_service_error,
                            },
                        },
                    },
                }
            except Exception as err:
                logger.error("Excel 上下文入库执行失败: %s", err, exc_info=True)
                return {
                    "success": False,
                    "message": f"入库失败：{str(err)}",
                }

        from app.application.normal_chat_dispatch import (
            build_product_query_response_dict,
            resolve_tool_execution_profile,
            route_normal_mode_message,
            run_normal_slot_shipment_preview,
        )

        profile = resolve_tool_execution_profile(context if isinstance(context, dict) else {})
        if profile == "normal":
            rr = route_normal_mode_message(text)
            if rr.get("intent") == "product_query":
                pq = build_product_query_response_dict(rr)
                if pq:
                    return pq
            if rr.get("intent") == "shipment":
                ship = run_normal_slot_shipment_preview(text)
                if ship.get("success"):
                    ship.pop("normal_slot_dispatch", None)
                    return ship

        # 处理混合模式下的确认/取消
        pending = self._pending_workflows.get(user_id)
        if pending:
            confirm_words = {"确认", "是", "好的", "继续", "执行", "ok", "yes"}
            cancel_words = {"取消", "否", "不要", "停止", "no"}
            if text.lower() in confirm_words or text in confirm_words:
                plan = pending.get("plan")
                runtime_ctx = pending.get("runtime_context", {})
                approval_required = pending.get("approval_required", False)
                approval_nodes = pending.get("approval_nodes", [])

                if approval_required and approval_nodes:
                    for node_info in approval_nodes:
                        node = None
                        for n in plan.nodes:
                            if n.node_id == node_info.get("node_id"):
                                node = n
                                break
                        if node:
                            self.approval_service.create_approval_request(
                                plan_id=plan.plan_id,
                                node=node,
                                runtime_context=runtime_ctx,
                                plan=plan,
                            )

                    return {
                        "success": True,
                        "message": "处理完成",
                        "response": "已提交审批请求，请等待审批完成后继续。",
                        "data": {
                            "text": "已提交审批请求，请等待审批完成后继续。",
                            "action": "approval_pending",
                            "data": {
                                "plan_id": plan.plan_id,
                                "approval_required": True,
                                "approval_nodes": approval_nodes,
                            },
                        },
                    }

                run_result = self.workflow_engine.run(plan=plan, runtime_context=runtime_ctx, max_retries=1)
                self._pending_workflows.pop(user_id, None)
                return self._format_workflow_run_response(
                    plan,
                    run_result,
                    user_message=str(runtime_ctx.get("message") or ""),
                )
            if text.lower() in cancel_words or text in cancel_words:
                self._pending_workflows.pop(user_id, None)
                return {
                    "success": True,
                    "message": "处理完成",
                    "response": "已取消本次工作流执行。",
                    "data": {"text": "已取消本次工作流执行。", "action": "workflow_cancelled", "data": {}},
                }

        # 普通工具画像（含「普通界面 + 专业意图」）：未命中槽位时勿走 LLM 工作流规划，避免长时间阻塞在 plan()；
        # 交给下方主对话链路（DeepSeek 等），体验与普通聊天一致。
        if profile == "normal":
            return None

        # 专业界面默认画像：发货单/开单句式与普通版槽位路由一致时，勿让 LLM 工作流规划抢先返回
        # 「我已根据语义生成动态工作流计划…节点 products.query / products.create…」，
        # 否则 Jarvis 收不到主链路里的 shipment_generate / toolCall，用户只看到冗长计划文案。
        if profile == "pro_default":
            rr_pro_ship = route_normal_mode_message(text)
            if rr_pro_ship.get("intent") == "shipment":
                # 订单句若能被 _parse_order_text 结构化，直接下发 shipment_generate / toolCall，
                # 避免再走意图识别（槽位空→追问）或主模型只回文本导致前端从不调用 /api/tools/execute。
                try:
                    from app.routes.tools import _parse_order_text

                    parsed_quick = _parse_order_text(text)
                except Exception:
                    parsed_quick = {"success": False}
                if parsed_quick.get("success"):
                    # 结构与 _build_tool_call_response 一致，避免把多余键摊进 toolCall.params
                    quick_ai = {
                        "text": "已识别订单，正在生成发货单…",
                        "action": "tool_call",
                        "data": {
                            "tool_key": "shipment_generate",
                            "intent": "shipment_generate",
                            "slots": {
                                "unit_name": (parsed_quick.get("unit_name") or "").strip(),
                                "products": parsed_quick.get("products") or [],
                            },
                            "hints": [],
                            "habit_suggestion": None,
                        },
                    }
                    return self._build_response(quick_ai, source, text)
                return None

        # 动态规划：不依赖关键词硬编码决策
        from app.routes.tools import get_workflow_tool_registry

        tool_registry = get_workflow_tool_registry()
        plan = self.workflow_planner.plan(
            user_id=user_id,
            message=message,
            tool_registry=tool_registry,
            context=context,
        )

        decision = self.risk_gate.evaluate(plan=plan, context=context)
        runtime_ctx = self._merge_tool_runtime_context(user_id, message, context)
        thinking_steps = self._build_workflow_thinking_steps(plan=plan, decision_reason=decision.reason)

        approval_required_nodes = self.approval_service.get_approval_required_nodes(plan)
        has_approval_requirement = bool(approval_required_nodes)
        approval_info = ""
        if has_approval_requirement:
            approval_node_names = [f"{n.tool_id}.{n.action}" for n in approval_required_nodes]
            approval_info = f"\n以下操作需要审批后执行：" + "、".join(approval_node_names)

        if decision.requires_confirmation or has_approval_requirement:
            self._pending_workflows[user_id] = {
                "plan": plan,
                "runtime_context": runtime_ctx,
                "pending_id": uuid.uuid4().hex,
                "approval_required": has_approval_requirement,
                "approval_nodes": [
                    {"node_id": n.node_id, "tool_id": n.tool_id, "action": n.action, "params": n.params}
                    for n in approval_required_nodes
                ],
            }
            todo_text = "\n".join(f"- {step}" for step in (plan.todo_steps or []))
            response_text = (
                "我已根据语义生成动态工作流计划：\n"
                f"{thinking_steps}\n\n"
                f"{todo_text}\n\n"
                f"检测到中高风险步骤（{', '.join(decision.blocking_nodes)}），"
                "回复「确认」继续执行，回复「取消」终止。"
                f"{approval_info if has_approval_requirement else ''}"
            )
            return {
                "success": True,
                "message": "处理完成",
                "response": response_text,
                "data": {
                    "text": response_text,
                    "action": "workflow_confirmation_required",
                    "data": {
                        "plan_id": plan.plan_id,
                        "intent": plan.intent,
                        "thinking_steps": thinking_steps,
                        "todo": plan.todo_steps,
                        "blocking_nodes": decision.blocking_nodes,
                        "reason": decision.reason,
                        "approval_required": has_approval_requirement,
                        "approval_nodes": [
                            {"node_id": n.node_id, "tool_id": n.tool_id, "action": n.action}
                            for n in approval_required_nodes
                        ],
                    },
                },
            }

        use_agentic = bool((runtime_ctx.get("excel_analysis") or {}).get("file_path"))
        run_result = self.workflow_engine.run(
            plan=plan,
            runtime_context=runtime_ctx,
            max_retries=1,
            agentic_loop=use_agentic,
            tool_registry=tool_registry,
            user_id=user_id,
        )
        return self._format_workflow_run_response(
            plan,
            run_result,
            thinking_steps=thinking_steps,
            user_message=str(message or ""),
        )

    def _build_workflow_thinking_steps(self, plan, decision_reason: str) -> str:
        node_lines = []
        for node in (plan.nodes or []):
            deps = ",".join(node.depends_on) if node.depends_on else "无"
            node_lines.append(
                f"- 节点 {node.node_id}: {node.tool_id}.{node.action} "
                f"(risk={node.risk}, depends_on={deps})"
            )
        nodes_text = "\n".join(node_lines) if node_lines else "- 无可执行节点"

        metadata = getattr(plan, "metadata", {}) or {}
        user_memory_rag_summary = str(metadata.get("user_memory_rag_summary") or "").strip()
        tool_probe_outputs = metadata.get("tool_probe_outputs") or []
        if not isinstance(tool_probe_outputs, list):
            tool_probe_outputs = []

        probe_lines = []
        for item in tool_probe_outputs[:3]:
            if not isinstance(item, dict):
                continue
            tid = str(item.get("tool_id") or "").strip()
            action = str(item.get("action") or "").strip()
            ok = bool(item.get("success"))
            msg = str(item.get("message") or "").strip()
            preview = str(item.get("data_preview") or "").strip()
            if preview:
                preview = preview[:220] + ("…" if len(preview) > 220 else "")
            probe_lines.append(f"- {tid}.{action}: success={ok}; {msg} {preview}".strip())

        memory_block = f"3.5) 用户记忆 RAG 概览:\n{user_memory_rag_summary}\n" if user_memory_rag_summary else ""
        probe_block = (
            "3.6) 工具探测概览:\n"
            + ("\n".join(probe_lines) if probe_lines else "- 无成功探测结果")
            + "\n"
        )
        return (
            "思考步骤:\n"
            f"1) 意图理解: {plan.intent}\n"
            "2) 计划生成: 基于工具注册表构建可执行节点图\n"
            f"3) 风险判断: {decision_reason}\n"
            f"{memory_block}{probe_block}"
            "4) 执行编排: 按依赖顺序执行节点并传递上下文\n"
            f"5) 节点图:\n{nodes_text}"
        )

    def _workflow_products_float_query(
        self, plan, run_result, user_message: str
    ) -> str:
        """从产品查询节点参数/结果或用户原话中提取副窗搜索词。"""
        for node in plan.nodes or []:
            if node.tool_id == "products" and node.action == "query":
                p = node.params or {}
                q = (
                    str(p.get("keyword") or "").strip()
                    or str(p.get("model_number") or "").strip()
                    or str(p.get("product_name") or p.get("name") or "").strip()
                )
                if q:
                    return q
        for r in run_result.node_results:
            if not r.success or r.tool_id != "products" or r.action != "query":
                continue
            out = r.output or {}
            rows = out.get("data") or []
            if isinstance(rows, list) and rows:
                row = rows[0] if isinstance(rows[0], dict) else {}
                if isinstance(row, dict):
                    m = str(row.get("model_number") or "").strip()
                    n = str(row.get("name") or row.get("product_name") or "").strip()
                    if m:
                        return m
                    if n:
                        return n
        return str(user_message or "").strip()

    def _format_workflow_run_response(
        self,
        plan,
        run_result,
        thinking_steps: str = "",
        user_message: str = "",
    ) -> Dict[str, Any]:
        lines = [f"工作流: {plan.intent}", f"计划ID: {plan.plan_id}"]
        if thinking_steps:
            lines.append(thinking_steps)
        if plan.todo_steps:
            lines.append("TODO:")
            lines.extend([f"- {x}" for x in plan.todo_steps])
        lines.append("执行结果:")
        for item in run_result.node_results:
            if item.success and item.tool_id == "products" and item.action == "query":
                rows = (item.output or {}).get("data") or []
                n = len(rows) if isinstance(rows, list) else 0
                lines.append(f"- {item.node_id}: 成功（产品库命中 {n} 条）")
                if isinstance(rows, list) and rows:
                    from app.utils.ai_helpers import format_money, safe_float

                    for row in rows[:5]:
                        if not isinstance(row, dict):
                            continue
                        m = str(row.get("model_number") or "").strip() or "-"
                        name = str(row.get("name") or row.get("product_name") or "-").strip()
                        p = safe_float(row.get("price"))
                        u = str(row.get("unit") or "").strip() or "-"
                        lines.append(f"    · {m} / {name} / ￥{format_money(p)} / 单位:{u}")
            elif item.success:
                lines.append(f"- {item.node_id}: 成功")
            else:
                lines.append(f"- {item.node_id}: 失败（{item.error}）")
        if run_result.message:
            lines.append(f"说明: {run_result.message}")
        response_text = "\n".join(lines)
        payload: Dict[str, Any] = {
            "success": run_result.success,
            "message": "处理完成" if run_result.success else "处理失败",
            "response": response_text,
            "data": {
                "text": response_text,
                "action": "workflow_done" if run_result.success else "workflow_failed",
                "data": {
                    "plan_id": plan.plan_id,
                    "intent": plan.intent,
                    "thinking_steps": thinking_steps,
                    "todo": plan.todo_steps,
                    "node_results": [
                        {
                            "node_id": r.node_id,
                            "success": r.success,
                            "tool_id": r.tool_id,
                            "action": r.action,
                            "error": r.error,
                        }
                        for r in run_result.node_results
                    ],
                },
            },
        }
        if run_result.success and any(
            r.success and r.tool_id == "products" and r.action == "query"
            for r in run_result.node_results
        ):
            q = self._workflow_products_float_query(plan, run_result, user_message)
            payload["autoAction"] = {
                "type": "show_products_float",
                "feature": "products",
                "query": q,
            }
            if q:
                lines.append(f"\n已为你打开产品副窗，搜索：{q}")
            else:
                lines.append("\n已为你打开产品副窗，可在卡片中查询或编辑。")
            payload["response"] = "\n".join(lines)
            payload["data"]["text"] = payload["response"]

        slot_overlay = self._normal_slot_dispatch_chat_overlay(run_result)
        if slot_overlay:
            if slot_overlay.get("response"):
                payload["response"] = slot_overlay["response"]
            if slot_overlay.get("message"):
                payload["message"] = slot_overlay["message"]
            if slot_overlay.get("autoAction"):
                payload["autoAction"] = slot_overlay["autoAction"]
            if slot_overlay.get("task"):
                payload["task"] = slot_overlay["task"]
            payload.setdefault("data", {})
            payload["data"]["text"] = payload["response"]

        return payload

    @staticmethod
    def _normal_slot_dispatch_chat_overlay(run_result) -> Dict[str, Any]:
        for item in reversed(run_result.node_results):
            if not item.success or item.tool_id != "normal_slot_dispatch":
                continue
            out = item.output or {}
            if not isinstance(out, dict) or not out.get("success"):
                continue
            if not (out.get("autoAction") or out.get("task")):
                continue
            picked: Dict[str, Any] = {}
            for key in ("response", "message", "autoAction", "task"):
                if key in out:
                    picked[key] = out[key]
            return picked
        return {}

    def _dispatch_workflow_tool(self, tool_id: str, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from app.routes.tools import execute_registered_workflow_tool

            return execute_registered_workflow_tool(tool_id=tool_id, action=action, params=params)
        except Exception as err:
            logger.error("workflow 工具调度失败 tool=%s action=%s err=%s", tool_id, action, err, exc_info=True)
            return {"success": False, "message": str(err)}

    def _handle_confirmation_flow(
        self,
        user_id: str,
        message: str,
        file_context: Optional[Dict[str, Any]]
    ) -> None:
        """处理确认流程"""
        if not file_context:
            return

        if message not in ("是", "好的", "确认", "yes", "ok", "好"):
            return

        saved_name = file_context.get("saved_name")
        unit_name = file_context.get("unit_name_guess") or file_context.get("unit_name", "")
        suggested_use = file_context.get("suggested_use", "")

        if saved_name and suggested_use == "unit_products_db" and unit_name:
            self.ai_service.set_pending_confirmation(user_id, {
                "type": "import_unit_products",
                "tool_key": "sqlite_import_unit_products",
                "params": {
                    "saved_name": saved_name,
                    "unit_name": unit_name,
                },
                "description": f"导入 {unit_name} 的产品"
            })
            logger.info(f"用户 {user_id} 确认导入文件：{saved_name} -> {unit_name}")

    def _build_response(
        self,
        ai_result: Dict[str, Any],
        source: Optional[str],
        original_message: str = ""
    ) -> Dict[str, Any]:
        """构建响应数据"""
        response_data = {
            "success": True,
            "message": "处理完成",
            "data": {
                "text": ai_result.get("text", ""),
                "action": ai_result.get("action", ""),
                "data": ai_result.get("data", {}) or {},
            },
        }
        response_data["response"] = ai_result.get("text", "")

        action = ai_result.get("action")
        result_data = ai_result.get("data") or {}

        if action == "tool_call" and result_data:
            response_data = self._handle_tool_call(
                response_data, ai_result, result_data, source, original_message
            )
        else:
            if action == "followup":
                response_data["followup"] = result_data
            if action == "auto_action" and result_data:
                response_data["autoAction"] = result_data

        return response_data

    def _handle_tool_call(
        self,
        response_data: Dict[str, Any],
        ai_result: Dict[str, Any],
        result_data: Dict[str, Any],
        source: Optional[str],
        original_message: str = ""
    ) -> Dict[str, Any]:
        """处理工具调用响应"""
        tool_key = result_data.get("tool_key")
        parsed_params = result_data.get("params") or {}
        slots = result_data.get("slots", {})

        if not tool_key:
            response_data["response"] = ai_result.get("text", "")
            response_data["data"]["data"] = result_data.get("data", {}) or {}
            return response_data

        if self._is_pro_source(source):
            response_data = self._execute_pro_mode_tools(
                response_data, tool_key, slots, parsed_params, ai_result, original_message
            )
        else:
            response_data = self._execute_normal_mode_tools(
                response_data, tool_key, parsed_params, ai_result, result_data
            )

        return response_data

    def _execute_pro_mode_tools(
        self,
        response_data: Dict[str, Any],
        tool_key: str,
        slots: Dict[str, Any],
        parsed_params: Dict[str, Any],
        ai_result: Dict[str, Any],
        original_message: str = ""
    ) -> Dict[str, Any]:
        """执行专业模式工具"""
        if tool_key == "products":
            return self._execute_products_query(
                response_data, slots, parsed_params
            )
        elif tool_key == "customers":
            return self._execute_customers_intent(
                response_data=response_data,
                slots=slots,
                parsed_params=parsed_params,
                original_message=original_message,
            )
        elif tool_key == "shipment_generate":
            unit_name = slots.get("unit_name") or parsed_params.get("unit_name", "")
            quantity_tins = slots.get("quantity_tins") or parsed_params.get("quantity_tins", "")
            model_number = slots.get("model_number") or slots.get("product_model") or parsed_params.get("model_number", "")
            tin_spec = slots.get("tin_spec") or parsed_params.get("tin_spec", "")
            products_list = slots.get("products") or []
            parsed_products = []
            parsed_unit_name = ""

            # pro 模式优先从原消息解析整单，保留完整 products[]。
            try:
                from app.routes.tools import _parse_order_text
                parsed_order = _parse_order_text(original_message or "")
                if parsed_order.get("success"):
                    parsed_products = parsed_order.get("products") or []
                    parsed_unit_name = parsed_order.get("unit_name") or ""
            except Exception as parse_err:
                logger.debug("pro shipment_generate 解析原句失败，回退旧逻辑: %s", parse_err)

            if original_message and len(original_message) > 5:
                order_text = original_message
            elif unit_name and quantity_tins and model_number and tin_spec:
                order_text = f"{unit_name}{int(quantity_tins)} 桶 {model_number} 规格 {int(float(tin_spec))}"
            elif unit_name and products_list:
                order_text = self._build_order_text_from_products(unit_name, products_list, original_message, quantity_tins, tin_spec)
            else:
                order_text = ai_result.get("text", "")

            effective_products = parsed_products or products_list
            effective_unit_name = parsed_unit_name or unit_name
            response_data["toolCall"] = {
                "tool_id": tool_key,
                "action": "执行",
                "params": {
                    "order_text": order_text,
                    **parsed_params,
                    **ai_result.get("data", {}),
                    "products": effective_products,
                    "unit_name": effective_unit_name,
                }
            }
            response_data["response"] = ai_result.get("text", "")
            return response_data
        else:
            response_data["toolCall"] = {
                "tool_id": tool_key,
                "action": "执行",
                "params": {
                    "order_text": ai_result.get("text", ""),
                    **parsed_params,
                    **ai_result.get("data", {})
                }
            }
            response_data["response"] = ai_result.get("text", "")
            return response_data

    def _execute_normal_mode_tools(
        self,
        response_data: Dict[str, Any],
        tool_key: str,
        parsed_params: Dict[str, Any],
        ai_result: Dict[str, Any],
        result_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行普通模式工具"""
        if tool_key == "shipment_generate":
            return self._execute_shipment_generate(
                response_data, parsed_params, ai_result
            )
        elif tool_key == "shipments":
            return self._execute_shipments_query(response_data)
        else:
            response_data["toolCall"] = {
                "tool_id": tool_key,
                "action": "执行",
                "params": {
                    "order_text": ai_result.get("text", ""),
                    **parsed_params,
                    **result_data
                }
            }
            response_data["response"] = ai_result.get("text", "")
            return response_data

    def _execute_products_query(
        self,
        response_data: Dict[str, Any],
        slots: Dict[str, Any],
        parsed_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行产品查询"""
        try:
            from app.bootstrap import get_products_service
            from app.infrastructure.lookups.purchase_unit_resolver import resolve_purchase_unit

            unit_name = slots.get("unit_name") or parsed_params.get("unit_name", "")
            model_number = slots.get("model_number") or parsed_params.get("model_number", "")
            keyword = slots.get("keyword") or parsed_params.get("keyword", "")

            if not unit_name and not model_number and keyword and "的" in keyword:
                match = re.search(r'([\u4e00-\u9fa5]{2,6})的(\d+[A-Z]?)', keyword)
                if match:
                    potential_unit = match.group(1)
                    model_candidate = match.group(2)
                    resolved = resolve_purchase_unit(potential_unit)
                    if resolved:
                        unit_name = resolved.unit_name
                    else:
                        unit_name = potential_unit
                    model_number = model_candidate
                    keyword = None

            app_service = get_products_service()

            if model_number and unit_name:
                products_result = app_service.get_products(model_number=model_number, unit_name=unit_name)
            elif model_number:
                products_result = app_service.get_products(model_number=model_number)
            elif unit_name:
                products_result = app_service.get_products(unit_name=unit_name)
            elif keyword:
                products_result = app_service.get_products(keyword=keyword)
            else:
                products_result = app_service.get_products()

            products_list = products_result.get("data", []) if products_result else []

            response_data["data"]["unit_name"] = unit_name
            response_data["data"]["model_number"] = model_number
            response_data["data"]["data"] = {"products": products_list}
            response_data["response"] = f"查询到 {len(products_list)} 个产品" if products_list else "未找到产品"
            response_data["toolCall"] = {
                "tool_id": "products",
                "action": "执行",
                "params": {
                    "unit_name": unit_name,
                    "model_number": model_number,
                    "keyword": keyword
                }
            }
            response_data["autoAction"] = {
                "type": "tool_call",
                "tool_key": "products",
                "params": {
                    "unit_name": unit_name,
                    "model_number": model_number,
                    "keyword": keyword
                },
                "products": products_list,
                "unit_name": unit_name,
                "query": model_number or keyword or ""
            }
        except Exception as prod_err:
            logger.error("即时执行 products 查询失败: %s", prod_err, exc_info=True)
            response_data["response"] = f"查询产品失败：{str(prod_err)}"

        return response_data

    def _execute_customers_query(
        self,
        response_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行客户查询"""
        try:
            from app.bootstrap import get_customer_app_service

            app_service = get_customer_app_service()
            customers_result = app_service.get_all()
            customers = customers_result.get("data", []) if customers_result else []

            response_data["data"]["data"] = {"customers": customers}
            response_data["response"] = f"查询到 {len(customers)} 个购买单位" if customers else "未找到购买单位"
        except Exception as cust_err:
            logger.error("即时执行 customers 查询失败: %s", cust_err, exc_info=True)
            response_data["response"] = f"查询购买单位失败：{str(cust_err)}"

        return response_data

    def _execute_customers_intent(
        self,
        response_data: Dict[str, Any],
        slots: Dict[str, Any],
        parsed_params: Dict[str, Any],
        original_message: str = "",
    ) -> Dict[str, Any]:
        text = str(original_message or "").strip()
        lower = text.lower()
        unit_name = str(
            slots.get("unit_name")
            or parsed_params.get("unit_name")
            or parsed_params.get("customer_name")
            or parsed_params.get("name")
            or ""
        ).strip()

        is_add_intent = any(k in text for k in ("添加", "新增", "新建", "创建")) or any(
            k in lower for k in ("add", "create", "new")
        )
        is_query_intent = any(k in text for k in ("查询", "查", "列表", "全部")) or any(
            k in lower for k in ("query", "search", "list")
        )

        if is_add_intent and not unit_name:
            response_data["response"] = "你要添加哪个单位？请告诉我单位名称，例如：添加单位 七彩乐园。"
            response_data["data"]["data"] = {
                "intent": "customer_create",
                "missing_fields": ["unit_name"],
            }
            return response_data

        if is_add_intent and unit_name:
            try:
                from app.routes.tools import execute_registered_workflow_tool

                created = execute_registered_workflow_tool(
                    tool_id="customers",
                    action="ensure_exists",
                    params={"unit_name": unit_name},
                )
                if created.get("success"):
                    if created.get("created"):
                        response_data["response"] = f"单位已创建：{unit_name}"
                    else:
                        response_data["response"] = f"单位已存在：{unit_name}"
                    response_data["data"]["data"] = created
                    return response_data
                response_data["response"] = created.get("message", "处理单位失败")
                return response_data
            except Exception as err:
                logger.error("customers 添加意图执行失败: %s", err, exc_info=True)
                response_data["response"] = f"处理单位失败：{str(err)}"
                return response_data

        if is_query_intent:
            return self._execute_customers_query(response_data)

        # 未明确意图时，不再默认查全表，避免“添加单位”误触发列表查询
        response_data["response"] = (
            "我可以帮你处理单位管理。你可以说："
            "“添加单位 七彩乐园”或“查询购买单位列表”。"
        )
        response_data["data"]["data"] = {"intent": "customers_followup"}
        return response_data

    def _build_order_text_from_products(self, unit_name: str, products: list, original_message: str = "", default_qty: int = None, default_spec: int = None) -> str:
        """根据产品列表构建订单文本"""
        import re
        if not products:
            return ""
        if not unit_name:
            return ""

        if original_message and len(products) >= 1:
            normalized_msg = original_message.replace('，', ',').replace('。', '').replace(' ', '')
            order_pattern = re.compile(r'帮?打\s*(.+?)\s*的?\s*货单?[,，]?\s*(\d+)\s*桶\s*(\d+[A-Z]?(?:-\d+[A-Z]?)?)\s*规格\s*(\d+)\s*[,，]?\s*(\d+)\s*桶\s*(\d+[A-Z]?(?:-\d+[A-Z]?)?)\s*规格\s*(\d+)')
            matches = list(order_pattern.finditer(normalized_msg))

            if len(matches) >= 1:
                m = matches[0]
                found_unit = m.group(1)
                if len(m.groups()) >= 7:
                    order_parts = []
                    for i in range(1, len(m.groups()), 4):
                        if i + 3 <= len(m.groups()):
                            qty = int(m.group(i + 1))
                            model = m.group(i + 2)
                            spec = int(m.group(i + 3))
                            order_parts.append(f"{qty}桶{model}规格{spec}")
                    if order_parts and found_unit:
                        return found_unit + "，" + "，".join(order_parts)
                else:
                    order_parts = []
                    for m in matches:
                        qty = int(m.group(2))
                        model = m.group(3)
                        spec = int(m.group(4))
                        order_parts.append(f"{qty}桶{model}规格{spec}")
                    if order_parts and found_unit:
                        return found_unit + "，" + "，".join(order_parts)

        parts = []
        total_qty = default_qty or 0
        for p in products:
            model = p.get("model") or p.get("model_number") or p.get("name") or ""
            qty = p.get("quantity_tins") or p.get("quantity") or p.get("qty") or 1
            spec = p.get("spec") or p.get("tin_spec") or p.get("规格") or default_spec or 25
            if model:
                parts.append(f"{int(qty)}桶{model}规格{int(float(spec))}")
            else:
                parts.append(f"{int(qty)}桶规格{int(float(spec))}")
        return unit_name + "，" + "，".join(parts)

    def _try_merge_split_model(self, text: str, product_template: dict) -> str:
        """尝试合并被拆分的型号（如 5003-2737B 被拆成 5003 和 2737B）"""
        import re
        qty = product_template.get("quantity_tins") or 1
        spec = product_template.get("spec") or product_template.get("tin_spec") or 25

        number_pattern = r'(\d+)([A-Z]?)\s*规格\s*(\d+)'
        m = re.search(number_pattern, text)
        if m:
            model = m.group(1) + m.group(2)
            spec_val = int(m.group(3))
            return f"{int(qty)}桶{model}规格{spec_val}"

        number_pattern2 = r'(\d+)\s*桶\s*(\d+)([A-Z]?)\s*规格\s*(\d+)'
        m2 = re.search(number_pattern2, text)
        if m2:
            qty_val = int(m2.group(1))
            model = m2.group(2) + m2.group(3)
            spec_val = int(m2.group(4))
            return f"{qty_val}桶{model}规格{spec_val}"

        return ""

    def _execute_shipment_generate(
        self,
        response_data: Dict[str, Any],
        parsed_params: Dict[str, Any],
        ai_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行发货单生成"""
        try:
            from app.bootstrap import get_shipment_app_service
            from app.routes.tools import _parse_order_text

            order_text = parsed_params.get("order_text") or ai_result.get("text", "")
            parsed = _parse_order_text(order_text)

            if parsed.get("success"):
                app_service = get_shipment_app_service()
                doc_result = app_service.generate_shipment_document(
                    unit_name=parsed.get("unit_name", ""),
                    products=parsed.get("products") or [],
                    template_name=None,
                )
                response_data["data"]["data"] = {"document": doc_result}

                if doc_result.get("success"):
                    doc_name = doc_result.get("doc_name") or ""
                    response_data["response"] = f"已生成发货单：{doc_name}" if doc_name else "已生成发货单。"
                else:
                    response_data["response"] = doc_result.get("message", "生成发货单失败")
            else:
                response_data["response"] = parsed.get("message", "订单解析失败")
        except Exception as tool_err:
            logger.error("自动执行 shipment_generate 失败: %s", tool_err, exc_info=True)
            response_data["response"] = f"生成发货单失败：{str(tool_err)}"

        return response_data

    def _execute_shipments_query(
        self,
        response_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行发货记录查询"""
        try:
            from app.bootstrap import get_shipment_app_service

            app_service = get_shipment_app_service()
            orders = app_service.get_orders(10) or []

            lines = ["最新出货/订单记录（最近 10 条）："]
            if not orders:
                lines.append("暂无订单记录。")
            else:
                for o in orders[:10]:
                    order_no = o.get("order_number") or o.get("order_no") or o.get("id") or ""
                    customer = o.get("customer_name") or o.get("unit_name") or o.get("purchase_unit") or ""
                    date = o.get("date") or o.get("created_at") or ""
                    amount = o.get("total_amount") or o.get("total_amount_yuan") or o.get("amount") or 0
                    status = o.get("status") or "已完成"
                    lines.append(f"- {order_no} | {customer} | {date} | ¥{amount} | {status}")

            response_data["response"] = "\n".join(lines)
            response_data["data"]["data"] = {"orders": orders}
            response_data.pop("toolCall", None)
        except Exception as tool_err:
            logger.error("即时执行 shipments 失败：%s", tool_err, exc_info=True)

        return response_data


_ai_chat_app_service_instance = None


def get_ai_chat_app_service() -> AIChatApplicationService:
    """获取 AI 聊天应用服务单例"""
    global _ai_chat_app_service_instance
    if _ai_chat_app_service_instance is None:
        _ai_chat_app_service_instance = AIChatApplicationService()
    return _ai_chat_app_service_instance
