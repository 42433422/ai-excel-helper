"""工具目录默认数据与 payload 组装。

Phase 3 从 ``app.legacy.tools_directory_compat`` 迁入。
"""

from __future__ import annotations

DEFAULT_TOOL_CATEGORIES = [
    {
        "id": 10,
        "category_key": "planner",
        "name": "AI Planner",
        "description": "对话 Planner 可调用的后端工具",
    },
    {"id": 1, "category_key": "products", "name": "产品管理", "description": "产品与型号维护"},
    {"id": 2, "category_key": "customers", "name": "客户管理", "description": "客户与购买单位维护"},
    {"id": 3, "category_key": "orders", "name": "出货单", "description": "出货单与记录管理"},
    {"id": 4, "category_key": "excel", "name": "Excel处理", "description": "模板与结构化处理"},
    {"id": 5, "category_key": "ocr", "name": "图片OCR", "description": "图片识别与对话入口"},
    {"id": 6, "category_key": "materials", "name": "原材料仓库", "description": "原材料管理"},
    {"id": 7, "category_key": "print", "name": "标签打印", "description": "打印与打印机管理"},
    {"id": 8, "category_key": "database", "name": "数据库管理", "description": "数据库健康与维护"},
    {"id": 9, "category_key": "system", "name": "系统设置", "description": "系统配置与开关"},
]


def _tool(
    tool_id: str,
    name: str,
    description: str,
    category_key: str,
    *,
    aliases: list[str] | None = None,
    roles: list[str] | None = None,
) -> dict:
    """
    Args:
        roles: 允许访问该工具的角色列表，例如 ['admin', 'manager']。
               None 或空列表表示所有角色可见。
    """
    return {
        "id": tool_id,
        "tool_key": tool_id,
        "name": name,
        "description": description,
        "kind": "app_entry",
        "planner_callable": False,
        "aliases": list(aliases or []),
        "roles": list(roles or []),
        "category": {
            "category_key": category_key,
            "name": next(
                (c["name"] for c in DEFAULT_TOOL_CATEGORIES if c["category_key"] == category_key),
                category_key,
            ),
        },
    }


DEFAULT_TOOLS = [
    _tool("products", "产品管理", "产品查询、新增与维护", "products"),
    _tool("customers", "客户管理", "客户与购买单位管理", "customers"),
    _tool("orders", "出货单", "出货单创建、查询与管理", "orders"),
    _tool("shipment_template", "出货单模板", "模板维护与套用", "excel"),
    _tool("excel_decompose", "Excel处理", "Excel模板分解与词条提取", "excel"),
    _tool("ocr", "图片OCR", "图片识别与文字提取", "ocr"),
    _tool("wechat", "微信联系人", "微信联系人与相关流程", "customers"),
    _tool("materials", "原材料仓库", "原材料信息维护与查询", "materials"),
    _tool("print", "标签打印", "标签打印与输出", "print"),
    _tool("printer_list", "打印机列表", "打印机状态与默认设备设置", "print"),
    _tool("database", "数据库管理", "数据库状态、校验与维护", "database"),
    _tool("settings", "系统设置", "系统参数与运行配置", "system"),
]


def _planner_tools_from_registry() -> list[dict]:
    """OpenAI function 规格，与 legacy_chat_adapter / execute_workflow_tool 一致。"""
    try:
        from app.mod_sdk.planner_tools import (
            get_planner_chat_tool_registry,
            is_planner_tools_via_mod_enabled,
        )

        if is_planner_tools_via_mod_enabled():
            reg = get_planner_chat_tool_registry()
        else:
            from app.application.tools.workflow import get_workflow_tool_registry

            reg = get_workflow_tool_registry()
    except Exception:
        return []
    out: list[dict] = []
    for spec in reg:
        if not isinstance(spec, dict):
            continue
        fn = spec.get("function")
        if not isinstance(fn, dict):
            continue
        name = str(fn.get("name") or "").strip()
        if not name:
            continue
        desc = str(fn.get("description") or "").strip()
        out.append(
            {
                "id": f"planner:{name}",
                "tool_key": name,
                "name": name,
                "description": desc or "（无描述）",
                "kind": "planner_backend",
                "planner_callable": True,
                "parameters": fn.get("parameters"),
                "category": {"category_key": "planner", "name": "AI Planner"},
            }
        )
    return out


def get_tools_payload() -> dict:
    planner_tools = _planner_tools_from_registry()
    return {
        "success": True,
        "tools": DEFAULT_TOOLS,
        "data": DEFAULT_TOOLS,
        "planner_tools": planner_tools,
    }


def get_tool_categories_payload() -> dict:
    return {"success": True, "categories": DEFAULT_TOOL_CATEGORIES, "data": DEFAULT_TOOL_CATEGORIES}


__all__ = [
    "DEFAULT_TOOL_CATEGORIES",
    "DEFAULT_TOOLS",
    "get_tools_payload",
    "get_tool_categories_payload",
]
