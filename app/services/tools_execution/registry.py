from __future__ import annotations

CANONICAL_ACTIONS = {
    "view",
    "list",
    "query",
    "create",
    "update",
    "delete",
    "batch_delete",
    "import",
    "export",
    "analyze",
    "extract",
    "preview",
    "execute",
}

ACTION_ALIASES = {
    "查找": "query",
    "查询": "query",
    "搜索": "query",
    "search": "query",
    "find": "query",
    "add": "create",
    "新增": "create",
    "添加": "create",
    "create": "create",
    "modify": "update",
    "edit": "update",
    "更新": "update",
    "删除": "delete",
    "remove": "delete",
    "del": "delete",
    "删除批量": "batch_delete",
    "batch-delete": "batch_delete",
    "batch_delete": "batch_delete",
    "导入": "import",
    "导出": "export",
    "分析": "analyze",
    "提取": "extract",
    "执行": "execute",
    "exec": "execute",
    "run": "execute",
}

REQUIRED_PARAMS_BY_TOOL_ACTION = {
    ("products", "create"): ["name_or_model", "unit_name"],
    ("products", "update"): ["id"],
    ("products", "delete"): ["id"],
    ("materials", "create"): ["name"],
    ("materials", "update"): ["id"],
    ("materials", "delete"): ["id"],
    ("materials", "batch_delete"): ["ids"],
    ("shipment_records", "update"): ["id"],
    ("shipment_records", "delete"): ["id"],
    ("template_extract", "extract"): ["file_path"],
    ("print", "print_label"): ["file_path"],
    ("print", "print_document"): ["file_path"],
    ("printer_list", "set_default"): ["printer_name"],
    ("wechat", "refresh_contact_cache"): [],
    ("wechat", "refresh_messages_cache"): [],
}


def _normalize_action(action: str, params: dict | None = None) -> str:
    raw = str(action or "").strip()
    if not raw:
        return "view"
    lowered = raw.lower()
    normalized = ACTION_ALIASES.get(raw) or ACTION_ALIASES.get(lowered) or lowered
    if normalized in CANONICAL_ACTIONS:
        return normalized
    if params and str(params.get("action") or "").strip():
        nested = str(params.get("action")).strip()
        nested_lower = nested.lower()
        mapped = ACTION_ALIASES.get(nested) or ACTION_ALIASES.get(nested_lower) or nested_lower
        if mapped in CANONICAL_ACTIONS:
            return mapped
    return normalized


def _validate_required_params(tool_id: str, action: str, params: dict | None) -> tuple[bool, str]:
    required = REQUIRED_PARAMS_BY_TOOL_ACTION.get(
        (str(tool_id or "").strip(), str(action or "").strip()), []
    )
    if not required:
        return True, ""
    payload = dict(params or {})
    missing = []
    for key in required:
        value = payload.get(key)
        if value is None:
            missing.append(key)
            continue
        if isinstance(value, str) and not value.strip():
            missing.append(key)
            continue
        if isinstance(value, list) and len(value) == 0:
            missing.append(key)
            continue
    if missing:
        return False, f"缺少参数：{', '.join(missing)}"
    return True, ""


def get_workflow_tool_registry() -> dict:
    return {
        "customers": {
            "description": "购买单位管理",
            "availability": "shared",
            "actions": {
                "query": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "shared",
                },
                "ensure_exists": {
                    "risk": "medium",
                    "idempotent": True,
                    "required_params": ["unit_name"],
                    "availability": "shared",
                },
                "create": {
                    "risk": "medium",
                    "idempotent": False,
                    "required_params": ["unit_name"],
                    "availability": "shared",
                },
            },
        },
        "products": {
            "description": "产品管理",
            "availability": "shared",
            "actions": {
                "query": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "shared",
                },
                "exists": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "shared",
                },
                "create": {
                    "risk": "medium",
                    "idempotent": False,
                    "required_params": ["name_or_model", "unit_name"],
                    "availability": "shared",
                },
            },
        },
        "materials": {
            "description": "原材料仓库与列表管理",
            "availability": "shared",
            "actions": {
                "list": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "shared",
                },
                "query": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "shared",
                },
                "create": {
                    "risk": "medium",
                    "idempotent": False,
                    "required_params": ["name"],
                    "availability": "shared",
                },
                "update": {
                    "risk": "medium",
                    "idempotent": False,
                    "required_params": ["id"],
                    "availability": "shared",
                },
                "delete": {
                    "risk": "high",
                    "idempotent": False,
                    "required_params": ["id"],
                    "availability": "shared",
                },
                "batch_delete": {
                    "risk": "high",
                    "idempotent": False,
                    "required_params": ["ids"],
                    "availability": "shared",
                },
                "export": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "shared",
                },
            },
        },
        "shipment_records": {
            "description": "出货记录管理",
            "availability": "shared",
            "actions": {
                "list": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "shared",
                },
                "query": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "shared",
                },
                "update": {
                    "risk": "medium",
                    "idempotent": False,
                    "required_params": ["id"],
                    "availability": "shared",
                },
                "delete": {
                    "risk": "high",
                    "idempotent": False,
                    "required_params": ["id"],
                    "availability": "shared",
                },
                "export": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "shared",
                },
            },
        },
        "business_docking": {
            "description": "业务对接与模板网格提取",
            "availability": "shared",
            "actions": {
                "view": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "shared",
                },
                "extract": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": ["file_path"],
                    "availability": "shared",
                },
                "preview": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": ["file_path"],
                    "availability": "shared",
                },
            },
        },
        "template_preview": {
            "description": "模板预览与管理",
            "availability": "shared",
            "actions": {
                "view": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "shared",
                },
                "list": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "shared",
                },
                "query": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "shared",
                },
                "create": {
                    "risk": "medium",
                    "idempotent": False,
                    "required_params": [],
                    "availability": "shared",
                },
            },
        },
        "wechat": {
            "description": "微信联系人与消息缓存管理",
            "availability": "shared",
            "actions": {
                "view": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "shared",
                },
                "list": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "shared",
                },
                "query": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "shared",
                },
                "refresh_contact_cache": {
                    "risk": "medium",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "shared",
                },
                "refresh_messages_cache": {
                    "risk": "medium",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "shared",
                },
            },
        },
        "print": {
            "description": "标签与文档打印",
            "availability": "shared",
            "actions": {
                "view": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "shared",
                },
                "list": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "shared",
                },
                "query": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "shared",
                },
                "print_label": {
                    "risk": "high",
                    "idempotent": False,
                    "required_params": ["file_path"],
                    "availability": "shared",
                },
                "print_document": {
                    "risk": "high",
                    "idempotent": False,
                    "required_params": ["file_path"],
                    "availability": "shared",
                },
                "test": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": ["printer_name"],
                    "availability": "shared",
                },
            },
        },
        "printer_list": {
            "description": "打印机列表与默认打印机设置",
            "availability": "shared",
            "actions": {
                "view": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "shared",
                },
                "list": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "shared",
                },
                "set_default": {
                    "risk": "medium",
                    "idempotent": False,
                    "required_params": ["printer_name"],
                    "availability": "shared",
                },
            },
        },
        "settings": {
            "description": "系统设置与运行环境配置",
            "availability": "shared",
            "actions": {
                "view": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "shared",
                },
                "query": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "shared",
                },
                "get_system_info": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "shared",
                },
                "get_startup_config": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "shared",
                },
                "enable_startup": {
                    "risk": "medium",
                    "idempotent": False,
                    "required_params": [],
                    "availability": "shared",
                },
                "disable_startup": {
                    "risk": "medium",
                    "idempotent": False,
                    "required_params": [],
                    "availability": "shared",
                },
            },
        },
        "normal_slot_dispatch": {
            "description": "普通版槽位：产品查询浮窗、发货单编号预览（与 /api/ai/unified_chat 同源）",
            "availability": "normal_only",
            "actions": {
                "product_query": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "normal_only",
                },
                "shipment_preview": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": [],
                    "availability": "normal_only",
                },
            },
        },
        "excel_analysis": {
            "description": "Excel文件智能分析：读取内容、分析结构、统计汇总、自然语言查询",
            "availability": "shared",
            "actions": {
                "read": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": ["file_path"],
                    "availability": "shared",
                },
                "structure": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": ["file_path"],
                    "availability": "shared",
                },
                "query": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": ["file_path", "question"],
                    "availability": "shared",
                },
                "statistics": {
                    "risk": "low",
                    "idempotent": True,
                    "required_params": ["file_path"],
                    "availability": "shared",
                },
            },
        },
    }
