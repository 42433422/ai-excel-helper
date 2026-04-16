"""
规则处理器 - <50ms 规则匹配
"""

import re
import time
import logging
from dataclasses import dataclass, field
from typing import Any

from ..registry.intent_registry import INTENT_REGISTRY
from ..utils.metrics import get_metrics

logger = logging.getLogger(__name__)


@dataclass
class RuleResult:
    matched: bool
    intent: str = ""
    confidence: float = 0.0
    entities: dict[str, Any] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    rule_name: str = ""


RULE_PATTERNS: list[tuple[str, re.Pattern, float, dict[str, Any]]] = [
    (
        "sales_contract",
        re.compile(r"(销售合同|购销合同|打印.*合同|生成.*合同|合同.*(桶|瓶|箱))", re.IGNORECASE),
        0.85,
        {}
    ),
    (
        "sales_contract",
        re.compile(r"(帮我|那个|呃).*?(销售|购销)?合同", re.IGNORECASE),
        0.75,
        {}
    ),
    (
        "product_query",
        re.compile(r"(查询|查|看|找)(产品|型号|编号|价格|规格)"),
        0.80,
        {}
    ),
    (
        "product_query",
        re.compile(r"(产品|型号|编号)\s*[\d\w]+"),
        0.75,
        {}
    ),
    (
        "price_list_export",
        re.compile(r"(价格表|价目表|报价单|price.?list)"),
        0.85,
        {}
    ),
    (
        "price_list_export",
        re.compile(r"(导出|打印)(.+)?(价格|价目|报价)"),
        0.88,
        {}
    ),
    (
        "shipment_generate",
        re.compile(r"(生成|创建|新建|做)(.+)?发货单"),
        0.88,
        {}
    ),
    (
        "shipment_generate",
        re.compile(r"发货单.{0,5}[\d\w]+.{0,10}(桶|箱|件|个)"),
        0.85,
        {}
    ),
    (
        "shipment_query",
        re.compile(r"(查询|查|看)(.+)?发货单(.+)?(状态|进度|情况)"),
        0.85,
        {}
    ),
    (
        "shipment_query",
        re.compile(r"发货单(FH|fh)\d+"),
        0.90,
        {}
    ),
    (
        "shipment_add",
        re.compile(r"(增加|添加|追加)(.+)?发货单"),
        0.85,
        {}
    ),
    (
        "shipment_update",
        re.compile(r"(修改|更新|编辑)(.+)?发货单"),
        0.85,
        {}
    ),
    (
        "shipment_delete",
        re.compile(r"(删除|移除|取消)(.+)?发货单"),
        0.85,
        {}
    ),
    (
        "shipment_approve",
        re.compile(r"(审核|审批|批准|通过)(.+)?发货单"),
        0.85,
        {}
    ),
    (
        "label_print",
        re.compile(r"(打印|生成|做)(.+)?标签"),
        0.88,
        {}
    ),
    (
        "label_print",
        re.compile(r"(标签|label).{0,5}[\d\w]+"),
        0.80,
        {}
    ),
    (
        "customer_query",
        re.compile(r"(查询|查|看)(.+)?(客户|客户信息|联系方式)"),
        0.85,
        {}
    ),
    (
        "stock_query",
        re.compile(r"(查询|查|看)(.+)?(库存|存量|存货)"),
        0.85,
        {}
    ),
    (
        "stock_query",
        re.compile(r"(库存|存量)(不足|不够|缺少|短缺)"),
        0.88,
        {}
    ),
    (
        "statement_generate",
        re.compile(r"(生成|打印|做)(.+)?对账单"),
        0.88,
        {}
    ),
    (
        "purchase_generate",
        re.compile(r"(生成|创建|做)(.+)?采购单"),
        0.88,
        {}
    ),
    (
        "report_generate",
        re.compile(r"(生成|导出|做)(.+)?(报表|报告|统计)"),
        0.85,
        {}
    ),
    (
        "data_export",
        re.compile(r"(导出|下载)(.+)?(数据|列表|记录)"),
        0.80,
        {}
    ),
]


class RuleProcessor:
    def __init__(self):
        self._enabled = True
        self._patterns = RULE_PATTERNS

    def process(self, user_input: str) -> RuleResult:
        if not self._enabled:
            return RuleResult(matched=False)

        start = time.perf_counter()

        try:
            for intent_name, pattern, confidence, default_entities in self._patterns:
                match = pattern.search(user_input)
                if match:
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    get_metrics().histogram("rule_processor.duration_ms", elapsed_ms)
                    get_metrics().inc("rule_processor.hit", tags={"intent": intent_name})

                    logger.debug(f"[RuleProcessor] 命中规则: {intent_name} ({elapsed_ms:.2f}ms)")

                    return RuleResult(
                        matched=True,
                        intent=intent_name,
                        confidence=confidence,
                        entities=default_entities,
                        processing_time_ms=elapsed_ms,
                        rule_name=intent_name
                    )

            elapsed_ms = (time.perf_counter() - start) * 1000
            return RuleResult(matched=False, processing_time_ms=elapsed_ms)

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.warning(f"[RuleProcessor] 处理异常: {e}")
            return RuleResult(matched=False, processing_time_ms=elapsed_ms)

    def add_pattern(self, intent: str, pattern: re.Pattern, confidence: float = 0.8, entities: dict | None = None) -> None:
        self._patterns.append((intent, pattern, confidence, entities or {}))

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False
