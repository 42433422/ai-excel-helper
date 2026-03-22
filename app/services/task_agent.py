# -*- coding: utf-8 -*-
"""
结构化任务代理：解析任务 -> 校验字段 -> 追问/执行编排。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .task_context_service import get_task_context_service

SLOT_LABELS = {
    "unit_name": "单位名称",
    "model_number": "编号/型号",
    "tin_spec": "规格",
    "quantity_tins": "桶数",
    "keyword": "关键词",
    "customer_name": "客户名称",
}


def _cn_number(token: str) -> Optional[int]:
    t = (token or "").strip()
    if not t:
        return None
    if re.fullmatch(r"\d+", t):
        return int(t)
    m = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    if t == "十":
        return 10
    if re.fullmatch(r"[一二两三四五六七八九]十", t):
        return m[t[0]] * 10
    if re.fullmatch(r"十[一二三四五六七八九]", t):
        return 10 + m[t[1]]
    if re.fullmatch(r"[一二两三四五六七八九]十[一二三四五六七八九]", t):
        return m[t[0]] * 10 + m[t[2]]
    if len(t) == 1 and t in m:
        return m[t]
    return None


class TaskAgent:
    def __init__(self) -> None:
        self.ctx = get_task_context_service()

    def parse_task(self, message: str, context: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        msg = (message or "").strip()
        context = context or {}

        user_id = context.get("user_id") or ""

        # 1) 多轮补齐：已有未完成任务时，吸收增量输入
        pending = self.ctx.get(user_id) if user_id else None
        if pending and pending.get("task_type") == "shipment_generate":
            slots = dict(pending.get("slots") or {})
            qty = re.search(r"(?:改成|改为)?\s*(\d+|[一二三四五六七八九十零〇两]+)\s*桶", msg)
            if qty:
                n = _cn_number(qty.group(1))
                if n:
                    slots["quantity_tins"] = n
                    return {"task_type": "shipment_generate", "slots": slots, "source": "followup"}
        if pending and pending.get("task_type") in ("product_query", "customer_query"):
            slots = dict(pending.get("slots") or {})
            keyword = self._extract_query_keyword(msg)
            if keyword:
                slots["keyword"] = keyword
                return {"task_type": pending.get("task_type"), "slots": slots, "source": "followup"}

        # 2) 补充客户信息意图检测（他/她/它的 + 联系人/电话/地址/补充 + 信息）
        supplement_patterns = [
            r"^(他|她|它)\s*的?\s*(联系人|联系电话|电话|手机|手机号|联系号码|地址|联系地址)\s*(?:是|：|:)?\s*(.{1,30})$",
            r"^(他|她|它)\s*的?\s*(补充)\s*(.{1,30})$",
            r"补充\s*(他|她|它)\s*的?\s*(联系人|联系电话|电话|手机|地址)\s*(?:是|：|:)?\s*(.{1,30})$",
        ]
        for pattern in supplement_patterns:
            m = re.search(pattern, msg)
            if m:
                groups = m.groups()
                if len(groups) >= 3:
                    field_name = groups[1]
                    field_value = groups[2].strip()
                    field_map = {
                        "联系人": "contact_person",
                        "联系电话": "contact_phone",
                        "电话": "contact_phone",
                        "手机": "contact_phone",
                        "手机号": "contact_phone",
                        "联系号码": "contact_phone",
                        "地址": "contact_address",
                        "联系地址": "contact_address",
                    }
                    if field_name in field_map:
                        return {
                            "task_type": "customer_supplement",
                            "slots": {
                                "field_name": field_map[field_name],
                                "field_value": field_value,
                                "reference_type": groups[0],
                            },
                            "source": "supplement_intent",
                        }

        # 3) 发货/打印任务
        order_action = any(k in msg for k in ["打印", "发货单", "送货单", "出货单", "开单", "打单"])
        order_signal = any(k in msg for k in ["编号", "型号", "规格", "桶"])
        # 只要明显是发货单语境，就进入结构化审查；有槽位就抽取，缺项就追问
        if order_action and (order_signal or any(k in msg for k in ["发货单", "送货单", "出货单"])):
            slots: Dict[str, Any] = {}
            spec_span_end = -1
            m_model = re.search(r"(?:编号|型号)\s*[:：]?\s*(\d{3,6})", msg) or re.search(r"(\d{3,6})\s*(?:的)?\s*规格", msg)
            if m_model:
                slots["model_number"] = m_model.group(1)
            m_spec_ar = re.search(r"规格\s*[:：]?\s*(\d+(?:\.\d+)?)", msg)
            m_spec_cn = re.search(
                r"规格\s*[:：]?\s*([一二两三四五六七八九十零〇]{1,4})(?=(?:[两一二三四五六七八九十零〇]{1,3}\s*桶)|[，,。\s]|一共|总共|共|$)",
                msg,
            )
            if m_spec_ar:
                slots["tin_spec"] = float(m_spec_ar.group(1))
                spec_span_end = m_spec_ar.span()[1]
            elif m_spec_cn:
                spec_token = m_spec_cn.group(1)
                # 兼容“规格二十八一共三桶”这种连读，去掉被吞进来的“共”前缀“一”
                if spec_token.endswith("一"):
                    suffix = msg[m_spec_cn.end(1): m_spec_cn.end(1) + 1]
                    if suffix == "共":
                        spec_token = spec_token[:-1]
                n = _cn_number(spec_token)
                if n is not None:
                    slots["tin_spec"] = float(n)
                    spec_span_end = m_spec_cn.span()[1]
            m_qty = re.search(r"(?:一共|总共|共|要|来|拿)?\s*(\d+|[一二三四五六七八九十零〇两]+)\s*桶", msg)
            qty_value = None
            if m_qty:
                n = self._parse_qty_token(m_qty.group(1))
                if n:
                    qty_value = int(n)
            if qty_value is None and spec_span_end > 0:
                tail = msg[spec_span_end:]
                m_qty_tail = re.search(r"\s*(\d+|[一二三四五六七八九十零〇两]{1,3})\s*桶", tail)
                if m_qty_tail:
                    n2 = self._parse_qty_token(m_qty_tail.group(1))
                    if n2:
                        qty_value = int(n2)
            if qty_value is not None:
                slots["quantity_tins"] = qty_value
            m_unit = re.search(r"打印(?:一下)?\s*([^，,。]+?)\s*(?:的)?\s*(?:发货单|送货单|出货单)", msg) or re.search(r"([^，,。]+?)\s*(?:的)?\s*(?:发货单|送货单|出货单)", msg)
            unit = ""
            if m_unit:
                unit = m_unit.group(1).strip()
                unit = re.sub(r"^(哎|嗯|啊|呃)\s*", "", unit)
                unit = re.sub(r"^(帮我|给我|请)\s*", "", unit)
                unit = unit.strip()
            if not unit and "发货单" in msg:
                # 兼容“发货单七彩乐园9803规格12要3桶”这类无“打印XX发货单”的语序
                unit_part = msg.split("发货单", 1)[1]
                unit_part = re.sub(r"(?:编号|型号)\s*[:：]?\s*\d{3,6}", " ", unit_part)
                unit_part = re.sub(r"\d{3,6}\s*(?:的)?\s*规格", " ", unit_part)
                unit_part = re.sub(r"规格\s*[:：]?\s*(?:\d+(?:\.\d+)?|[一二两三四五六七八九十零〇]+)", " ", unit_part)
                unit_part = re.sub(r"(?:一共|总共|共|要|来|拿)?\s*(?:\d+|[一二三四五六七八九十零〇两]+)\s*桶", " ", unit_part)
                unit_part = re.sub(r"\d{3,6}", " ", unit_part)
                unit_part = re.sub(r"[，,。；;\s]+", "", unit_part).strip()
                unit = unit_part
            if unit:
                slots["unit_name"] = unit
            return {"task_type": "shipment_generate", "slots": slots, "source": "nlu"}

        # 3) 其他任务（全工作模式基础覆盖）
        if any(k in msg for k in ["产品", "型号", "产品库", "查产品", "搜产品"]):
            return {"task_type": "product_query", "slots": self._extract_product_query_slots(msg), "source": "nlu"}
        if any(k in msg for k in ["客户", "购买单位", "单位列表", "查客户", "搜客户"]):
            return {"task_type": "customer_query", "slots": self._extract_customer_query_slots(msg), "source": "nlu"}
        if "打印机" in msg and any(k in msg for k in ["默认", "设置"]):
            return {"task_type": "print_config", "slots": {}, "source": "nlu"}

        return None

    def validate_slots(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        task_type = plan.get("task_type")
        slots = plan.get("slots") or {}
        missing: List[str] = []
        if task_type == "shipment_generate":
            for key in ["unit_name", "model_number", "tin_spec", "quantity_tins"]:
                if not slots.get(key):
                    missing.append(key)
        if task_type in ("product_query", "customer_query"):
            if not slots.get("keyword"):
                missing.append("keyword")
        if task_type == "customer_supplement":
            for key in ["field_name", "field_value"]:
                if not slots.get(key):
                    missing.append(key)
        return {"ok": len(missing) == 0, "missing_slots": missing}

    def build_followup(self, plan: Dict[str, Any], missing_slots: List[str]) -> str:
        if plan.get("task_type") != "shipment_generate":
            task_type = plan.get("task_type")
            if task_type == "product_query":
                return "你要查哪个产品？请说产品名、型号或规格关键词。"
            if task_type == "customer_query":
                return "你要查哪个客户/购买单位？请说名称关键词。"
            if task_type == "customer_supplement":
                return "请告诉我要补充什么信息，比如：他的联系人是谁。"
            return "请补充必要参数。"
        # 先审查整句，再按缺失槽位给出自然语言追问
        if missing_slots == ["quantity_tins"]:
            return "我这边看了一下，问一下这次需要多少桶呢？"
        if missing_slots == ["tin_spec"]:
            return "我这边看了一下，问一下规格是多少呢？"
        if missing_slots == ["model_number"]:
            return "我这边看了一下，编号好像还没有呢，问一下是多少？"
        if missing_slots == ["unit_name"]:
            return "我这边看了一下，购买单位还没有呢，问一下是哪一家？"
        question_map = {
            "quantity_tins": "多少桶呢",
            "model_number": "编号好像还没有呢，问一下是多少",
            "tin_spec": "规格是多少呢",
            "unit_name": "购买单位是哪一家呢",
        }
        ordered_keys = ["unit_name", "model_number", "tin_spec", "quantity_tins"]
        questions = [question_map[k] for k in ordered_keys if k in missing_slots and k in question_map]
        if questions:
            return "我先帮你审查了一下这句话，麻烦确认一下：" + "，".join(questions) + "。"
        zh_slots = [SLOT_LABELS.get(slot, slot) for slot in missing_slots]
        return "我先帮你审查了一下这句话，请补充：" + "、".join(zh_slots)

    def execute_plan(self, plan: Dict[str, Any], original_message: str = "") -> Dict[str, Any]:
        task_type = plan.get("task_type")
        slots = plan.get("slots") or {}
        if task_type == "shipment_generate":
            # 只有在所有必要槽位都存在时才构建 order_text
            unit_name = slots.get('unit_name', '')
            quantity_tins = slots.get('quantity_tins', 0)
            model_number = slots.get('model_number', '')
            tin_spec = slots.get('tin_spec', 0)
            
            # 验证槽位有效性
            if not unit_name or not quantity_tins or not model_number or not tin_spec:
                # 槽位不完整，返回错误消息而不是生成无效的 order_text
                return {
                    "tool_key": "shipment_generate",
                    "intent": "shipment_generate",
                    "params": {"order_text": ""},
                    "error": "槽位信息不完整，无法生成订单文本",
                    "missing_slots": {
                        "unit_name": not unit_name,
                        "quantity_tins": not quantity_tins,
                        "model_number": not model_number,
                        "tin_spec": not tin_spec,
                    }
                }
            
            order_text = f"{unit_name}{int(quantity_tins)} 桶 {model_number} 规格 {int(float(tin_spec))}"
            return {
                "tool_key": "shipment_generate",
                "intent": "shipment_generate",
                "params": {"order_text": order_text},
            }
        if task_type == "product_query":
            return {
                "tool_key": "products",
                "intent": "products",
                "params": {
                    "action": "search",
                    "keyword": slots.get("keyword", ""),
                    "model_number": slots.get("model_number", ""),
                    "tin_spec": slots.get("tin_spec", ""),
                    "unit_name": slots.get("unit_name", ""),
                },
            }
        if task_type == "customer_query":
            return {
                "tool_key": "customers",
                "intent": "customers",
                "params": {
                    "action": "search",
                    "keyword": slots.get("keyword", ""),
                    "customer_name": slots.get("customer_name", ""),
                },
            }
        if task_type == "print_config":
            return {"tool_key": "system", "intent": "system", "params": {}}
        if task_type == "customer_supplement":
            return {
                "tool_key": "customers",
                "intent": "customer_supplement",
                "params": {
                    "action": "supplement",
                    "field_name": slots.get("field_name", ""),
                    "field_value": slots.get("field_value", ""),
                },
            }
        return {"tool_key": None, "intent": None, "params": {}}

    def process_message(self, user_id: str, message: str) -> Optional[Dict[str, Any]]:
        plan = self.parse_task(message, {"user_id": user_id})
        if not plan:
            return None
        check = self.validate_slots(plan)
        if not check["ok"]:
            self.ctx.set(user_id, plan)
            return {
                "action": "followup",
                "text": self.build_followup(plan, check["missing_slots"]),
                "data": {"task_type": plan.get("task_type"), "missing_slots": check["missing_slots"]},
            }
        # 完整可执行则清理上下文并返回 tool_call
        self.ctx.clear(user_id)
        exec_data = self.execute_plan(plan, message)
        if exec_data.get("tool_key"):
            return {"action": "tool_call", "text": f"正在处理工具调用：{exec_data['tool_key']}", "data": exec_data}
        return None

    @staticmethod
    def _extract_query_keyword(msg: str) -> str:
        text = (msg or "").strip()
        text = re.sub(r"^(那就|那|就|改成|改为|帮我|给我|请)\s*", "", text)
        for pattern in [
            r"(?:查|查询|搜索|找|看)\s*(?:一下)?\s*(.+)$",
            r"(?:产品|客户|购买单位)\s*(?:是|叫|名称是)?\s*(.+)$",
        ]:
            m = re.search(pattern, text)
            if m:
                kw = m.group(1).strip(" ，,。")
                if kw in {"产品", "产品列表", "客户", "客户列表", "购买单位", "单位列表"}:
                    return ""
                if kw:
                    return kw
        if len(text) <= 24 and not any(x in text for x in ["产品", "客户", "购买单位"]):
            return text.strip(" ，,。")
        generic_phrases = [
            "产品", "产品列表", "查产品", "查询产品", "看看产品", "看产品",
            "客户", "客户列表", "购买单位", "单位列表", "查客户", "查询客户", "看客户",
        ]
        if text in generic_phrases:
            return ""
        return ""

    def _extract_product_query_slots(self, msg: str) -> Dict[str, Any]:
        slots: Dict[str, Any] = {}
        model = re.search(r"(?:编号|型号)\s*[:：]?\s*(\d{3,8})", msg)
        if model:
            slots["model_number"] = model.group(1)
        spec_num = re.search(r"规格\s*[:：]?\s*(\d+(?:\.\d+)?)", msg)
        spec_cn = re.search(r"规格\s*[:：]?\s*([一二两三四五六七八九十零〇]{1,4})", msg)
        if spec_num:
            slots["tin_spec"] = spec_num.group(1)
        elif spec_cn:
            n = _cn_number(spec_cn.group(1))
            if n is not None:
                slots["tin_spec"] = str(n)
        m_unit_product = re.search(r"([^\s，,。]{2,20})\s*的\s*(\d{3,8})", msg)
        if m_unit_product:
            slots["unit_name"] = m_unit_product.group(1).strip()
            slots["model_number"] = m_unit_product.group(2)
        keyword = self._extract_query_keyword(msg)
        if not keyword:
            if slots.get("model_number") and slots.get("tin_spec"):
                keyword = f"{slots['model_number']} 规格{slots['tin_spec']}"
            elif slots.get("model_number"):
                keyword = slots["model_number"]
            elif slots.get("tin_spec"):
                keyword = f"规格{slots['tin_spec']}"
        if keyword:
            slots["keyword"] = keyword
        return slots

    def _extract_customer_query_slots(self, msg: str) -> Dict[str, Any]:
        slots: Dict[str, Any] = {}
        keyword = self._extract_query_keyword(msg)
        m_name = re.search(r"(?:客户|购买单位|单位)\s*(?:是|叫|名称是)?\s*([^\s，,。]{2,30})", msg)
        if m_name:
            slots["customer_name"] = m_name.group(1).strip()
            if not keyword:
                keyword = slots["customer_name"]
        if keyword:
            slots["keyword"] = keyword
        return slots

    @staticmethod
    def _parse_qty_token(token: str) -> Optional[int]:
        t = (token or "").strip()
        n = _cn_number(t)
        if n is not None:
            return n
        # 兼容“二十八两桶”这类口语粘连，回退到末尾 1~3 位中文数词
        if re.fullmatch(r"[一二三四五六七八九十零〇两]+", t):
            for size in (1, 2, 3):
                if len(t) >= size:
                    n2 = _cn_number(t[-size:])
                    if n2 is not None:
                        return n2
        return None


_task_agent: Optional[TaskAgent] = None


def get_task_agent() -> TaskAgent:
    global _task_agent
    if _task_agent is None:
        _task_agent = TaskAgent()
    return _task_agent

