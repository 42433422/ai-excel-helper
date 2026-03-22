# -*- coding: utf-8 -*-
"""
全流程意图层 v2 - 基于规则引擎

统一意图定义、否定检测、问候/再见/模糊判断，供 AI 对话系统使用。
支持从配置文件加载意图规则，热更新无需重启服务。

流程：
1. 问候/再见 -> 直接回复，不进入工具
2. 否定式指令 -> 不触发对应工具，走 AI 或友好提示
3. 工具意图 -> 关键词匹配 + 优先级，考虑否定
4. 仅模板查询 -> intent_hints 兜底模板直答
5. 模糊/短句/未知 -> 走 AI 兜底或引导

本模块现在委托给 domain.services.intent 下的策略类处理具体检测逻辑
"""

import hashlib
import re
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from app.domain.services.intent import get_intent_coordinator
from app.services.rule_engine import get_rule_engine, reload_rule_engine
from app.utils.cache_manager import get_intent_rule_cache
from resources.config.intent_config import get_intent_config, reload_intent_config

_intent_cache = get_intent_rule_cache()

_coordinator = get_intent_coordinator()


def _make_intent_cache_key(message: str) -> str:
    return hashlib.md5(message.strip().lower().encode()).hexdigest()


def _normalize(msg: Optional[str]) -> str:
    """标准化消息字符串"""
    if not isinstance(msg, str):
        return ""
    return (msg or "").strip()


def reload_intent_service() -> None:
    """重新加载意图服务（热更新）"""
    global _intent_cache
    _intent_cache.clear()
    reload_intent_config()
    reload_rule_engine()


def is_negation(message: str, action_keywords: Optional[List[str]] = None) -> bool:
    """判断是否为否定式指令"""
    return _coordinator.detect_negation(message, action_keywords)


def is_greeting(message: str) -> bool:
    """判断是否为问候语"""
    return _coordinator.detect_greeting(message)


def is_goodbye(message: str) -> bool:
    """判断是否为告别语"""
    return _coordinator.detect_goodbye(message)


def is_help_request(message: str) -> bool:
    """判断是否为帮助请求"""
    return _coordinator.detect_help(message)


def is_confirmation(message: str) -> bool:
    """判断是否为确认意图"""
    return _coordinator.detect_confirmation(message)


def is_negation_intent(message: str) -> bool:
    """判断是否为否定意图"""
    return _coordinator.detect_negation_intent(message)


QUICK_COMMAND_MAP = {
    "开单": "shipment_generate",
    "开发货单": "shipment_generate",
    "生成发货单": "shipment_generate",
    "打单": "shipment_generate",
    "查产品": "products",
    "产品列表": "products",
    "查客户": "customers",
    "客户列表": "customers",
    "发货单模板": "shipment_template",
    "当前模板": "shipment_template",
    "出货记录": "shipments",
    "发货记录": "shipments",
    "发微信": "wechat_send",
    "发送微信": "wechat_send",
    "打印标签": "print_label",
    "打印": "print_label",
    "上传": "upload_file",
    "导入": "upload_file",
    "导出": "upload_file",
    "材料": "materials",
    "原材料": "materials",
    "库存": "materials",
    "分解": "excel_decompose",
    "分解excel": "excel_decompose",
}

QUICK_INTENT_PATTERNS = [
    (r"^发货单[^\s]{2,10}\s*\d+[桶箱件个]", "shipment_generate"),
    (r"^送货单[^\s]{2,10}\s*\d+[桶箱件个]", "shipment_generate"),
    (r"^出货单[^\s]{2,10}\s*\d+[桶箱件个]", "shipment_generate"),
    (r"发货单.*桶.*规格", "shipment_generate"),
    (r"开单.*[一二三四五六七八九十零〇\d]+.*桶", "shipment_generate"),
    (r"打印.*\d+.*规格", "shipment_generate"),
]

_CONTEXT_INHERIT_PATTERNS = [
    (r"^再[一1]份$", "repeat_last"),
    (r"^再.*[一1]份$", "repeat_last"),
    (r"^同样$", "repeat_last"),
    (r"^一样$", "repeat_last"),
    (r"^按上次的$", "repeat_last"),
    (r"^和上次一样$", "repeat_last"),
]

_APPEND_KEYWORDS = [
    "再加", "还要", "再加1", "再来", "继续加", "再补",
    "追加", "额外", "加上"
]


def recognize_intents(message: str) -> Dict[str, Any]:
    """
    全流程意图识别入口

    Returns:
        意图识别结果字典，包含：
        - primary_intent: 主意图 id
        - tool_key: 建议触发的工具 key
        - intent_hints: 用于上下文的 hint 列表
        - is_negated: 是否判定为否定式
        - is_greeting: 是否问候
        - is_goodbye: 是否再见
        - is_help: 是否帮助请求
        - is_likely_unclear: 短句且无任何意图匹配
        - all_matched_tools: 所有匹配到的 (intent_id, tool_key) 列表
    """
    msg = _normalize(message)
    msg_lower = (msg or "").lower()

    cache_key = _make_intent_cache_key(message)
    cached_result = _intent_cache.get(cache_key)
    if cached_result is not None:
        return cached_result

    result = {
        "primary_intent": None,
        "tool_key": None,
        "intent_hints": [],
        "is_negated": False,
        "is_greeting": False,
        "is_goodbye": False,
        "is_help": False,
        "is_confirmation": False,
        "is_negation_intent": False,
        "is_likely_unclear": False,
        "all_matched_tools": [],
    }

    basic_intents = _coordinator.detect_basic_intents(message)
    result.update(basic_intents)

    engine = get_rule_engine()

    tool_matches = engine.match_intents(msg)
    result["all_matched_tools"] = [(m["id"], m["tool_key"]) for m in tool_matches]

    if tool_matches:
        best = tool_matches[0]
        intent_id = best["id"]
        tool_key = best["tool_key"]
        block_if_negated = best["block_if_negated"]

        result["primary_intent"] = intent_id

        negated = is_negation(message, action_keywords=best.get("keywords")) if block_if_negated else False
        result["is_negated"] = negated

        if not negated:
            result["tool_key"] = tool_key

        if intent_id == "shipment_generate":
            result["intent_hints"].append("shipment_generate")
        elif intent_id == "shipment_template":
            if "template_query" not in result["intent_hints"]:
                result["intent_hints"].append("template_query")

        if "upload_file" in (m["tool_key"] for m in tool_matches):
            if "upload_file" not in result["intent_hints"]:
                result["intent_hints"].append("upload_file")

    hint_matches = engine.match_hint_intents(msg)
    for h in hint_matches:
        if h not in result["intent_hints"]:
            result["intent_hints"].append(h)

    if ("模板" in msg or "template" in msg_lower) and "template_query" not in result["intent_hints"]:
        result["intent_hints"].append("template_query")

    if ("生成发货单" in msg or "开发货单" in msg) and "shipment_generate" not in result["intent_hints"]:
        result["intent_hints"].append("shipment_generate")

    if (msg.startswith("发货单") or msg.startswith("送货单") or msg.startswith("出货单")) and len(msg) > 5:
        order_patterns = ["桶", "规格", "公斤", "kg", "件", "箱"]
        has_order_info = any(pattern in msg for pattern in order_patterns)
        if has_order_info and not result["tool_key"]:
            result["primary_intent"] = "shipment_generate"
            result["tool_key"] = "shipment_generate"
            if "shipment_generate" not in result["intent_hints"]:
                result["intent_hints"].append("shipment_generate")

    if result["tool_key"] in (None, "products", "shipments"):
        has_container_and_spec = ("桶" in msg and "规格" in msg)
        has_number_like = re.search(r"(\d+|[一二三四五六七八九十零〇两]+)", msg) is not None
        if has_container_and_spec and has_number_like:
            negated = is_negation(message, action_keywords=[
                "生成发货单", "发货单生成", "做发货单", "开发货单",
                "开单", "打单", "开送货单", "做出货单", "生成出货单",
            ])
            if not negated:
                result["primary_intent"] = "shipment_generate"
                result["tool_key"] = "shipment_generate"
                if "shipment_generate" not in result["intent_hints"]:
                    result["intent_hints"].append("shipment_generate")

    if result["tool_key"] == "products":
        has_print_kw = ("打印" in msg) or msg.startswith("打印")
        has_model_spec = re.search(r"(\d+)\s*规格\s*(\d+(?:\.\d+)?)", msg) is not None or re.search(r"(\d+)\s*的\s*规格\s*(\d+(?:\.\d+)?)", msg) is not None
        has_container_qty = any(k in msg for k in ["桶", "箱", "件", "公斤", "kg"])
        if has_print_kw and has_model_spec and not has_container_qty and not result["is_negated"]:
            negated = is_negation(message, action_keywords=[
                "生成发货单", "发货单生成", "做发货单", "开发货单",
                "开单", "打单", "开送货单", "做出货单", "生成出货单",
            ])
            if not negated:
                result["primary_intent"] = "shipment_generate"
                result["tool_key"] = "shipment_generate"
                if "shipment_generate" not in result["intent_hints"]:
                    result["intent_hints"].append("shipment_generate")

    if result["tool_key"] is None:
        has_order_action = any(k in msg for k in ["打印", "发货单", "送货单", "出货单", "开单", "打单"])
        signals = 0
        if ("编号" in msg or "型号" in msg) and re.search(r"\d{3,6}", msg):
            signals += 1
        if "规格" in msg and re.search(r"(\d+|[一二三四五六七八九十零〇两]+)", msg):
            signals += 1
        if "桶" in msg and re.search(r"(\d+|[一二三四五六七八九十零〇两]+)\s*桶|桶\s*(\d+|[一二三四五六七八九十零〇两]+)", msg):
            signals += 1
        if has_order_action and signals >= 2 and not result["is_negated"]:
            if not is_negation(message, action_keywords=[
                "生成发货单", "发货单生成", "做发货单", "开发货单",
                "开单", "打单", "开送货单", "做出货单", "生成出货单",
            ]):
                result["primary_intent"] = "shipment_generate"
                result["tool_key"] = "shipment_generate"
                if "shipment_generate" not in result["intent_hints"]:
                    result["intent_hints"].append("shipment_generate")

    if ("上传" in msg or "导入" in msg or "upload" in msg_lower) and "upload_file" not in result["intent_hints"]:
        result["intent_hints"].append("upload_file")

    result["is_likely_unclear"] = (
        len(msg) <= 4
        and not result["is_greeting"]
        and not result["is_goodbye"]
        and not result["primary_intent"]
        and not result["intent_hints"]
    )

    unit_model_match = re.search(r'([^\s的]{2,10})的(\d+[A-Z]?)', msg)
    if unit_model_match:
        potential_unit = unit_model_match.group(1)
        model = unit_model_match.group(2)
        from app.infrastructure.lookups.purchase_unit_resolver import resolve_purchase_unit
        resolved = resolve_purchase_unit(potential_unit)
        if resolved:
            result["slots"] = {
                "unit_name": resolved.unit_name,
                "model_number": model
            }
        else:
            result["slots"] = {
                "unit_name": potential_unit,
                "model_number": model
            }
        if result["tool_key"] is None and not result["primary_intent"] and not result["is_greeting"] and not result["is_goodbye"] and not result["is_help"]:
            result["primary_intent"] = "products"
            result["tool_key"] = "products"
    elif result["tool_key"] == "products":
        result["slots"] = {"keyword": msg}
    else:
        result["slots"] = {}

    _intent_cache.set(cache_key, result)
    return result


def get_tool_key_with_negation_check(message: str) -> Optional[str]:
    """对外接口：在考虑否定后，返回应触发的 tool_key"""
    r = recognize_intents(message)
    return r.get("tool_key")


_MULTI_UNIT_PATTERN = r'([^\s，,、和]+)(?:[和、,]([^\s，,、]+))+'
_MULTI_UNIT_SEPARATORS = ["和", "、", ",", "，"]


def quick_recognize(
    message: str,
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    快速意图识别通道

    流程：
    1. 快捷命令匹配 -> 直接返回
    2. 明确意图关键词匹配 -> 快速返回
    3. 上下文继承检测 -> 使用上下文意图
    4. 不匹配 -> 返回 None（走完整识别）

    Args:
        message: 用户消息
        context: 对话上下文

    Returns:
        快速识别结果
    """
    import time
    start_time = time.time()

    msg = _normalize(message)
    msg_lower = msg.lower()

    result = {
        "fast_path": True,
        "primary_intent": None,
        "tool_key": None,
        "slots": {},
        "context_inherited": False,
        "source": "quick_recognize",
        "elapsed_ms": 0,
    }

    if not msg:
        result["elapsed_ms"] = round((time.time() - start_time) * 1000, 2)
        return result

    for cmd, intent in QUICK_COMMAND_MAP.items():
        if msg == cmd or msg_lower == cmd.lower():
            result["primary_intent"] = intent
            result["tool_key"] = intent
            result["source"] = "quick_command"
            result["elapsed_ms"] = round((time.time() - start_time) * 1000, 2)
            return result

    for pattern, intent in QUICK_INTENT_PATTERNS:
        if re.search(pattern, msg):
            result["primary_intent"] = intent
            result["tool_key"] = intent
            result["source"] = "quick_pattern"
            result["elapsed_ms"] = round((time.time() - start_time) * 1000, 2)
            return result

    if context:
        for append_kw in _APPEND_KEYWORDS:
            if msg.startswith(append_kw) or f"^{append_kw}" in msg:
                pending = context.get("pending_confirmation")
                if pending:
                    pending_intent = pending.get("intent") or pending.get("tool_key")
                    pending_slots = pending.get("slots", {}).copy() if pending.get("slots") else {}
                    result["primary_intent"] = pending_intent
                    result["tool_key"] = pending_intent
                    result["slots"] = pending_slots
                    result["context_inherited"] = True
                    result["source"] = "append_inherit"
                    result["is_append"] = True
                    result["elapsed_ms"] = round((time.time() - start_time) * 1000, 2)
                    return result

                last_intent = context.get("current_intent") or context.get("last_intent")
                last_tool = context.get("current_tool_key") or context.get("last_tool_key")
                last_slots = context.get("last_slots", {}).copy() if context.get("last_slots") else {}
                if last_intent or last_tool:
                    result["primary_intent"] = last_intent
                    result["tool_key"] = last_tool
                    result["slots"] = last_slots
                    result["context_inherited"] = True
                    result["source"] = "append_inherit"
                    result["is_append"] = True
                    result["elapsed_ms"] = round((time.time() - start_time) * 1000, 2)
                    return result

        for pattern, action in _CONTEXT_INHERIT_PATTERNS:
            if re.search(pattern, msg):
                if action == "repeat_last":
                    last_intent = context.get("current_intent") or context.get("last_intent")
                    last_tool = context.get("current_tool_key") or context.get("last_tool_key")
                    last_slots = context.get("last_slots", {})
                    if last_intent or last_tool:
                        result["primary_intent"] = last_intent
                        result["tool_key"] = last_tool
                        result["slots"] = last_slots.copy() if last_slots else {}
                        result["context_inherited"] = True
                        result["source"] = "context_inherit"
                        result["elapsed_ms"] = round((time.time() - start_time) * 1000, 2)
                        return result

        if context.get("pending_confirmation"):
            pending = context["pending_confirmation"]
            pending_intent = pending.get("intent") or pending.get("tool_key")
            if pending_intent:
                pending_slots = pending.get("slots", {})
                result["primary_intent"] = pending_intent
                result["tool_key"] = pending_intent
                result["slots"] = pending_slots.copy() if pending_slots else {}
                result["context_inherited"] = True
                result["source"] = "context_pending"
                result["elapsed_ms"] = round((time.time() - start_time) * 1000, 2)
                return result

    result["elapsed_ms"] = round((time.time() - start_time) * 1000, 2)
    return result


def quick_slot_extraction(message: str, intent: str) -> Dict[str, Any]:
    """
    快速槽位提取

    针对明确意图快速提取槽位信息

    Args:
        message: 用户消息
        intent: 识别的意图

    Returns:
        槽位字典
    """
    msg = _normalize(message)
    slots = {}

    if intent == "shipment_generate":
        unit_names = _extract_multi_unit_names(msg)
        if unit_names:
            if len(unit_names) == 1:
                slots["unit_name"] = unit_names[0]
            else:
                slots["unit_name"] = unit_names

        quantity_match = re.search(r'(\d+|[一二三四五六七八九十零〇两]+)\s*[桶箱件个]', msg)
        if quantity_match:
            slots["quantity"] = quantity_match.group(0)

        spec_match = re.search(r'规格\s*(\d+)', msg)
        if spec_match:
            slots["spec"] = spec_match.group(1)

        model_match = re.search(r'型号?\s*(\d+)', msg)
        if model_match:
            slots["model_number"] = model_match.group(1)

    elif intent == "products":
        if msg:
            slots["keyword"] = msg

    elif intent == "customers":
        if msg:
            slots["keyword"] = msg

    return slots


def _extract_multi_unit_names(msg: str) -> List[str]:
    """提取多个客户名称"""
    prefixes = ["发货单", "送货单", "出货单", "开单", "生成"]
    clean_msg = msg
    for prefix in prefixes:
        if clean_msg.startswith(prefix):
            clean_msg = clean_msg[len(prefix):].strip()

    quantity_pattern = r'\d+[桶箱件个]|[一二三四五六七八九十零〇]+[桶箱件个]'

    all_seps = ['和', '、', ',', '，']
    has_any_sep = any(sep in clean_msg for sep in all_seps)

    if has_any_sep:
        sep_pattern = '|'.join(re.escape(s) for s in all_seps)
        parts = re.split(sep_pattern, clean_msg)
        names = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            name = _extract_name_before_quantity(part, quantity_pattern)
            if name:
                names.append(name)
        if names:
            return names

    name = _extract_name_before_quantity(clean_msg, quantity_pattern)
    if name:
        return [name]

    return []


def _extract_name_before_quantity(text: str, quantity_pattern: str) -> Optional[str]:
    """从文本中提取量词前的客户名"""
    q_match = re.search(quantity_pattern, text)
    if q_match:
        name_part = text[:q_match.start()]
    else:
        name_part = text

    name_part = name_part.strip().rstrip('和的')
    name_match = re.match(r'^([^\s\d]{2,10})', name_part)
    if name_match:
        return name_match.group(1)

    if len(name_part) >= 2 and len(name_part) <= 10:
        return name_part

    return None
