# -*- coding: utf-8 -*-
"""
全流程意图层：统一意图定义、否定检测、问候/再见/模糊判断，供 AI 对话系统使用。

流程中的可能意图与处理：
1. 问候/再见 -> 直接回复，不进入工具
2. 否定式指令（不要生成、别上传）-> 不触发对应工具，走 AI 或友好提示
3. 硬规则意图（用户列表、导出、客户编辑、模板直答、专业版打印）-> 在路由层处理
4. 工具意图（生成发货单、上传、产品、客户、模板等）-> 关键词匹配 + 优先级，考虑否定
5. 仅模板查询（无工具命中）-> intent_hints 兜底模板直答
6. 模糊/短句/未知 -> 走 AI 兜底或引导
"""

import re
from typing import Dict, List, Optional, Any


# ------------------------- 否定前缀：句首或动作前出现则视为"不要做" -------------------------
NEGATION_PREFIXES = [
    "不要", "别", "不用", "不需要", "不必", "取消", "别给我", "别帮我",
    "不用了", "不要了", "算了", "不生成", "不开发", "不导入", "不上传",
    "不想", "不用帮我", "别弄", "不用弄", "不用做", "不要做",
]

# 否定短语（整句匹配或短句）
NEGATION_PHRASES = [
    "不要生成", "别生成", "不用生成", "不要开发货单", "别开发货单", "不要开单", "别开单",
    "不要上传", "别上传", "不用上传", "不要导入", "别导入",
    "不要打印", "别打印", "不用打印", "取消打印", "不打印", "不要打标签",
]

# ------------------------- 问候：命中则直接回复，不进入工具 -------------------------
GREETING_PATTERNS = [
    "你好", "您好", "嗨", "嗨喽", "hello", "hi ", "早上好", "下午好", "晚上好",
    "在吗", "在么", "有人吗", "在不在", "在不在呀",
]

# ------------------------- 再见/结束 -------------------------
GOODBYE_PATTERNS = [
    "再见", "拜拜", "bye", "先这样", "没事了", "谢谢再见", "好的谢谢", "先忙",
]

# ------------------------- 帮助/能力查询：可走硬规则或 AI -------------------------
HELP_PATTERNS = [
    "你能做什么", "你会什么", "有什么功能", "怎么用", "帮助", "帮帮我",
    "功能介绍", "说明一下", "有什么可以帮", "能干啥", "支持什么", "怎么操作",
]

# ------------------------- 工具意图定义：与 TOOL_KEYWORDS_MAP 对齐并扩展 -------------------------
# 每项：intent_id, keywords, priority(越大越优先), tool_key(对应分发), block_if_negated
TOOL_INTENTS = [
    # 高优先级：明确动作（专业版「打印 + 订单」在路由层单独处理，此处不占「打印」）
    ("shipment_generate", [
        "生成发货单", "发货单生成", "做发货单", "开发货单", "生成送货单",
        "开单", "打单", "开送货单", "做出货单", "生成出货单",
    ], 12, "shipment_generate", True),
    ("shipment_template", [
        "发货单模板", "模板", "抬头", "购货单位", "联系人", "订单编号", "功能介绍",
        "当前模板", "现在用的模板", "哪个模板", "词条", "可编辑词条",
    ], 9, "shipment_template", False),
    ("excel_decompose", [
        "分解 excel", "解析 excel", "分解模板", "提取词条", "excel 模板", "表头",
        "解析模板", "表头提取", "词条提取", "分解表",
    ], 9, "excel_decompose", False),
    ("shipments", ["出货", "订单", "发货", "出货单", "发货记录", "订单列表"], 8, "shipments", False),
    ("products", ["产品", "商品", "型号", "产品列表", "产品库", "规格"], 7, "products", False),
    ("customers", [
        "客户", "顾客", "单位", "用户列表", "用户名单", "购买单位", "单位列表",
        "客户列表", "用户清单", "客户名单",
    ], 6, "customers", False),
    ("print_label", [
        "打印", "标签", "打印标签", "商标导出", "标签导出", "下载标签", "打标签",
    ], 5, "print_label", True),
    ("show_images", ["图片", "照片", "图片列表", "查看图片", "看图片", "打开图片"], 6, "show_images", False),
    ("show_videos", ["视频", "录像", "视频列表", "查看视频", "看视频", "打开视频"], 6, "show_videos", False),
    ("upload_file", ["上传", "导入", "解析", "上传文件", "导入文件", "上传 excel"], 5, "upload_file", True),
    ("materials", ["原材料", "材料", "库存", "原材料库存", "库存查询", "材料库"], 4, "materials", False),
    ("wechat_send", [
        "发给他", "发送", "发微信", "发消息", "转发给他", "发一下", "发给",
        "转给他", "发给对方", "发过去", "发消息给", "发送消息给", "发送给",
    ], 10, "wechat_send", True),
]

# 仅用于 hint 的意图（不直接对应单一 tool_key，但影响兜底与 AI 上下文）
HINT_ONLY_INTENTS = [
    ("template_query", ["发货单模板", "当前模板", "现在用的模板", "现在模板", "哪个模板", "用的哪个模板"], 8),
    ("customer_export", ["导出 excel", "导出 xlsx", "导出表格", "导出用户列表", "导出客户列表", "导出购买单位", "导出单位"], 7),
    ("customer_list", ["查看用户列表", "用户列表", "用户名单", "查看用户", "客户列表", "查看客户列表", "购买单位列表"], 7),
    ("customer_edit", ["改成", "修改", "更新", "设为", "设置为", "改一下", "改下"], 5),
]


def _normalize(msg: Optional[str]) -> str:
    """标准化消息字符串"""
    if not isinstance(msg, str):
        return ""
    return (msg or "").strip()


def is_negation(message: str, action_keywords: Optional[List[str]] = None) -> bool:
    """
    判断是否为否定式指令。
    
    Args:
        message: 用户消息
        action_keywords: 若提供，则检查否定前缀是否在该动作词之前（更精确）
        
    Returns:
        是否为否定式指令
    """
    msg = _normalize(message)
    if not msg:
        return False
    
    msg_lower = msg.lower()
    
    # 整句否定短语
    for phrase in NEGATION_PHRASES:
        if phrase in msg or phrase in msg_lower:
            return True
    
    # 句首否定
    for prefix in NEGATION_PREFIXES:
        if msg_lower.startswith(prefix) or msg.startswith(prefix):
            return True
        if (" " + prefix in msg_lower) or ("，" + prefix in msg_lower):
            return True
    
    # 若指定了动作词，检查「不要/别/不用」是否在动作词前面
    if action_keywords:
        for kw in action_keywords:
            idx = msg_lower.find(kw.lower())
            if idx == -1:
                continue
            before = msg_lower[:idx]
            for prefix in NEGATION_PREFIXES:
                if prefix in before or before.endswith(prefix):
                    return True
    
    return False


def is_greeting(message: str) -> bool:
    """
    判断是否为问候语。
    
    Args:
        message: 用户消息
        
    Returns:
        是否为问候语
    """
    msg = _normalize(message)
    if len(msg) > 20:
        return False
    
    msg_lower = msg.lower()
    for p in GREETING_PATTERNS:
        if p in msg_lower or p in msg:
            return True
    
    return False


def is_goodbye(message: str) -> bool:
    """
    判断是否为告别语。
    
    Args:
        message: 用户消息
        
    Returns:
        是否为告别语
    """
    msg = _normalize(message)
    if len(msg) > 25:
        return False
    
    msg_lower = msg.lower()
    for p in GOODBYE_PATTERNS:
        if p in msg_lower or p in msg:
            return True
    
    return False


def is_help_request(message: str) -> bool:
    """
    判断是否为帮助请求。
    
    Args:
        message: 用户消息
        
    Returns:
        是否为帮助请求
    """
    msg = _normalize(message)
    msg_lower = msg.lower()
    for p in HELP_PATTERNS:
        if p in msg_lower or p in msg:
            return True
    
    return False


def _match_tool_intents(message: str) -> List[tuple]:
    """
    匹配工具意图。
    
    Args:
        message: 用户消息
        
    Returns:
        (intent_id, tool_key, priority, block_if_negated) 列表，按 priority 降序
    """
    msg = _normalize(message)
    msg_lower = msg.lower()
    matched = []
    
    for item in TOOL_INTENTS:
        intent_id, keywords, priority, tool_key, block_if_negated = item
        for kw in keywords:
            if kw in message or kw.lower() in msg_lower:
                matched.append((intent_id, tool_key, priority, block_if_negated))
                break
    
    matched.sort(key=lambda x: (x[2], -len(x[0])), reverse=True)
    return matched


def _match_hint_intents(message: str) -> List[str]:
    """
    匹配提示意图。
    
    Args:
        message: 用户消息
        
    Returns:
        命中的 hint 意图 id 列表
    """
    msg = _normalize(message)
    msg_lower = msg.lower()
    hints = []
    
    for item in HINT_ONLY_INTENTS:
        intent_id, keywords, _ = item
        for kw in keywords:
            if kw in message or kw.lower() in msg_lower:
                if intent_id not in hints:
                    hints.append(intent_id)
                break
    
    return hints


def recognize_intents(message: str) -> Dict[str, Any]:
    """
    全流程意图识别入口。
    
    Args:
        message: 用户消息
        
    Returns:
        意图识别结果字典，包含：
        - primary_intent: 主意图 id（工具类或 template_query 等）
        - tool_key: 建议触发的工具 key，若为否定或无可选则为 None
        - intent_hints: 用于上下文的 hint 列表（含 template_query, shipment_generate 等）
        - is_negated: 是否判定为否定式
        - is_greeting: 是否问候
        - is_goodbye: 是否再见
        - is_help: 是否帮助请求
        - is_likely_unclear: 短句且无任何意图匹配
        - all_matched_tools: 所有匹配到的 (intent_id, tool_key) 列表（供日志/多意图扩展）
    """
    msg = _normalize(message)
    msg_lower = (msg or "").lower()
    
    result = {
        "primary_intent": None,
        "tool_key": None,
        "intent_hints": [],
        "is_negated": False,
        "is_greeting": False,
        "is_goodbye": False,
        "is_help": False,
        "is_likely_unclear": False,
        "all_matched_tools": [],
    }
    
    result["is_greeting"] = is_greeting(message)
    result["is_goodbye"] = is_goodbye(message)
    result["is_help"] = is_help_request(message)
    
    # 先检测"发货单 + 订单信息"特殊格式（优先级最高）
    # 如"发货单七彩乐园 1 桶 9803 规格 12"
    if (msg.startswith("发货单") or msg.startswith("送货单") or msg.startswith("出货单")) and len(msg) > 5:
        order_patterns = ["桶", "规格", "公斤", "kg", "件", "箱"]
        has_order_info = any(pattern in msg for pattern in order_patterns)
        if has_order_info:
            result["primary_intent"] = "shipment_generate"
            result["tool_key"] = "shipment_generate"
            result["intent_hints"].append("shipment_generate")
            # 跳过普通工具匹配，避免被其他关键词干扰
            return result
    
    # 工具意图匹配
    tool_matches = _match_tool_intents(message)
    result["all_matched_tools"] = [(m[0], m[1]) for m in tool_matches]
    
    if tool_matches:
        best = tool_matches[0]
        intent_id, tool_key, _pri, block_if_negated = best
        result["primary_intent"] = intent_id
        
        action_kw = []
        for item in TOOL_INTENTS:
            if item[0] == intent_id:
                action_kw = list(item[1])
                break
        
        negated = is_negation(message, action_keywords=action_kw) if block_if_negated else False
        result["is_negated"] = negated
        
        if not negated:
            result["tool_key"] = tool_key
        
        # 同步到 hint
        if intent_id == "shipment_generate":
            result["intent_hints"].append("shipment_generate")
        elif intent_id == "shipment_template" or intent_id == "template_query":
            if "template_query" not in result["intent_hints"]:
                result["intent_hints"].append("template_query")
        
        if "upload_file" in (m[1] for m in tool_matches) and "upload_file" not in result["intent_hints"]:
            result["intent_hints"].append("upload_file")
    
    # Hint-only 意图（补充 intent_hints，不覆盖 tool_key）
    hint_only = _match_hint_intents(message)
    for h in hint_only:
        if h not in result["intent_hints"]:
            result["intent_hints"].append(h)
    
    if ("模板" in msg or "template" in msg_lower) and "template_query" not in result["intent_hints"]:
        result["intent_hints"].append("template_query")
    
    if ("生成发货单" in msg or "开发货单" in msg) and "shipment_generate" not in result["intent_hints"]:
        result["intent_hints"].append("shipment_generate")
    
    # 检测"发货单 + 订单信息"格式（如"发货单七彩乐园 1 桶 9803 规格 12"）
    if (msg.startswith("发货单") or msg.startswith("送货单") or msg.startswith("出货单")) and len(msg) > 5:
        # 检查是否包含订单特征词（桶、规格、公斤等）
        order_patterns = ["桶", "规格", "公斤", "kg", "件", "箱"]
        has_order_info = any(pattern in msg for pattern in order_patterns)
        if has_order_info and not result["tool_key"]:
            # 没有更明确的工具意图时，将其识别为生成发货单
            result["primary_intent"] = "shipment_generate"
            result["tool_key"] = "shipment_generate"
            if "shipment_generate" not in result["intent_hints"]:
                result["intent_hints"].append("shipment_generate")
    
    if ("上传" in msg or "导入" in msg or "upload" in msg_lower) and "upload_file" not in result["intent_hints"]:
        result["intent_hints"].append("upload_file")
    
    # 模糊：很短且无任何匹配
    result["is_likely_unclear"] = (
        len(msg) <= 4
        and not result["is_greeting"]
        and not result["is_goodbye"]
        and not result["primary_intent"]
        and not result["intent_hints"]
    )
    
    return result


def get_tool_key_with_negation_check(message: str) -> Optional[str]:
    """
    对外接口：在考虑否定后，返回应触发的 tool_key；若为否定或无可选则返回 None。
    
    Args:
        message: 用户消息
        
    Returns:
        工具 key 或 None
    """
    r = recognize_intents(message)
    return r.get("tool_key")
