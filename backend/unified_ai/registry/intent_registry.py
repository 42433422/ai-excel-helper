"""
意图注册表
"""

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class IntentDefinition:
    name: str
    description: str
    slots: dict[str, Any]
    default_response: str = ""
    tools: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    priority: int = 50


INTENT_REGISTRY: dict[str, IntentDefinition] = {
    "sales_contract": IntentDefinition(
        name="sales_contract",
        description="生成销售合同",
        slots={
            "customer_name": {"type": "string", "required": True},
            "products": {"type": "list[ProductItem]", "required": True},
            "delivery_date": {"type": "date", "required": False},
            "remark": {"type": "string", "required": False},
        },
        default_response="正在为您生成销售合同...",
        tools=["contract_validate", "sales_contract_generate"],
        examples=[
            "打印销售合同",
            "生成合同 客户 xxx 产品 xxx",
            "帮我做一份销售合同",
        ],
        priority=80
    ),
    "product_query": IntentDefinition(
        name="product_query",
        description="查询产品信息、价格、规格",
        slots={
            "query": {"type": "string", "required": False},
            "customer_name": {"type": "string", "required": False},
        },
        default_response="正在查询产品信息...",
        tools=["product_match"],
        examples=[
            "查询产品3721",
            "这个客户买过什么产品",
            "查产品价格",
            "查询9806A产品规格",
        ],
        priority=70
    ),
    "price_list_export": IntentDefinition(
        name="price_list_export",
        description="导出价格表",
        slots={
            "customer_name": {"type": "string", "required": True},
            "products": {"type": "list[string]", "required": False},
        },
        default_response="正在导出价格表...",
        tools=["price_list_export"],
        examples=["导出价格表", "打印价格单"],
        priority=60
    ),
    "shipment_generate": IntentDefinition(
        name="shipment_generate",
        description="生成发货单",
        slots={
            "customer_name": {"type": "string", "required": True},
            "products": {"type": "list[ProductItem]", "required": True},
            "delivery_date": {"type": "date", "required": False},
            "remark": {"type": "string", "required": False},
        },
        default_response="正在生成发货单...",
        tools=["shipment_generate"],
        examples=[
            "生成发货单",
            "发货单蕊芯1一桶9806A规格23",
            "帮我做一份发货单",
        ],
        priority=78
    ),
    "shipment_query": IntentDefinition(
        name="shipment_query",
        description="查询发货单状态",
        slots={
            "shipment_id": {"type": "string", "required": False},
            "customer_name": {"type": "string", "required": False},
            "status": {"type": "string", "required": False},
        },
        default_response="正在查询发货单...",
        tools=["shipment_query"],
        examples=[
            "查询发货单状态",
            "查询发货单FH2024001",
            "查看待发货的发货单",
        ],
        priority=68
    ),
    "shipment_add": IntentDefinition(
        name="shipment_add",
        description="增加发货单",
        slots={
            "customer_name": {"type": "string", "required": True},
            "products": {"type": "list[ProductItem]", "required": True},
            "shipment_id": {"type": "string", "required": False},
        },
        default_response="正在增加发货单...",
        tools=["shipment_add"],
        examples=[
            "增加2桶9806规格23",
            "给发货单FH2024001增加产品",
        ],
        priority=67
    ),
    "shipment_update": IntentDefinition(
        name="shipment_update",
        description="修改发货单",
        slots={
            "shipment_id": {"type": "string", "required": True},
            "updates": {"type": "dict", "required": True},
        },
        default_response="正在修改发货单...",
        tools=["shipment_update"],
        examples=[
            "修改发货单FH2024001数量",
            "更新发货单状态为已发货",
        ],
        priority=66
    ),
    "shipment_delete": IntentDefinition(
        name="shipment_delete",
        description="删除发货单",
        slots={
            "shipment_id": {"type": "string", "required": True},
        },
        default_response="正在删除发货单...",
        tools=["shipment_delete"],
        examples=[
            "删除发货单FH2024002",
        ],
        priority=65
    ),
    "shipment_approve": IntentDefinition(
        name="shipment_approve",
        description="审核发货单",
        slots={
            "shipment_id": {"type": "string", "required": True},
            "approved": {"type": "boolean", "required": False},
        },
        default_response="正在审核发货单...",
        tools=["shipment_approve"],
        examples=[
            "审核待处理发货单",
            "通过发货单FH2024001",
        ],
        priority=64
    ),
    "label_print": IntentDefinition(
        name="label_print",
        description="打印产品标签",
        slots={
            "model_number": {"type": "string", "required": True},
            "quantity": {"type": "integer", "required": False},
        },
        default_response="正在打印标签...",
        tools=["label_print"],
        examples=[
            "打印标签9806A",
            "生成产品标签",
            "打印3张9806标签",
        ],
        priority=72
    ),
    "customer_query": IntentDefinition(
        name="customer_query",
        description="查询客户信息",
        slots={
            "customer_name": {"type": "string", "required": False},
            "customer_id": {"type": "string", "required": False},
        },
        default_response="正在查询客户信息...",
        tools=["customer_query"],
        examples=[
            "查询客户张三的信息",
            "查看客户联系方式",
        ],
        priority=62
    ),
    "stock_query": IntentDefinition(
        name="stock_query",
        description="查询库存信息",
        slots={
            "query": {"type": "string", "required": False},
            "product_name": {"type": "string", "required": False},
        },
        default_response="正在查询库存...",
        tools=["stock_query"],
        examples=[
            "查询9806A库存情况",
            "查看库存不足的产品",
            "原材料库存",
        ],
        priority=63
    ),
    "statement_generate": IntentDefinition(
        name="statement_generate",
        description="生成对账单",
        slots={
            "customer_name": {"type": "string", "required": True},
            "date_range": {"type": "string", "required": False},
        },
        default_response="正在生成对账单...",
        tools=["statement_generate"],
        examples=[
            "生成客户A对账单",
            "打印对账单",
        ],
        priority=58
    ),
    "purchase_generate": IntentDefinition(
        name="purchase_generate",
        description="生成采购单",
        slots={
            "products": {"type": "list[ProductItem]", "required": True},
            "supplier": {"type": "string", "required": False},
        },
        default_response="正在生成采购单...",
        tools=["purchase_generate"],
        examples=[
            "生成采购单",
            "库存不足产品采购单",
        ],
        priority=57
    ),
    "report_generate": IntentDefinition(
        name="report_generate",
        description="生成业务报表",
        slots={
            "report_type": {"type": "string", "required": False},
            "date_range": {"type": "string", "required": False},
        },
        default_response="正在生成报表...",
        tools=["report_generate"],
        examples=[
            "生成本月销售报表",
            "导出库存报表",
        ],
        priority=56
    ),
    "data_export": IntentDefinition(
        name="data_export",
        description="导出数据",
        slots={
            "data_type": {"type": "string", "required": True},
            "format": {"type": "string", "required": False},
            "date_range": {"type": "string", "required": False},
        },
        default_response="正在导出数据...",
        tools=["data_export"],
        examples=[
            "导出本月发货单数据",
            "导出客户列表",
        ],
        priority=55
    ),
    "general_chat": IntentDefinition(
        name="general_chat",
        description="通用对话",
        slots={},
        default_response="",
        tools=[],
        priority=10
    ),
}


def register_intent(intent_def: IntentDefinition) -> None:
    INTENT_REGISTRY[intent_def.name] = intent_def


def get_intent(name: str) -> IntentDefinition | None:
    return INTENT_REGISTRY.get(name)


def list_intents() -> list[IntentDefinition]:
    return list(INTENT_REGISTRY.values())
