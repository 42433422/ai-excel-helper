"""
反射弧注册表 - 快速预定义响应 (<1ms)
"""

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ReflexPattern:
    regex: re.Pattern
    response: str
    intent: str = "reflex"
    priority: int = 100
    metadata: dict[str, Any] = field(default_factory=dict)


REFLEX_PATTERNS: dict[str, ReflexPattern] = {
    "greeting": ReflexPattern(
        regex=re.compile(r"^(hi|hello|hey|你好|在吗|在不在|嗨|hiya)$", re.IGNORECASE),
        response="你好！有什么我可以帮助你的？",
        intent="greeting",
        priority=100
    ),
    "stop": ReflexPattern(
        regex=re.compile(r"^(stop|停止|cancel|取消|abort|别说了|不用了)$", re.IGNORECASE),
        response="好的，已停止。",
        intent="stop",
        priority=100
    ),
    "simple_query": ReflexPattern(
        regex=re.compile(r"^(查|看|找|搜索|search|查询)\s", re.IGNORECASE),
        response="",
        intent="query",
        priority=80
    ),
    "help_request": ReflexPattern(
        regex=re.compile(r"^(帮助|help|怎么用|如何|usage|使用说明)$", re.IGNORECASE),
        response="我可以帮你：\n1. 生成销售合同 / 打印合同\n2. 生成发货单 / 增加发货单\n3. 查询产品信息 / 价格 / 规格\n4. 查询客户信息\n5. 查询库存\n6. 导出价格表 / 对账单\n7. 打印产品标签\n8. 生成采购单 / 报表\n9. 分析Excel数据\n\n请告诉我你需要什么帮助？",
        intent="help",
        priority=90
    ),
    "confirm_yes": ReflexPattern(
        regex=re.compile(r"^(是|yes|对|好的|确认|ok|确定|可以|行|嗯)$", re.IGNORECASE),
        response="好的，已确认。",
        intent="confirm_yes",
        priority=95
    ),
    "confirm_no": ReflexPattern(
        regex=re.compile(r"^(不|no|否|取消|算了|不要)$", re.IGNORECASE),
        response="好的，已取消。",
        intent="confirm_no",
        priority=95
    ),
    "thank_you": ReflexPattern(
        regex=re.compile(r"^(谢谢|感谢|thanks|thank you|多谢|3q|thx)$", re.IGNORECASE),
        response="不客气！如果还有其他问题，随时问我。",
        intent="thank_you",
        priority=50
    ),
    "shipment_generate": ReflexPattern(
        regex=re.compile(r"^(生成发货单|发货单|做发货单|新建发货单|创建发货单)$", re.IGNORECASE),
        response="",
        intent="shipment_generate",
        priority=85
    ),
    "shipment_query": ReflexPattern(
        regex=re.compile(r"^(查发货单|查询发货单|发货单状态|发货单查询|查看发货单)$", re.IGNORECASE),
        response="",
        intent="shipment_query",
        priority=85
    ),
    "label_print": ReflexPattern(
        regex=re.compile(r"^(打印标签|标签打印|生成标签|产品标签|打标签)$", re.IGNORECASE),
        response="",
        intent="label_print",
        priority=85
    ),
    "stock_query": ReflexPattern(
        regex=re.compile(r"^(查库存|库存查询|库存情况|库存状态|查看库存)$", re.IGNORECASE),
        response="",
        intent="stock_query",
        priority=85
    ),
    "customer_query": ReflexPattern(
        regex=re.compile(r"^(查客户|客户查询|客户信息|查看客户|客户资料)$", re.IGNORECASE),
        response="",
        intent="customer_query",
        priority=85
    ),
    "price_list": ReflexPattern(
        regex=re.compile(r"^(导出价格表|价格表|价格单|报价单)$", re.IGNORECASE),
        response="",
        intent="price_list_export",
        priority=85
    ),
    "statement": ReflexPattern(
        regex=re.compile(r"^(对账单|生成对账单|打印对账单)$", re.IGNORECASE),
        response="",
        intent="statement_generate",
        priority=85
    ),
    "purchase": ReflexPattern(
        regex=re.compile(r"^(采购单|生成采购单|新建采购单)$", re.IGNORECASE),
        response="",
        intent="purchase_generate",
        priority=85
    ),
    "report": ReflexPattern(
        regex=re.compile(r"^(报表|生成报表|销售报表|库存报表)$", re.IGNORECASE),
        response="",
        intent="report_generate",
        priority=85
    ),
}


def register_reflex(name: str, pattern: ReflexPattern) -> None:
    REFLEX_PATTERNS[name] = pattern


def match_reflex(user_input: str) -> ReflexPattern | None:
    user_input = user_input.strip()
    if not user_input:
        return None

    matched: ReflexPattern | None = None
    highest_priority = -1

    for pattern in REFLEX_PATTERNS.values():
        if pattern.regex.match(user_input):
            if pattern.priority > highest_priority:
                highest_priority = pattern.priority
                matched = pattern

    return matched


def list_reflexes() -> list[ReflexPattern]:
    return list(REFLEX_PATTERNS.values())
