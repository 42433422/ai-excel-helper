"""
工具注册表
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    handler: Callable[..., Any]
    required_intents: list[str] = field(default_factory=list)
    priority: int = 50
    timeout_ms: int = 10000


TOOL_REGISTRY: dict[str, ToolDefinition] = {}


def register_tool(tool_def: ToolDefinition) -> None:
    TOOL_REGISTRY[tool_def.name] = tool_def


def get_tool(name: str) -> ToolDefinition | None:
    return TOOL_REGISTRY.get(name)


def get_tools_for_intent(intent: str) -> list[ToolDefinition]:
    return [t for t in TOOL_REGISTRY.values() if intent in t.required_intents]


def list_tools() -> list[ToolDefinition]:
    return list(TOOL_REGISTRY.values())


def register_builtin_tools() -> None:
    from backend.unified_ai.tools.contract_tool import ContractTool
    from backend.unified_ai.tools.product_tool import ProductTool
    from backend.unified_ai.tools.sales_contract_tool import SalesContractGenerateTool
    from backend.unified_ai.tools.shipment_tool import (
        ShipmentGenerateTool, ShipmentQueryTool, ShipmentAddTool,
        ShipmentUpdateTool, ShipmentDeleteTool, ShipmentApproveTool,
    )
    from backend.unified_ai.tools.label_tool import LabelPrintTool
    from backend.unified_ai.tools.customer_tool import CustomerQueryTool
    from backend.unified_ai.tools.stock_tool import StockQueryTool
    from backend.unified_ai.tools.statement_tool import StatementGenerateTool
    from backend.unified_ai.tools.purchase_tool import PurchaseGenerateTool
    from backend.unified_ai.tools.report_tool import ReportGenerateTool
    from backend.unified_ai.tools.data_export_tool import DataExportTool

    contract_tool = ContractTool()
    TOOL_REGISTRY["contract_validate"] = ToolDefinition(
        name="contract_validate",
        description="校验销售合同中的客户名称和产品型号是否有效",
        input_schema={
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
                "products": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "model_number": {"type": "string"},
                            "quantity": {"type": "integer"}
                        }
                    }
                }
            },
            "required": ["customer_name", "products"]
        },
        output_schema={
            "type": "object",
            "properties": {
                "valid": {"type": "boolean"},
                "message": {"type": "string"},
                "valid_products": {"type": "array"}
            }
        },
        handler=contract_tool.execute,
        required_intents=["sales_contract"],
        priority=80
    )

    product_tool = ProductTool()
    TOOL_REGISTRY["product_match"] = ToolDefinition(
        name="product_match",
        description="根据产品型号或名称匹配产品信息",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "customer_name": {"type": "string", "default": ""}
            },
            "required": ["query"]
        },
        output_schema={
            "type": "object",
            "properties": {
                "matches": {"type": "array"},
                "best_match": {"type": "object"}
            }
        },
        handler=product_tool.execute,
        required_intents=["product_query", "sales_contract", "stock_query"],
        priority=70
    )

    sales_contract_tool = SalesContractGenerateTool()
    TOOL_REGISTRY["sales_contract_generate"] = ToolDefinition(
        name="sales_contract_generate",
        description="生成销售合同 Excel（送货单版式 .xlsx）",
        input_schema={
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
                "products": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "model_number": {"type": "string"},
                            "name": {"type": "string"},
                            "quantity": {"type": "string"}
                        }
                    }
                },
                "contract_date": {"type": "string"},
                "customer_phone": {"type": "string"},
                "template_id": {
                    "type": "string",
                    "description": "内部模板 id（GET /api/sales-contract/templates），与前端下拉一致",
                },
            },
            "required": ["customer_name", "products"]
        },
        output_schema={
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "data": {"type": "object"},
                "message": {"type": "string"}
            }
        },
        handler=sales_contract_tool.execute,
        required_intents=["sales_contract"],
        priority=90
    )

    shipment_gen = ShipmentGenerateTool()
    TOOL_REGISTRY["shipment_generate"] = ToolDefinition(
        name="shipment_generate",
        description="生成发货单",
        input_schema={
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
                "products": {"type": "array", "items": {"type": "object"}},
                "delivery_date": {"type": "string"},
                "remark": {"type": "string"}
            },
            "required": ["customer_name", "products"]
        },
        output_schema={"type": "object", "properties": {"success": {"type": "boolean"}, "data": {"type": "object"}, "message": {"type": "string"}}},
        handler=shipment_gen.execute,
        required_intents=["shipment_generate"],
        priority=78
    )

    shipment_qry = ShipmentQueryTool()
    TOOL_REGISTRY["shipment_query"] = ToolDefinition(
        name="shipment_query",
        description="查询发货单状态",
        input_schema={
            "type": "object",
            "properties": {
                "shipment_id": {"type": "string"},
                "customer_name": {"type": "string"},
                "status": {"type": "string"}
            }
        },
        output_schema={"type": "object", "properties": {"success": {"type": "boolean"}, "data": {"type": "object"}, "message": {"type": "string"}}},
        handler=shipment_qry.execute,
        required_intents=["shipment_query"],
        priority=68
    )

    shipment_add = ShipmentAddTool()
    TOOL_REGISTRY["shipment_add"] = ToolDefinition(
        name="shipment_add",
        description="增加发货单产品",
        input_schema={
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
                "products": {"type": "array", "items": {"type": "object"}},
                "shipment_id": {"type": "string"}
            },
            "required": ["customer_name", "products"]
        },
        output_schema={"type": "object", "properties": {"success": {"type": "boolean"}, "data": {"type": "object"}, "message": {"type": "string"}}},
        handler=shipment_add.execute,
        required_intents=["shipment_add"],
        priority=67
    )

    shipment_upd = ShipmentUpdateTool()
    TOOL_REGISTRY["shipment_update"] = ToolDefinition(
        name="shipment_update",
        description="修改发货单",
        input_schema={
            "type": "object",
            "properties": {
                "shipment_id": {"type": "string"},
                "updates": {"type": "object"}
            },
            "required": ["shipment_id", "updates"]
        },
        output_schema={"type": "object", "properties": {"success": {"type": "boolean"}, "data": {"type": "object"}, "message": {"type": "string"}}},
        handler=shipment_upd.execute,
        required_intents=["shipment_update"],
        priority=66
    )

    shipment_del = ShipmentDeleteTool()
    TOOL_REGISTRY["shipment_delete"] = ToolDefinition(
        name="shipment_delete",
        description="删除发货单",
        input_schema={
            "type": "object",
            "properties": {"shipment_id": {"type": "string"}},
            "required": ["shipment_id"]
        },
        output_schema={"type": "object", "properties": {"success": {"type": "boolean"}, "data": {"type": "object"}, "message": {"type": "string"}}},
        handler=shipment_del.execute,
        required_intents=["shipment_delete"],
        priority=65
    )

    shipment_apv = ShipmentApproveTool()
    TOOL_REGISTRY["shipment_approve"] = ToolDefinition(
        name="shipment_approve",
        description="审核发货单",
        input_schema={
            "type": "object",
            "properties": {
                "shipment_id": {"type": "string"},
                "approved": {"type": "boolean", "default": True}
            },
            "required": ["shipment_id"]
        },
        output_schema={"type": "object", "properties": {"success": {"type": "boolean"}, "data": {"type": "object"}, "message": {"type": "string"}}},
        handler=shipment_apv.execute,
        required_intents=["shipment_approve"],
        priority=64
    )

    label_tool = LabelPrintTool()
    TOOL_REGISTRY["label_print"] = ToolDefinition(
        name="label_print",
        description="打印产品标签",
        input_schema={
            "type": "object",
            "properties": {
                "model_number": {"type": "string"},
                "quantity": {"type": "integer", "default": 1}
            },
            "required": ["model_number"]
        },
        output_schema={"type": "object", "properties": {"success": {"type": "boolean"}, "data": {"type": "object"}, "message": {"type": "string"}}},
        handler=label_tool.execute,
        required_intents=["label_print"],
        priority=72
    )

    customer_tool = CustomerQueryTool()
    TOOL_REGISTRY["customer_query"] = ToolDefinition(
        name="customer_query",
        description="查询客户信息",
        input_schema={
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
                "customer_id": {"type": "string"}
            }
        },
        output_schema={"type": "object", "properties": {"success": {"type": "boolean"}, "data": {"type": "object"}, "message": {"type": "string"}}},
        handler=customer_tool.execute,
        required_intents=["customer_query"],
        priority=62
    )

    stock_tool = StockQueryTool()
    TOOL_REGISTRY["stock_query"] = ToolDefinition(
        name="stock_query",
        description="查询库存信息",
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "product_name": {"type": "string"}
            }
        },
        output_schema={"type": "object", "properties": {"success": {"type": "boolean"}, "data": {"type": "object"}, "message": {"type": "string"}}},
        handler=stock_tool.execute,
        required_intents=["stock_query"],
        priority=63
    )

    statement_tool = StatementGenerateTool()
    TOOL_REGISTRY["statement_generate"] = ToolDefinition(
        name="statement_generate",
        description="生成客户对账单",
        input_schema={
            "type": "object",
            "properties": {
                "customer_name": {"type": "string"},
                "date_range": {"type": "string"}
            },
            "required": ["customer_name"]
        },
        output_schema={"type": "object", "properties": {"success": {"type": "boolean"}, "data": {"type": "object"}, "message": {"type": "string"}}},
        handler=statement_tool.execute,
        required_intents=["statement_generate"],
        priority=58
    )

    purchase_tool = PurchaseGenerateTool()
    TOOL_REGISTRY["purchase_generate"] = ToolDefinition(
        name="purchase_generate",
        description="生成采购单",
        input_schema={
            "type": "object",
            "properties": {
                "products": {"type": "array", "items": {"type": "object"}},
                "supplier": {"type": "string"}
            },
            "required": ["products"]
        },
        output_schema={"type": "object", "properties": {"success": {"type": "boolean"}, "data": {"type": "object"}, "message": {"type": "string"}}},
        handler=purchase_tool.execute,
        required_intents=["purchase_generate"],
        priority=57
    )

    report_tool = ReportGenerateTool()
    TOOL_REGISTRY["report_generate"] = ToolDefinition(
        name="report_generate",
        description="生成业务报表",
        input_schema={
            "type": "object",
            "properties": {
                "report_type": {"type": "string"},
                "date_range": {"type": "string"}
            }
        },
        output_schema={"type": "object", "properties": {"success": {"type": "boolean"}, "data": {"type": "object"}, "message": {"type": "string"}}},
        handler=report_tool.execute,
        required_intents=["report_generate"],
        priority=56
    )

    data_export_tool = DataExportTool()
    TOOL_REGISTRY["data_export"] = ToolDefinition(
        name="data_export",
        description="导出数据",
        input_schema={
            "type": "object",
            "properties": {
                "data_type": {"type": "string"},
                "format": {"type": "string", "default": "xlsx"},
                "date_range": {"type": "string"}
            },
            "required": ["data_type"]
        },
        output_schema={"type": "object", "properties": {"success": {"type": "boolean"}, "data": {"type": "object"}, "message": {"type": "string"}}},
        handler=data_export_tool.execute,
        required_intents=["data_export"],
        priority=55
    )

    logger.info(f"注册了 {len(TOOL_REGISTRY)} 个内置工具")


def register_workflow_tools() -> None:
    """注册来自 backend.tools 的工作流工具"""
    try:
        from backend.tools import get_workflow_tool_registry, execute_workflow_tool

        workflow_list = get_workflow_tool_registry()
        registered = 0
        for item in workflow_list:
            if not isinstance(item, dict):
                continue

            func_def = item.get("function", item)
            tool_name = func_def.get("name")
            if not tool_name:
                continue

            if tool_name in TOOL_REGISTRY:
                continue

            def _make_handler(name: str):
                def handler(**kwargs):
                    import asyncio
                    result_str = execute_workflow_tool(name, kwargs)
                    import json
                    try:
                        return json.loads(result_str)
                    except (json.JSONDecodeError, TypeError):
                        return {"success": True, "raw": result_str}
                return handler

            TOOL_REGISTRY[tool_name] = ToolDefinition(
                name=tool_name,
                description=func_def.get("description", ""),
                input_schema=func_def.get("parameters", {}),
                output_schema={"type": "object"},
                handler=_make_handler(tool_name),
                required_intents=["price_list_export", "data_export"],
                priority=40
            )
            registered += 1
        logger.info(f"注册了 {registered} 个工作流工具")
    except Exception as e:
        logger.warning(f"注册工作流工具失败: {e}")


def initialize_tools() -> None:
    """初始化所有内置工具"""
    register_builtin_tools()
    register_workflow_tools()


_initialized = False


def ensure_tools_initialized() -> None:
    global _initialized
    if not _initialized:
        initialize_tools()
        _initialized = True
