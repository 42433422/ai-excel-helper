"""
工具表目录：供 GET /api/tools、/api/db-tools、/api/tool-categories。
与 XCAGI app.services.tools_directory 默认清单对齐；无 products 库 ai_tools 表时仅用内置数据。
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

_VIEW_ACTIONS = [{"name": "view", "label": "查看"}]


def _default_categories() -> List[Dict[str, Any]]:
    rows = [
        ("products", "产品管理", "产品、价格与导入导出", "box", 10),
        ("customers", "客户/购买单位", "购买单位与联系人", "users", 20),
        ("orders", "出货单", "发货与出货记录", "truck", 30),
        ("excel", "Excel 处理", "模板与网格提取", "file-excel", 40),
        ("ocr", "图片 OCR", "聊天内图片识别", "image", 50),
        ("materials", "原材料仓库", "原料与库存", "cubes", 60),
        ("print", "标签打印", "打印与标签", "print", 70),
        ("database", "数据库管理", "数据与备份相关", "database", 80),
        ("system", "系统设置", "配置与意图包", "cog", 90),
        ("inventory", "库存", "库存查询与调整", "warehouse", 100),
        ("purchase", "采购", "采购订单与供应商", "cart", 110),
    ]
    out: List[Dict[str, Any]] = []
    for i, (key, name, desc, icon, sort_order) in enumerate(rows, start=1):
        out.append(
            {
                "id": i,
                "category_name": name,
                "category_key": key,
                "description": desc,
                "icon": icon,
                "sort_order": sort_order,
                "is_active": 1,
            }
        )
    return out


def _default_tools(categories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    key_to_id = {c["category_key"]: c["id"] for c in categories}

    def cat(key: str) -> Dict[str, Any]:
        cid = key_to_id.get(key, key_to_id.get("system", 1))
        base = next((c for c in categories if c["id"] == cid), categories[0])
        return {
            "id": base["id"],
            "category_name": base["category_name"],
            "category_key": base["category_key"],
            "description": base.get("description") or "",
            "icon": base.get("icon") or "",
        }

    specs: List[Tuple[str, str, str, str]] = [
        ("products", "产品管理", "products", "维护产品型号、价格与单位"),
        ("customers", "客户/购买单位", "customers", "维护购买单位与联系方式"),
        ("orders", "出货单", "orders", "创建与查询发货/出货单"),
        ("materials", "原材料", "materials", "原材料档案与库存"),
        ("print", "标签打印", "print", "标签与打印任务"),
        ("shipment_template", "Excel 模板", "excel", "模板预览与导出配置"),
        ("excel_decompose", "模板网格提取", "excel", "从 Excel 提取字段网格"),
        ("ocr", "图片 OCR", "ocr", "在聊天中上传图片做 OCR"),
        ("wechat", "微信联系人", "customers", "同步与查看微信侧联系人"),
        ("database", "数据库与备份", "database", "数据目录与健康检查（见设置）"),
        ("system", "系统设置", "system", "行业、意图包与测试库等"),
    ]
    tools: List[Dict[str, Any]] = []
    for route_key, title, ckey, desc in specs:
        tools.append(
            {
                "id": route_key,
                "tool_key": route_key,
                "name": title,
                "description": desc,
                "category": cat(ckey),
                "actions": list(_VIEW_ACTIONS),
                "parameters": [],
            }
        )
    return tools


def get_tool_categories_payload() -> Dict[str, Any]:
    return {"success": True, "categories": _default_categories()}


def get_tools_payload() -> Dict[str, Any]:
    cats = _default_categories()
    return {"success": True, "tools": _default_tools(cats)}
