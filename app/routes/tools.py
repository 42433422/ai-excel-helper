"""
工具管理路由

提供工具列表、分类管理等 API。
"""

import logging
import os

from flasgger import swag_from
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)
tools_bp = Blueprint('tools', __name__)

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
    required = REQUIRED_PARAMS_BY_TOOL_ACTION.get((str(tool_id or "").strip(), str(action or "").strip()), [])
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
    """供动态工作流规划器使用的工具注册表（schema + risk + availability）。"""
    return {
        "customers": {
            "description": "购买单位管理",
            "availability": "shared",
            "actions": {
                "query": {"risk": "low", "idempotent": True, "required_params": [], "availability": "shared"},
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
                "query": {"risk": "low", "idempotent": True, "required_params": [], "availability": "shared"},
                "exists": {"risk": "low", "idempotent": True, "required_params": [], "availability": "shared"},
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
                "list": {"risk": "low", "idempotent": True, "required_params": [], "availability": "shared"},
                "query": {"risk": "low", "idempotent": True, "required_params": [], "availability": "shared"},
                "create": {"risk": "medium", "idempotent": False, "required_params": ["name"], "availability": "shared"},
                "update": {"risk": "medium", "idempotent": False, "required_params": ["id"], "availability": "shared"},
                "delete": {"risk": "high", "idempotent": False, "required_params": ["id"], "availability": "shared"},
                "batch_delete": {"risk": "high", "idempotent": False, "required_params": ["ids"], "availability": "shared"},
                "export": {"risk": "low", "idempotent": True, "required_params": [], "availability": "shared"},
            },
        },
        "shipment_records": {
            "description": "出货记录管理",
            "availability": "shared",
            "actions": {
                "list": {"risk": "low", "idempotent": True, "required_params": [], "availability": "shared"},
                "query": {"risk": "low", "idempotent": True, "required_params": [], "availability": "shared"},
                "update": {"risk": "medium", "idempotent": False, "required_params": ["id"], "availability": "shared"},
                "delete": {"risk": "high", "idempotent": False, "required_params": ["id"], "availability": "shared"},
                "export": {"risk": "low", "idempotent": True, "required_params": [], "availability": "shared"},
            },
        },
        "business_docking": {
            "description": "业务对接与模板网格提取",
            "availability": "shared",
            "actions": {
                "view": {"risk": "low", "idempotent": True, "required_params": [], "availability": "shared"},
                "extract": {"risk": "low", "idempotent": True, "required_params": ["file_path"], "availability": "shared"},
                "preview": {"risk": "low", "idempotent": True, "required_params": ["file_path"], "availability": "shared"},
            },
        },
        "template_preview": {
            "description": "模板预览与管理",
            "availability": "shared",
            "actions": {
                "view": {"risk": "low", "idempotent": True, "required_params": [], "availability": "shared"},
                "list": {"risk": "low", "idempotent": True, "required_params": [], "availability": "shared"},
                "query": {"risk": "low", "idempotent": True, "required_params": [], "availability": "shared"},
                "create": {"risk": "medium", "idempotent": False, "required_params": [], "availability": "shared"},
            },
        },
        "wechat": {
            "description": "微信联系人与消息缓存管理",
            "availability": "shared",
            "actions": {
                "view": {"risk": "low", "idempotent": True, "required_params": [], "availability": "shared"},
                "list": {"risk": "low", "idempotent": True, "required_params": [], "availability": "shared"},
                "query": {"risk": "low", "idempotent": True, "required_params": [], "availability": "shared"},
                "refresh_contact_cache": {"risk": "medium", "idempotent": True, "required_params": [], "availability": "shared"},
                "refresh_messages_cache": {"risk": "medium", "idempotent": True, "required_params": [], "availability": "shared"},
            },
        },
        "print": {
            "description": "标签与文档打印",
            "availability": "shared",
            "actions": {
                "view": {"risk": "low", "idempotent": True, "required_params": [], "availability": "shared"},
                "list": {"risk": "low", "idempotent": True, "required_params": [], "availability": "shared"},
                "query": {"risk": "low", "idempotent": True, "required_params": [], "availability": "shared"},
                "print_label": {"risk": "high", "idempotent": False, "required_params": ["file_path"], "availability": "shared"},
                "print_document": {"risk": "high", "idempotent": False, "required_params": ["file_path"], "availability": "shared"},
                "test": {"risk": "low", "idempotent": True, "required_params": ["printer_name"], "availability": "shared"},
            },
        },
        "printer_list": {
            "description": "打印机列表与默认打印机设置",
            "availability": "shared",
            "actions": {
                "view": {"risk": "low", "idempotent": True, "required_params": [], "availability": "shared"},
                "list": {"risk": "low", "idempotent": True, "required_params": [], "availability": "shared"},
                "set_default": {"risk": "medium", "idempotent": False, "required_params": ["printer_name"], "availability": "shared"},
            },
        },
        "settings": {
            "description": "系统设置与运行环境配置",
            "availability": "shared",
            "actions": {
                "view": {"risk": "low", "idempotent": True, "required_params": [], "availability": "shared"},
                "query": {"risk": "low", "idempotent": True, "required_params": [], "availability": "shared"},
                "get_system_info": {"risk": "low", "idempotent": True, "required_params": [], "availability": "shared"},
                "get_startup_config": {"risk": "low", "idempotent": True, "required_params": [], "availability": "shared"},
                "enable_startup": {"risk": "medium", "idempotent": False, "required_params": [], "availability": "shared"},
                "disable_startup": {"risk": "medium", "idempotent": False, "required_params": [], "availability": "shared"},
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


def execute_registered_workflow_tool(tool_id: str, action: str, params: dict | None = None) -> dict:
    """
    统一 dispatcher（供 WorkflowEngine 与 /api/tools/execute 复用）。
    """
    from app.application.normal_chat_dispatch import (
        resolve_tool_execution_profile,
        run_normal_slot_product_query_from_message,
        run_normal_slot_shipment_preview,
        run_workflow_products_query_normal_profile,
    )

    params = dict(params or {})
    runtime_context = dict(params.pop("_runtime_context", None) or {})
    profile = resolve_tool_execution_profile(runtime_context)
    user_message = str(runtime_context.get("message") or "").strip()

    if tool_id == "normal_slot_dispatch":
        if action == "product_query":
            text = user_message or str(params.get("message") or "").strip()
            return run_normal_slot_product_query_from_message(text)
        if action == "shipment_preview":
            order_text = str(params.get("order_text") or user_message or "").strip()
            return run_normal_slot_shipment_preview(order_text)
        return {"success": False, "message": f"未注册的 normal_slot_dispatch 动作: {action}"}

    if tool_id == "customers":
        from app.application import get_customer_app_service

        svc = get_customer_app_service()
        unit_name = str(
            params.get("unit_name")
            or params.get("customer_name")
            or params.get("name")
            or ""
        ).strip()
        if action == "query":
            keyword = str(params.get("keyword") or unit_name or "").strip()
            result = svc.get_all(keyword=keyword, page=1, per_page=20)
            return {"success": bool(result.get("success")), "data": result.get("data", []), "raw": result}

        if action == "ensure_exists":
            if not unit_name:
                return {"success": False, "message": "缺少 unit_name"}
            matched = svc.match_purchase_unit(unit_name)
            if matched:
                return {"success": True, "exists": True, "unit_name": matched.unit_name}
            create_result = svc.create({"customer_name": unit_name})
            if create_result.get("success"):
                return {"success": True, "exists": False, "created": True, "unit_name": unit_name}
            msg = str(create_result.get("message") or "")
            if "已存在" in msg:
                return {"success": True, "exists": True, "unit_name": unit_name}
            return {"success": False, "message": msg or "创建单位失败"}

        if action == "create":
            if not unit_name:
                return {"success": False, "message": "缺少 unit_name"}
            create_result = svc.create({"customer_name": unit_name})
            if create_result.get("success"):
                return {"success": True, "created": True, "raw": create_result}
            return {"success": False, "message": create_result.get("message") or "创建失败"}

    if tool_id == "products":
        from app.services import get_products_service

        svc = get_products_service()
        unit_name = str(params.get("unit_name") or "").strip()
        model_number = str(params.get("model_number") or "").strip().upper()
        product_name = str(params.get("product_name") or params.get("name") or "").strip()
        keyword = str(params.get("keyword") or product_name or model_number or "").strip()

        if action == "query":
            if profile == "normal":
                return run_workflow_products_query_normal_profile(
                    user_message,
                    node_params=params,
                    per_page=20,
                )
            result = svc.get_products(
                unit_name=unit_name or None,
                model_number=model_number or None,
                keyword=keyword or None,
                page=1,
                per_page=20,
            )
            return {"success": bool(result.get("success")), "data": result.get("data", []), "raw": result}

        if action == "exists":
            result = svc.get_products(
                unit_name=unit_name or None,
                model_number=model_number or None,
                keyword=keyword or None,
                page=1,
                per_page=10,
            )
            rows = result.get("data") or []
            exists = False
            for row in rows:
                row_name = str(row.get("name") or row.get("product_name") or "").strip()
                row_model = str(row.get("model_number") or "").strip().upper()
                if model_number and row_model == model_number:
                    exists = True
                    break
                if product_name and row_name == product_name:
                    exists = True
                    break
            return {"success": True, "exists": exists, "matched_count": len(rows)}

        if action == "create":
            name_or_model = str(params.get("name_or_model") or product_name or model_number).strip()
            if not name_or_model or not unit_name:
                return {"success": False, "message": "缺少 name_or_model 或 unit_name"}
            price = params.get("unit_price", params.get("price", 0.0))
            try:
                price = float(price)
            except Exception:
                price = 0.0
            create_result = svc.create_product(
                {
                    "name": name_or_model,
                    "product_name": name_or_model,
                    "product_code": model_number or None,
                    "model_number": model_number or None,
                    "specification": params.get("specification"),
                    "unit_price": price,
                    "price": price,
                    "unit": unit_name,
                }
            )
            if create_result.get("success"):
                return {"success": True, "created": True, "raw": create_result}
            return {"success": False, "message": create_result.get("message") or "创建失败"}

    if tool_id == "materials":
        from app.application import get_material_application_service

        svc = get_material_application_service()
        if action in ("list", "query"):
            result = svc.get_all_materials(
                search=str(params.get("search") or params.get("keyword") or "").strip(),
                category=str(params.get("category") or "").strip() or None,
                page=int(params.get("page") or 1),
                per_page=int(params.get("per_page") or 20),
            )
            return result
        if action == "create":
            payload = dict(params or {})
            payload.setdefault("name", str(payload.get("name") or payload.get("material_name") or "").strip())
            return svc.create_material(payload)
        if action == "update":
            material_id = int(params.get("id"))
            payload = {k: v for k, v in params.items() if k != "id"}
            return svc.update_material(material_id, **payload)
        if action == "delete":
            return svc.delete_material(int(params.get("id")))
        if action == "batch_delete":
            raw_ids = params.get("ids") or params.get("material_ids") or []
            ids = [int(x) for x in raw_ids if str(x).strip()]
            return svc.batch_delete_materials(ids)
        if action == "export":
            return svc.export_to_excel(
                search=str(params.get("search") or params.get("keyword") or "").strip() or None,
                category=str(params.get("category") or "").strip() or None,
                template_id=params.get("template_id"),
            )

    if tool_id == "shipment_records":
        from app.bootstrap import get_shipment_app_service

        svc = get_shipment_app_service()
        if action in ("list", "query"):
            unit = str(params.get("unit") or params.get("unit_name") or "").strip() or None
            return {"success": True, "data": svc.get_shipment_records(unit)}
        if action == "update":
            record_id = int(params.get("id"))
            payload = {k: v for k, v in params.items() if k != "id"}
            return svc.update_shipment_record(record_id=record_id, **payload)
        if action == "delete":
            return svc.delete_shipment_record(int(params.get("id")))
        if action == "export":
            return svc.export_shipment_records(
                unit_name=str(params.get("unit") or params.get("unit_name") or "").strip() or None,
                template_id=params.get("template_id"),
                status_filter=params.get("status"),
            )

    if tool_id in ("business_docking", "template_extract"):
        if action in ("view",):
            return {"success": True, "redirect": "/console?view=business-docking"}
        file_path = str(params.get("file_path") or "").strip()
        if not file_path:
            return {"success": False, "message": "缺少参数：file_path"}
        from app.routes.templates import (
            _extract_excel_all_sheets_preview,
            _extract_excel_grid_preview,
            _extract_excel_grid_style_cache,
            _extract_structured_excel_preview,
            _list_excel_sheet_names,
        )
        if not os.path.exists(file_path):
            return {"success": False, "message": f"文件不存在：{file_path}"}
        sheet_name = str(params.get("sheet_name") or "").strip() or None
        structured = _extract_structured_excel_preview(file_path, sheet_name=sheet_name, sample_limit=8)
        grid_preview = _extract_excel_grid_preview(file_path, sheet_name=sheet_name, max_rows=24, max_cols=14)
        style_cache = _extract_excel_grid_style_cache(file_path, sheet_name=sheet_name, max_rows=24, max_cols=14)
        all_sheets = _extract_excel_all_sheets_preview(file_path, sample_limit=8, max_rows=24, max_cols=14)
        return {
            "success": True,
            "file_path": file_path,
            "sheet_names": _list_excel_sheet_names(file_path),
            "fields": structured.get("fields") or [],
            "sample_rows": structured.get("sample_rows") or [],
            "grid_preview": grid_preview,
            "grid_style_cache": style_cache,
            "sheets": all_sheets,
        }

    if tool_id == "template_preview":
        if action == "view":
            return {"success": True, "redirect": "/console?view=template-preview"}
        from app.application import get_template_app_service
        svc = get_template_app_service()
        if action in ("list", "query"):
            result = svc.get_templates()
            if isinstance(result, dict):
                return result
            return {"success": True, "data": result}
        if action == "create":
            import json
            import re
            import uuid
            from datetime import datetime
            from sqlalchemy import text
            from app.db.session import get_db
            from app.routes.templates import _ensure_template_tables_ready, _infer_business_scope, _validate_required_terms

            excel_analysis = params.get("excel_analysis")
            if not isinstance(excel_analysis, dict):
                excel_analysis = runtime_context.get("excel_analysis")
            if not isinstance(excel_analysis, dict):
                fallback_ctx = runtime_context.get("last_excel_analysis_context")
                if isinstance(fallback_ctx, dict):
                    excel_analysis = fallback_ctx.get("result") if isinstance(fallback_ctx.get("result"), dict) else fallback_ctx
            excel_analysis = excel_analysis if isinstance(excel_analysis, dict) else {}

            sheets = excel_analysis.get("sheets")
            if not isinstance(sheets, list):
                preview_data = excel_analysis.get("preview_data") if isinstance(excel_analysis.get("preview_data"), dict) else {}
                sheets = preview_data.get("all_sheets") if isinstance(preview_data.get("all_sheets"), list) else []

            sheet_index = params.get("sheet_index")
            sheet_name = str(params.get("sheet_name") or "").strip()
            if sheet_index is None:
                text_message = str(params.get("order_text") or runtime_context.get("message") or "")
                m = re.search(r"第\s*(\d+)\s*(个)?\s*(sheet|表)", text_message, flags=re.I)
                if m:
                    try:
                        sheet_index = int(m.group(1))
                    except Exception:
                        sheet_index = None

            selected_sheet = None
            if isinstance(sheet_index, int) and sheet_index > 0:
                for s in sheets:
                    if int(s.get("sheet_index") or 0) == sheet_index:
                        selected_sheet = s
                        break
            if selected_sheet is None and sheet_name:
                for s in sheets:
                    if str(s.get("sheet_name") or "").strip() == sheet_name:
                        selected_sheet = s
                        break
            if selected_sheet is None and sheets:
                selected_sheet = sheets[0]

            if not selected_sheet:
                return {"success": False, "message": "未找到可用的 sheet 分析结果，请先执行分析Excel。"}

            picked_sheet_name = str(selected_sheet.get("sheet_name") or "").strip() or "Sheet1"
            template_name = str(params.get("name") or params.get("template_name") or "").strip()
            if not template_name:
                template_name = f"{picked_sheet_name}-模板"

            fields = selected_sheet.get("fields") if isinstance(selected_sheet.get("fields"), list) else []
            preview_data = {
                "sheet_name": picked_sheet_name,
                "selected_sheet_name": picked_sheet_name,
                "sample_rows": selected_sheet.get("sample_rows") if isinstance(selected_sheet.get("sample_rows"), list) else [],
                "grid_preview": selected_sheet.get("grid_preview") if isinstance(selected_sheet.get("grid_preview"), dict) else {},
                "grid_style_cache": selected_sheet.get("style_cache") if isinstance(selected_sheet.get("style_cache"), dict) else {},
            }
            template_type = str(params.get("template_type") or "Excel").strip()
            business_scope = str(params.get("business_scope") or _infer_business_scope(template_type) or "").strip()
            source = str(params.get("source") or "ai-natural-language").strip() or "ai-natural-language"
            file_path = str(params.get("file_path") or excel_analysis.get("file_path") or "").strip() or None

            if business_scope:
                valid, missing_terms = _validate_required_terms({}, fields, business_scope)
                if not valid:
                    return {
                        "success": False,
                        "message": "必填字段未匹配，不能保存模板",
                        "business_scope": business_scope,
                        "missing_terms": missing_terms,
                    }

            analyzed_data = {
                "category": "excel",
                "source": source,
                "business_scope": business_scope,
                "fields": fields,
                "preview_data": preview_data,
            }
            editable_config = fields
            business_rules = {
                "business_scope": business_scope,
                "source": source,
                "selected_sheet_name": picked_sheet_name,
            }

            _ensure_template_tables_ready()
            template_key = f"TPL_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8].upper()}"
            with get_db() as db:
                result = db.execute(
                    text("""
                        INSERT INTO templates (
                            template_key, template_name, template_type,
                            original_file_path, analyzed_data, editable_config,
                            zone_config, merged_cells_config, style_config,
                            business_rules, is_active
                        ) VALUES (
                            :template_key, :template_name, :template_type,
                            :original_file_path, :analyzed_data, :editable_config,
                            :zone_config, :merged_cells_config, :style_config,
                            :business_rules, :is_active
                        )
                    """),
                    {
                        "template_key": template_key,
                        "template_name": template_name,
                        "template_type": template_type,
                        "original_file_path": file_path,
                        "analyzed_data": json.dumps(analyzed_data, ensure_ascii=False),
                        "editable_config": json.dumps(editable_config, ensure_ascii=False),
                        "zone_config": json.dumps({}, ensure_ascii=False),
                        "merged_cells_config": json.dumps({}, ensure_ascii=False),
                        "style_config": json.dumps({}, ensure_ascii=False),
                        "business_rules": json.dumps(business_rules, ensure_ascii=False),
                        "is_active": 1,
                    },
                )
                template_id = result.lastrowid
                db.commit()

            return {
                "success": True,
                "message": "已按指定 sheet 加入模板库",
                "template": {
                    "id": f"db:{template_id}",
                    "db_id": template_id,
                    "name": template_name,
                    "template_type": template_type,
                    "business_scope": business_scope,
                    "source": source,
                    "fields": fields,
                    "preview_data": preview_data,
                },
            }

    if tool_id == "wechat":
        from app.application import get_wechat_contact_app_service
        svc = get_wechat_contact_app_service()
        if action == "view":
            return {"success": True, "redirect": "/console?view=wechat-contacts"}
        if action in ("list", "query"):
            return {
                "success": True,
                "data": svc.get_contacts(
                    contact_type=str(params.get("type") or "all"),
                    keyword=str(params.get("keyword") or "").strip() or None,
                    limit=int(params.get("limit") or 100),
                ),
            }
        if action in ("refresh_contact_cache", "refresh_messages_cache"):
            from app.routes.wechat_contacts import _ensure_decrypted_db
            return _ensure_decrypted_db()

    if tool_id == "print":
        from app.services import get_printer_service
        svc = get_printer_service()
        if action == "view":
            return {"success": True, "redirect": "/console?view=print"}
        if action in ("list", "query"):
            return svc.get_printers()
        if action == "print_label":
            return svc.print_label(
                str(params.get("file_path") or "").strip(),
                params.get("printer_name"),
                int(params.get("copies") or 1),
            )
        if action == "print_document":
            return svc.print_document(
                str(params.get("file_path") or "").strip(),
                params.get("printer_name"),
                bool(params.get("use_automation", False)),
            )
        if action == "test":
            return svc.test_printer(str(params.get("printer_name") or "").strip())

    if tool_id == "printer_list":
        from app.services import get_system_service
        svc = get_system_service()
        if action == "view":
            return {"success": True, "redirect": "/console?view=printer-list"}
        if action in ("list", "query"):
            return svc.get_printer_config()
        if action == "set_default":
            return svc.set_default_printer(str(params.get("printer_name") or "").strip())

    if tool_id == "settings":
        from app.services import get_system_service
        svc = get_system_service()
        if action == "view":
            return {"success": True, "redirect": "/console?view=settings"}
        if action in ("query", "get_system_info"):
            return {"success": True, "data": svc.get_system_info()}
        if action == "get_startup_config":
            return {"success": True, "data": svc.get_startup_config()}
        if action == "enable_startup":
            return svc.enable_startup()
        if action == "disable_startup":
            return svc.disable_startup()

    if tool_id == "excel_analysis":
        file_path = str(params.get("file_path") or "").strip()
        if not file_path:
            excel_ctx = runtime_context.get("excel_analysis") if isinstance(runtime_context.get("excel_analysis"), dict) else None
            if not excel_ctx:
                last_ctx = runtime_context.get("last_excel_analysis_context")
                if isinstance(last_ctx, dict):
                    excel_ctx = last_ctx.get("result") if isinstance(last_ctx.get("result"), dict) else last_ctx
            if isinstance(excel_ctx, dict):
                file_path = str(excel_ctx.get("file_path") or "").strip()
        if not file_path:
            return {"success": False, "message": "excel_analysis 缺少 file_path 参数"}

        question = str(params.get("question") or "").strip()

        try:
            from app.infrastructure.skills.excel_toolkit.excel_toolkit import get_excel_toolkit_skill
            from app.infrastructure.skills.excel_analyzer.excel_template_analyzer import get_excel_analyzer_skill
        except ImportError:
            return {"success": False, "message": "Excel Skill 未正确安装"}

        toolkit_skill = get_excel_toolkit_skill()
        analyzer_skill = get_excel_analyzer_skill()

        if action == "read":
            result = toolkit_skill.execute(file_path=file_path, action="view")
            return result

        if action == "structure":
            result = analyzer_skill.execute(file_path=file_path)
            return result

        if action == "statistics":
            view_result = toolkit_skill.execute(file_path=file_path, action="view")
            if not view_result.get("success"):
                return view_result
            content = view_result.get("content") or []
            total_rows = view_result.get("row_count") or 0
            all_values = []
            for row in content:
                for cell in (row.get("cells") or []):
                    v = cell.get("value")
                    if v is not None:
                        try:
                            all_values.append(float(v))
                        except (TypeError, ValueError):
                            pass
            if all_values:
                stats = {"count": len(all_values), "sum": round(sum(all_values), 4), "avg": round(sum(all_values) / len(all_values), 4), "min": min(all_values), "max": max(all_values)}
            else:
                stats = {"count": 0}
            return {"success": True, "file_path": file_path, "total_rows": total_rows, "statistics": stats}

        if action == "query":
            view_result = toolkit_skill.execute(file_path=file_path, action="view")
            if not view_result.get("success"):
                return view_result
            content = view_result.get("content") or []
            if not question:
                return {"success": True, "data": content[:20]}
            question_lower = question.lower()
            if any(kw in question_lower for kw in ["多少", "总和", "总计", "total", "sum"]):
                all_vals = []
                for row in content:
                    for cell in (row.get("cells") or []):
                        try:
                            all_vals.append(float(cell.get("value")))
                        except (TypeError, ValueError):
                            pass
                total = sum(all_vals) if all_vals else 0
                return {"success": True, "answer": f"所有数值总和为 {round(total, 4)}", "total": total}
            if any(kw in question_lower for kw in ["最大", "最高", "max"]):
                all_vals = [float(c.get("value")) for row in content for c in (row.get("cells") or []) if c.get("value") is not None]
                try:
                    mx = max(all_vals)
                    return {"success": True, "answer": f"最大值为 {mx}", "max": mx}
                except ValueError:
                    return {"success": True, "answer": "未找到数值"}
            return {"success": True, "data": content[:20], "message": f"已读取前 {min(20, len(content))} 行数据"}

        return {"success": False, "message": f"未知 excel_analysis action: {action}"}

    return {"success": False, "message": f"未注册的工具动作: {tool_id}.{action}"}


def _parse_order_text(order_text: str) -> dict:
    """
    解析订单文本，提取单位名和产品信息
    
    支持的格式：
    - "发货单七彩乐园 1 桶 9803 规格 12"
    - "送货单公司名称 2 箱产品 A 规格 100"
    - 等
    
    Returns:
        {
            "success": True/False,
            "unit_name": "单位名称",
            "products": [
                {
                    "name": "产品名称",
                    "quantity_tins": 桶数，
                    "tin_spec": 每桶规格，
                    "model_number": "型号"
                }
            ],
            "message": "错误消息（如果有）"
        }
    """
    try:
        import re

        original_text = (order_text or "").strip()

        # 统一移除“发货单/送货单/出货单”关键词本身，避免“关键词在句尾”时把正文截空
        # 例如：“打印七彩乐园9803规格12要3桶发货单”旧逻辑会得到空串。
        text = original_text
        for kw in ["发货单", "送货单", "出货单"]:
            text = text.replace(kw, " ")

        # 轻量清洗：把常见中文标点当作分隔符
        text = (
            text.replace('。', ' ')
            .replace('，', ' ')
            .replace(',', ' ')
            .replace('、', ' ')
            .replace('：', ' ')
            .replace(':', ' ')
        )

        # 归一化粒子：允许“的规格 / 的型号 / 的桶”等 ASR 文本形式
        text = text.replace('的规格', '规格')
        slot_text = (
            original_text.replace('。', ' ')
            .replace('，', ' ')
            .replace(',', ' ')
            .replace('、', ' ')
            .replace('：', ' ')
            .replace(':', ' ')
            .replace('的规格', '规格')
        )
        
        if not text:
            return {
                "success": False,
                "message": "订单文本格式不正确，缺少内容"
            }

        def _parse_cn_number(token: str):
            """解析阿拉伯数字/常见中文数字（支持二十八、三十、十、三桶中的三）。"""
            import re
            t = (token or "").strip()
            if not t:
                return None
            if re.fullmatch(r"\d+(?:\.\d+)?", t):
                return float(t) if "." in t else int(t)

            m = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
            if t in m:
                return m[t]
            if t == "十":
                return 10
            if re.fullmatch(r"[一二两三四五六七八九]十", t):
                return m[t[0]] * 10
            if re.fullmatch(r"十[一二三四五六七八九]", t):
                return 10 + m[t[1]]
            if re.fullmatch(r"[一二两三四五六七八九]十[一二三四五六七八九]", t):
                return m[t[0]] * 10 + m[t[2]]
            return None

        def _cleanup_unit_name(raw: str) -> str:
            import re
            s = (raw or "").strip()
            # 去掉口语填充词/命令词，保留真实单位名
            s = re.sub(r"^(哎|嗯|啊|呃)[，,\s]*", "", s)
            s = re.sub(r"^(帮我|给我|请)?\s*打印(一下)?", "", s)
            s = re.sub(r"^(把|给)?", "", s)
            # 去掉增删改前缀动作词，避免把“再加/减少/删掉/改成”误当单位名
            s = re.sub(
                r"^(再加|还要|继续加|再补|加上|增加|加|减少|减去|减|删掉|删除|去掉|移除|改成|改为|改)\s*",
                "",
                s,
            )
            s = s.replace("发货单", "").replace("送货单", "").replace("出货单", "")
            for token in [
                "打印一下", "打印", "给我", "帮我", "一下", "哎", "嗯", "啊", "呃",
                "桶", "要", "来", "拿", "再加", "还要", "继续加", "再补", "减少",
                "减去", "减", "删掉", "删除", "去掉", "移除", "改成", "改为",
            ]:
                s = s.replace(token, "")
            # 避免把型号 token 残留到单位名中（支持 9000A）
            s = re.sub(r"[0-9A-Za-z-]{3,16}", "", s)
            s = re.sub(r"\s+", "", s)
            s = s.rstrip("的").strip()
            return s

        def _build_missing_prompt(unit_name=None, model_number=None, tin_spec=None, quantity_tins=None):
            missing = []
            if not unit_name:
                missing.append("单位")
            if not quantity_tins:
                missing.append("桶数")
            if not model_number:
                missing.append("编号/型号")
            if not tin_spec:
                missing.append("规格")
            if not missing:
                return None
            recognized = []
            if unit_name:
                recognized.append(f"单位 {unit_name}")
            if model_number:
                recognized.append(f"编号 {model_number}")
            if tin_spec:
                recognized.append(f"规格 {tin_spec}")
            recognized_text = ("（已识别：" + "，".join(recognized) + "）") if recognized else ""
            if missing == ["桶数"]:
                return f"还缺少桶数，请告诉我需要多少桶？{recognized_text}"
            if missing == ["单位"]:
                return f"还缺少单位名称，请补充购买单位。{recognized_text}"
            if missing == ["规格"]:
                return f"还缺少规格，请补充规格数值。{recognized_text}"
            if missing == ["编号/型号"]:
                return f"还缺少编号/型号，请补充。{recognized_text}"
            return f"还缺少{'、'.join(missing)}，请补充。{recognized_text}"

        # 槽位解析（任意语序口语）
        # 示例：给我打印七彩乐园发货单，编号9803，规格二十八，一共三桶
        # 先从全句提取 编号/规格/桶数，再从剩余文本抽单位名
        slot_model = None
        slot_spec = None
        slot_qty_tins = None

        model_token_pattern = r"[0-9A-Za-z-]{3,16}"
        m_model = re.search(rf"(?:编号|型号)\s*(?:是)?\s*[:：]?\s*({model_token_pattern})", slot_text)
        if m_model:
            slot_model = (m_model.group(1) or "").strip().upper()
        else:
            # 兜底：取“规格”前最近的数字串作为型号（如 9803规格28）
            m_model2 = re.search(rf"({model_token_pattern})\s*(?:的)?\s*规格", slot_text)
            if m_model2:
                slot_model = (m_model2.group(1) or "").strip().upper()

        # 规格支持阿拉伯数字与中文数字，并兼容"规格12要3桶/规格二十八三桶"等连读口语
        if "规格" in slot_text:
            after_spec = slot_text.split("规格", 1)[1]
            number_token_pattern = r"(?:\d+(?:\.\d+)?|[一二两三四五六七八九]?十[一二三四五六七八九]?|[一二两三四五六七八九零〇])"
            qty_token_pattern = r"(?:\d+|[一二两三四五六七八九十零〇两]+)"

            # 优先匹配"规格XX(要|来|拿)?三桶"这类连读
            m_spec_qty = re.search(
                rf"^\s*[:：]?\s*({number_token_pattern})(?:\s*(?:要|来|拿|共|一共|总共)?\s*({qty_token_pattern})\s*桶)?",
                after_spec,
            )
            if m_spec_qty:
                spec_num = _parse_cn_number(m_spec_qty.group(1))
                if spec_num is not None:
                    slot_spec = float(spec_num)
                if m_spec_qty.group(2):
                    qty_num = _parse_cn_number(m_spec_qty.group(2))
                    if qty_num is not None:
                        slot_qty_tins = int(qty_num)
            else:
                # 兜底：只提取规格
                m_spec = re.search(r"^\s*[:：]?\s*(\d+(?:\.\d+)?)", after_spec)
                if m_spec:
                    spec_num = _parse_cn_number(m_spec.group(1))
                    if spec_num is not None:
                        slot_spec = float(spec_num)
                else:
                    m_spec_cn = re.search(r"^\s*[:：]?\s*([一二两三四五六七八九]?十[一二三四五六七八九]?|[一二两三四五六七八九零〇])", after_spec)
                    if m_spec_cn:
                        spec_num = _parse_cn_number(m_spec_cn.group(1))
                        if spec_num is not None:
                            slot_spec = float(spec_num)

        # 如果规格连读已经提取了桶数，就不再重复提取（支持“要3桶/来3桶/拿3桶”）
        if slot_qty_tins is None:
            m_qty = re.search(r"(?:一共|总共|共|要|来|拿)?\s*(\d+|[一二两三四五六七八九十零〇两]+)\s*桶", slot_text)
            if m_qty:
                qty_num = _parse_cn_number(m_qty.group(1))
                if qty_num is not None:
                    slot_qty_tins = int(qty_num)
        # 单位名：移除命令词+关键槽位片段后取前半段
        unit_candidate = slot_text
        unit_candidate = re.sub(r"(发货单|送货单|出货单)", " ", unit_candidate)
        unit_candidate = re.sub(rf"(?:编号|型号)\s*(?:是)?\s*[:：]?\s*{model_token_pattern}", " ", unit_candidate)
        unit_candidate = re.sub(r"规格\s*[:：]?\s*(?:\d+(?:\.\d+)?|[一二两三四五六七八九十零〇两]+)(?:\s*(?:\d+|[一二两三四五六七八九十零〇两]+)\s*桶)?", " ", unit_candidate)
        unit_candidate = re.sub(r"(?:一共|总共|共|要|来|拿)?\s*(?:\d+|[一二两三四五六七八九十零〇两]+)\s*桶", " ", unit_candidate)
        unit_candidate = re.sub(r"[0-9A-Za-z-]{3,16}", " ", unit_candidate)
        unit_candidate = re.sub(r"[，,\s]+", " ", unit_candidate).strip()
        slot_unit = _cleanup_unit_name(unit_candidate)
        if not slot_unit:
            m_unit = re.search(r"(?:打印(?:一下)?)\s*([^，,。]+?)\s*的?\s*(?:发货单|送货单|出货单)", slot_text)
            if not m_unit:
                m_unit = re.search(r"([^，,。]+?)\s*的?\s*(?:发货单|送货单|出货单)", slot_text)
            if m_unit:
                slot_unit = _cleanup_unit_name(m_unit.group(1))
        if not slot_unit:
            m_unit3 = re.search(r"([^，,。0-9]+?)的(?:发货单|送货单|出货单)", slot_text)
            if m_unit3:
                slot_unit = _cleanup_unit_name(m_unit3.group(1))
        if not slot_unit:
            for bill_kw in ["发货单", "送货单", "出货单"]:
                if bill_kw in slot_text:
                    slot_unit = _cleanup_unit_name(slot_text.split(bill_kw)[0])
                    if slot_unit:
                        break
        if not slot_unit:
            # 最后兜底：提取“打印一下XX发货单”中 XX
            m_unit4 = re.search(r"打印(?:一下)?\s*([^，,。]+?)\s*(?:发货单|送货单|出货单)", slot_text)
            if m_unit4:
                slot_unit = _cleanup_unit_name(m_unit4.group(1))

        # 「发货单蕊芯1一桶9806…」类句式：桶数 1 会残留在单位尾部成「蕊芯1」，导致购买单位匹配失败
        if slot_unit and slot_qty_tins is not None:
            try:
                qt = int(slot_qty_tins)
            except (TypeError, ValueError):
                qt = None
            if qt is not None and qt > 0:
                tu = str(slot_unit).strip()
                tail = str(qt)
                if tu.endswith(tail) and len(tu) > len(tail):
                    pref = tu[: -len(tail)].strip()
                    if pref and re.search(r"[\u4e00-\u9fa5A-Za-z]", pref):
                        slot_unit = pref

        # 仅在口语槽位信号较强时才走该分支，避免覆盖原有“1桶酒吧零三规格28”成功路径
        slot_mode_trigger = (
            ("编号" in slot_text or "型号" in slot_text or "一共" in slot_text or "总共" in slot_text or "共" in slot_text)
            or re.search(rf"{model_token_pattern}\s*(?:的)?\s*规格", slot_text)
            or re.search(r"(?:要|来|拿)\s*(?:\d+|[一二两三四五六七八九十零〇两]+)\s*桶", slot_text)
        )
        # 多产品句式（如“1桶9803规格23，2桶9000A规格23”）不走单槽位直返，交给后面的多产品解析。
        multi_product_hint = len(
            re.findall(r"(?:\d+|[一二两三四五六七八九十零〇]+)\s*桶\s*[0-9A-Za-z-]+\s*规格\s*\d+(?:\.\d+)?", slot_text)
        ) >= 2
        if slot_mode_trigger and (slot_model or slot_spec or slot_qty_tins) and not multi_product_hint:
            # 缺项追问（不中断工作流）
            missing_prompt = _build_missing_prompt(
                unit_name=slot_unit,
                model_number=slot_model,
                tin_spec=int(slot_spec) if isinstance(slot_spec, float) and slot_spec.is_integer() else slot_spec,
                quantity_tins=slot_qty_tins,
            )
            if missing_prompt:
                return {"success": False, "message": missing_prompt}

            # 完整则直接返回，避免后续固定顺序正则再失败
            return {
                "success": True,
                "unit_name": slot_unit,
                "products": [{
                    "name": "",
                    "model_number": str(slot_model),
                    "quantity_tins": int(slot_qty_tins),
                    "tin_spec": float(slot_spec),
                }]
            }
        
        # -----------------------------
        # 归一化解析用的小工具
        # -----------------------------
        CHINESE_DIGIT_MAP = {
            "零": "0", "〇": "0",
            "一": "1",
            "二": "2",
            "三": "3",
            "四": "4",
            "五": "5",
            "六": "6",
            "七": "7",
            "八": "8",
            "九": "9",
            "两": "2",
        }

        # ASR 误读片段到数字片段的“分段纠错映射”
        # 例如：酒吧零三 -> (酒吧->98) + (零三->03) -> 9803
        ASR_MODEL_SEGMENT_MAP = {
            "酒吧": "98",
        }

        def _normalize_trailing_unit_name(name: str) -> str:
            # 例如：七彩乐园的 -> 七彩乐园
            return (name or "").strip().rstrip("的").strip()

        def _normalize_chinese_digits(token: str) -> str:
            """
            把“零三/一/两”等这种“逐位数字串”转成阿拉伯数字串，保留前导零（如 零三 -> 03）。
            """
            token = (token or "").strip()
            if not token:
                return ""

            # 纯阿拉伯数字：直接返回
            if re.fullmatch(r"\d+(?:\.\d+)?", token):
                return token

            # 仅由中文数字字符组成（逐位映射）
            if all(ch in CHINESE_DIGIT_MAP for ch in token):
                return "".join(CHINESE_DIGIT_MAP[ch] for ch in token)

            # 兜底：在 token 内提取中文数字字符并逐位映射
            digits = []
            for ch in token:
                if ch in CHINESE_DIGIT_MAP:
                    digits.append(CHINESE_DIGIT_MAP[ch])
            return "".join(digits)

        def _normalize_quantity_token(quantity_token: str):
            """
            把数量（如“一”）归一为整数桶数。
            """
            quantity_token = (quantity_token or "").strip()
            if not quantity_token:
                return None
            if re.fullmatch(r"\d+", quantity_token):
                return int(quantity_token)
            digits = _normalize_chinese_digits(quantity_token)
            if digits.isdigit():
                return int(digits)
            return None

        def _normalize_model_number_token(model_token: str) -> str:
            """
            把型号 token 归一为统一型号字符串（数字/字母/连字符）。
            - 支持 ASR 误读分段（如 酒吧->98）
            - 支持中文数字逐位映射（零三->03）
            """
            token = (model_token or "").strip()
            if not token:
                return ""

            # 已是常见型号形态，直接标准化（去空格、转大写）
            compact = re.sub(r"\s+", "", token)
            if re.fullmatch(r"[0-9A-Za-z-]+", compact):
                return compact.upper()

            # 逐段纠错：把已知误读片段先替换为数字片段
            for k, v in ASR_MODEL_SEGMENT_MAP.items():
                if k in token:
                    token = token.replace(k, v)

            # 按字符归一：保留数字/字母/连字符，中文数字映射为阿拉伯数字
            out: list[str] = []
            for ch in token:
                if ch.isdigit():
                    out.append(ch)
                elif ch in CHINESE_DIGIT_MAP:
                    out.append(CHINESE_DIGIT_MAP[ch])
                elif ch.isalpha():
                    out.append(ch.upper())
                elif ch == "-":
                    out.append(ch)
            return "".join(out)

        # -----------------------------
        # 多产品解析：支持 "发货单七彩乐园1桶9803规格23，2桶9000A规格23"
        # -----------------------------
        multi_pattern = r'(\d+|[一二两三四五六七八九十零〇]+)\s*桶\s*([0-9A-Za-z-]+)\s*规格\s*(\d+(?:\.\d+)?)'
        multi_matches = list(re.finditer(multi_pattern, slot_text))
        if multi_matches:
            products = []
            for m in multi_matches:
                qty = _parse_cn_number(m.group(1))
                model = (m.group(2) or "").strip().upper()
                spec = float(m.group(3))
                if model:
                    products.append({
                        "name": "",
                        "model_number": model,
                        "quantity_tins": int(qty) if qty else 1,
                        "tin_spec": spec
                    })

            if products:
                prefix_text = slot_text[:multi_matches[0].start()]
                for kw in ["发货单", "送货单", "出货单", "货单", "打印", "打单", "开单", "帮我", "给我", "请", "一下"]:
                    prefix_text = prefix_text.replace(kw, " ")
                unit_candidate = _cleanup_unit_name(prefix_text)
                if not unit_candidate:
                    unit_candidate = _cleanup_unit_name(text.split()[0] if text.split() else "")

                if unit_candidate:
                    return {
                        "success": True,
                        "unit_name": unit_candidate,
                        "products": products
                    }

        # -----------------------------
        # 简单解析：按"桶"、"规格"分割
        # -----------------------------
        patterns = [
            # 模式 1: "七彩乐园 1 桶 9803 规格 12"
            # 允许数量/型号为中文数字/ASR token，且允许“的规格”
            r'^([^\d]+?)(\d+|[一二三四五六七八九十零〇两]+)\s*桶\s*(.+?)\s*规格\s*(\d+(?:\.\d+)?)',
            # 模式 2: "七彩乐园 1 桶 9803"
            r'^([^\d]+?)(\d+|[一二三四五六七八九十零〇两]+)\s*桶\s*(.+)$',
            # 模式 3: "七彩乐园 2 箱产品 A"
            r'^([^\d]+?)(\d+|[一二三四五六七八九十零〇两]+)\s*(箱 | 件)\s*(.+)',
            # 模式 4: "公司 A 3 公斤材料 B"
            r'^([^\d]+?)(\d+(?:\.\d+)?|[一二三四五六七八九十零〇两]+)\s*(公斤|kg)\s*(.+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if len(groups) >= 3:
                    unit_name = _normalize_trailing_unit_name(groups[0])
                    
                    # 判断是否是数字开头（型号）还是单位
                    unit_or_measure = (groups[2] or "").strip()
                    if unit_or_measure in ['箱', '件', '公斤', 'kg']:
                        # 模式 3 或 4
                        try:
                            # 箱/件：尽量解析为整数；公斤/kg：允许小数（并支持中文数字）
                            if unit_or_measure in ['箱', '件']:
                                quantity = float(_normalize_quantity_token(groups[1]) or 0)
                            else:
                                token = (groups[1] or "").strip()
                                if re.fullmatch(r"\d+(?:\.\d+)?", token):
                                    quantity = float(token)
                                else:
                                    digits = _normalize_chinese_digits(token)
                                    quantity = float(digits) if digits else float(token)
                        except:
                            quantity = 1
                        
                        product_name = groups[3].strip() if len(groups) > 3 else "产品"
                        
                        result = {
                            "success": True,
                            "unit_name": unit_name,
                            "products": [{
                                "name": product_name,
                                "tin_spec": 10.0,  # 默认规格
                            }]
                        }
                        
                        if '公斤' in unit_or_measure or 'kg' in unit_or_measure:
                            result["products"][0]["quantity_kg"] = quantity
                        else:
                            result["products"][0]["quantity_tins"] = int(quantity) if unit_or_measure in ['箱', '件'] else quantity
                        
                        return result
                    else:
                        # 模式 1 或 2: "七彩乐园 1 桶 9803 规格 12"
                        try:
                            quantity = _normalize_quantity_token(groups[1])
                            if quantity is None:
                                return {
                                    "success": False,
                                    "message": "解析数字失败（数量无法识别）"
                                }

                            model_number = _normalize_model_number_token(groups[2])
                            if not model_number:
                                return {
                                    "success": False,
                                    "message": "解析数字失败（型号无法识别）"
                                }

                            spec = float(groups[3]) if len(groups) > 3 else 10.0
                        except:
                            return {
                                "success": False,
                                "message": "解析数字失败"
                            }
                        
                        # name 留空，让后续数据库匹配来填充正确的产品名称
                        return {
                            "success": True,
                            "unit_name": unit_name,
                            "products": [{
                                "name": "",  # 留空，等待数据库匹配
                                "model_number": model_number,
                                "quantity_tins": quantity,
                                "tin_spec": spec,
                            }]
                        }
        
        # 弱匹配：打印/报型号+规格，但缺少“桶/箱/件/公斤/kg”数量容器时
        # 例如：打印一下七彩乐园的9803规格28（用户只给了型号与规格，没有桶数）
        # 目标：让系统追问“需要多少桶？”，而不是忽略或走产品流程。
        has_container_qty = any(k in text for k in ["桶", "箱", "件", "公斤", "kg"])
        if not has_container_qty:
            m = re.search(rf'([^\d]+?)\s*({model_token_pattern})\s*规格\s*(\d+(?:\.\d+)?)', text)
            if m:
                unit_part = m.group(1)
                model_token = m.group(2)
                spec_token = m.group(3)

                unit_name = _normalize_trailing_unit_name(unit_part)
                # 去掉可能出现在 unit_part 前缀的口语/指令词（如“打印一下七彩乐园的”）
                unit_name = re.sub(r'^(帮我|给我)?打印(一下)?|^打单|^开单', '', unit_name).strip()
                model_number = _normalize_model_number_token(model_token)
                tin_spec = float(spec_token)

                if unit_name and model_number and tin_spec is not None:
                    spec_display = int(tin_spec) if tin_spec.is_integer() else tin_spec
                    return {
                        "success": False,
                        "message": f"还缺少桶数（数量）。已识别：{unit_name} / {model_number} / 规格 {spec_display}。请告诉我需要多少桶？"
                    }

        # AI 结构化抽取兜底：规则仍失败时尝试从口语中抽取 unit/model/spec/qty
        try:
            import json
            import os

            import httpx

            api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
            if api_key:
                prompt = (
                    "请从下面中文订单口语中抽取 JSON 字段："
                    "unit_name, model_number, tin_spec, quantity_tins。"
                    "仅返回 JSON，不要解释，不要 markdown。\n"
                    f"文本：{text}"
                )
                with httpx.Client(timeout=8.0) as client:
                    resp = client.post(
                        "https://api.deepseek.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": "deepseek-chat",
                            "messages": [
                                {"role": "system", "content": "你是结构化信息抽取助手，只输出 JSON。"},
                                {"role": "user", "content": prompt},
                            ],
                            "temperature": 0.0,
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        content = (
                            (data.get("choices") or [{}])[0]
                            .get("message", {})
                            .get("content", "")
                            .strip()
                        )
                        # 兼容 ```json ... ``` 包裹
                        content = re.sub(r"^```json\s*|^```\s*|```$", "", content).strip()
                        parsed = json.loads(content) if content else {}
                        ai_unit = _cleanup_unit_name(str(parsed.get("unit_name", "")).strip())
                        ai_model = str(parsed.get("model_number", "")).strip()
                        ai_spec_raw = str(parsed.get("tin_spec", "")).strip()
                        ai_qty_raw = str(parsed.get("quantity_tins", "")).strip()
                        ai_spec = _parse_cn_number(ai_spec_raw) if ai_spec_raw else None
                        ai_qty = _parse_cn_number(ai_qty_raw) if ai_qty_raw else None

                        missing_prompt = _build_missing_prompt(
                            unit_name=ai_unit,
                            model_number=ai_model or None,
                            tin_spec=ai_spec,
                            quantity_tins=int(ai_qty) if ai_qty else None,
                        )
                        if missing_prompt:
                            return {"success": False, "message": missing_prompt}

                        if ai_unit and ai_model and ai_spec and ai_qty:
                            return {
                                "success": True,
                                "unit_name": ai_unit,
                                "products": [{
                                    "name": "",
                                    "model_number": ai_model,
                                    "quantity_tins": int(ai_qty),
                                    "tin_spec": float(ai_spec),
                                }],
                            }
        except Exception as ai_err:
            logger.warning(f"AI 结构化抽取兜底失败，回退规则流程: {ai_err}")

        # 如果所有模式都不匹配，尝试简单分割
        parts = text.split()
        if len(parts) >= 2:
            unit_name = parts[0].strip()
            return {
                "success": True,
                "unit_name": unit_name,
                "products": [{
                    "name": " ".join(parts[1:]),
                    "quantity_tins": 1,
                    "tin_spec": 10.0,
                }]
            }
        
        return {
            "success": False,
            "message": f"无法解析订单文本：{order_text}，请使用格式：发货单 + 单位名 + 数量 + 桶 + 型号 + 规格"
        }
        
    except Exception as e:
        logger.error(f"解析订单文本失败：{e}")
        return {
            "success": False,
            "message": f"解析失败：{str(e)}"
        }


@tools_bp.route('/api/database/backup', methods=['POST'])
@swag_from({
    'summary': '备份数据库',
    'description': '备份 SQLite 数据库到备份目录',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'},
                    'file_path': {'type': 'string', 'description': '备份文件路径'},
                    'filename': {'type': 'string', 'description': '备份文件名'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def backup_database():
    """备份数据库"""
    try:
        from app.services import get_database_service
        db_service = get_database_service()
        result = db_service.backup_database()
        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"备份数据库失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/database/restore', methods=['POST'])
@swag_from({
    'summary': '恢复数据库',
    'description': '从备份文件恢复数据库',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['backup_file'],
                'properties': {
                    'backup_file': {'type': 'string', 'description': '备份文件路径或文件名'}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '400': {
            'description': '请求参数错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def restore_database():
    """恢复数据库"""
    try:
        from app.services import get_database_service
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "message": "请求数据不能为空"}), 400
        
        backup_file = data.get('backup_file')
        if not backup_file:
            return jsonify({"success": False, "message": "缺少参数：backup_file"}), 400
        
        db_service = get_database_service()
        result = db_service.restore_database(backup_file)
        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"恢复数据库失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/database/backups', methods=['GET'])
@swag_from({
    'summary': '列出备份文件',
    'description': '列出所有数据库备份文件',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'backups': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'filename': {'type': 'string'},
                                'file_path': {'type': 'string'},
                                'size': {'type': 'integer'},
                                'created_at': {'type': 'string'}
                            }
                        }
                    },
                    'count': {'type': 'integer'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def list_database_backups():
    """列出备份文件"""
    try:
        from app.services import get_database_service
        db_service = get_database_service()
        result = db_service.list_backups()
        return jsonify(result)
    except Exception as e:
        logger.error(f"列出备份文件失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/database/backup/<path:backup_file>', methods=['DELETE'])
@swag_from({
    'summary': '删除备份文件',
    'description': '删除指定的数据库备份文件',
    'parameters': [
        {
            'name': 'backup_file',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': '备份文件名'
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def delete_database_backup(backup_file):
    """删除备份文件"""
    try:
        from app.services import get_database_service
        db_service = get_database_service()
        result = db_service.delete_backup(backup_file)
        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"删除备份文件失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/system/startup', methods=['GET'])
@swag_from({
    'summary': '获取开机自启配置',
    'description': '获取当前应用的开机自启状态',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'enabled': {'type': 'boolean'},
                            'app_path': {'type': 'string'},
                            'startup_path': {'type': 'string'},
                            'platform': {'type': 'string'}
                        }
                    }
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def get_startup_config():
    """获取开机自启配置"""
    try:
        from app.services import get_system_service
        system_service = get_system_service()
        result = system_service.get_startup_config()
        return jsonify({"success": True, "data": result})
    except Exception as e:
        logger.error(f"获取开机自启配置失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/system/startup', methods=['POST'])
@swag_from({
    'summary': '启用开机自启',
    'description': '启用应用的开机自启动功能',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'},
                    'command': {'type': 'string', 'description': '启动命令'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def enable_startup():
    """启用开机自启"""
    try:
        from app.services import get_system_service
        system_service = get_system_service()
        result = system_service.enable_startup()
        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"启用开机自启失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/system/startup', methods=['DELETE'])
@swag_from({
    'summary': '禁用开机自启',
    'description': '禁用应用的开机自启动功能',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def disable_startup():
    """禁用开机自启"""
    try:
        from app.services import get_system_service
        system_service = get_system_service()
        result = system_service.disable_startup()
        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"禁用开机自启失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/system/info', methods=['GET'])
@swag_from({
    'summary': '获取系统信息',
    'description': '获取系统信息，包括操作系统、Python 版本等',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'data': {
                        'type': 'object',
                        'properties': {
                            'platform': {'type': 'string'},
                            'platform_version': {'type': 'string'},
                            'python_version': {'type': 'string'},
                            'app_path': {'type': 'string'},
                            'working_directory': {'type': 'string'},
                            'executable': {'type': 'string'}
                        }
                    }
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def get_system_info():
    """获取系统信息"""
    try:
        from app.services import get_system_service
        system_service = get_system_service()
        result = system_service.get_system_info()
        return jsonify({"success": True, "data": result})
    except Exception as e:
        logger.error(f"获取系统信息失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/system/printer', methods=['GET'])
@swag_from({
    'summary': '获取打印机配置',
    'description': '获取可用的打印机列表和默认打印机',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'printers': {
                        'type': 'array',
                        'items': {'type': 'string'}
                    },
                    'default_printer': {'type': 'string'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def get_printer_config():
    """获取打印机配置"""
    try:
        from app.services import get_system_service
        system_service = get_system_service()
        result = system_service.get_printer_config()
        return jsonify(result)
    except Exception as e:
        logger.error(f"获取打印机配置失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/system/printer', methods=['POST'])
@swag_from({
    'summary': '设置默认打印机',
    'description': '设置系统默认打印机',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['printer_name'],
                'properties': {
                    'printer_name': {'type': 'string', 'description': '打印机名称'}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '400': {
            'description': '请求参数错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def set_default_printer():
    """设置默认打印机"""
    try:
        from app.services import get_system_service
        data = request.get_json()
        
        if not data:
            return jsonify({"success": False, "message": "请求数据不能为空"}), 400
        
        printer_name = data.get('printer_name')
        if not printer_name:
            return jsonify({"success": False, "message": "缺少参数：printer_name"}), 400
        
        system_service = get_system_service()
        result = system_service.set_default_printer(printer_name)
        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code
    except Exception as e:
        logger.error(f"设置默认打印机失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/db-tools', methods=['GET'])
def get_db_tools_compat():
    """兼容旧版前端的 /api/db-tools 接口"""
    return get_tools_list()


@tools_bp.route('/api/tools', methods=['GET'])
@swag_from({
    'summary': '获取工具列表',
    'description': '获取可用工具列表',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'tools': {'type': 'array'}
                }
            }
        }
    }
})
def get_tools_list():
    """获取可用工具列表"""
    try:
        tools = [
            {"id": "chat", "name": "智能对话", "description": "打开智能对话主界面", "category": "chat",
             "actions": [{"name": "打开对话", "description": "跳转到智能对话页"}]},
            {"id": "ai_ecosystem", "name": "AI生态", "description": "打开 AI 生态页面", "category": "ai",
             "actions": [{"name": "查看", "description": "跳转到 AI 生态页"}, {"name": "查询", "description": "查看生态能力摘要"}]},
            {"id": "products", "name": "产品管理", "description": "查看、搜索产品与型号，管理产品库", "category": "products",
             "actions": [{"name": "查看", "description": "查看所有产品列表"}, {"name": "查询", "description": "按型号或名称搜索"}, {"name": "创建", "description": "添加新产品"}, {"name": "更新", "description": "更新产品"}, {"name": "删除", "description": "删除产品"}, {"name": "批量删除", "description": "批量删除产品"}, {"name": "导出", "description": "导出产品 Excel"}]},
            {"id": "materials_list", "name": "原材料列表", "description": "查看原材料明细列表", "category": "materials",
             "actions": [{"name": "查看", "description": "跳转到原材料列表页"}, {"name": "查询", "description": "按关键词筛选原材料"}]},
            {"id": "customers", "name": "客户/购买单位", "description": "查看、编辑客户列表，或上传 Excel 更新购买单位", "category": "customers",
             "actions": [{"name": "查看", "description": "查看客户/购买单位列表"}, {"name": "查询", "description": "按关键词搜索客户"}, {"name": "创建", "description": "添加新客户"}, {"name": "更新", "description": "补充客户联系人信息"}, {"name": "删除", "description": "删除客户"}]},
            {"id": "business_docking", "name": "业务对接", "description": "上传 Excel 并做模板网格提取与保存", "category": "excel",
             "actions": [{"name": "查看", "description": "跳转到业务对接页"}, {"name": "提取", "description": "按 file_path 提取模板结构"}, {"name": "预览", "description": "获取网格预览与样例行"}]},
            {"id": "shipment_records", "name": "出货记录", "description": "查看出货记录与导出结果", "category": "orders",
             "actions": [{"name": "查看", "description": "跳转到出货记录页"}, {"name": "列表", "description": "按单位查看记录"}, {"name": "更新", "description": "更新出货记录"}, {"name": "删除", "description": "删除出货记录"}, {"name": "导出", "description": "导出出货记录"}]},
            {"id": "orders", "name": "出货单", "description": "查看出货订单、创建订单、导出 Excel", "category": "orders",
             "actions": [{"name": "查看订单", "description": "查看出货订单列表"}, {"name": "创建订单", "description": "创建新订单"}, {"name": "导出订单", "description": "导出订单到 Excel"}]},
            {"id": "shipment_generate", "name": "生成发货单", "description": "按订单文本或「打印+订单」生成发货单，支持编号模式与商标导出", "category": "orders",
             "actions": [{"name": "生成发货单", "description": "输入订单内容直接生成发货单"}]},
            {"id": "print", "name": "标签打印", "description": "打印产品标签或导出商标到本地下载", "category": "print",
             "actions": [{"name": "查看", "description": "打开标签打印页"}, {"name": "列表", "description": "查询打印机和标签"}, {"name": "打印标签", "description": "打印商标导出目录下标签"}, {"name": "打印文档", "description": "打印发货单等文档"}, {"name": "测试", "description": "测试打印机"}]},
            {"id": "printer_list", "name": "打印机列表", "description": "查看系统打印机列表和默认打印机", "category": "print",
             "actions": [{"name": "查看", "description": "跳转到打印机列表页"}, {"name": "列表", "description": "查询系统打印机列表"}, {"name": "设置默认", "description": "设置默认打印机"}]},
            {"id": "materials", "name": "原材料仓库", "description": "查看原材料库存与预警", "category": "materials",
             "actions": [{"name": "查看", "description": "查看库存"}, {"name": "查询", "description": "按条件查询原材料"}, {"name": "创建", "description": "新增原材料"}, {"name": "更新", "description": "更新原材料"}, {"name": "删除", "description": "删除原材料"}, {"name": "批量删除", "description": "批量删除原材料"}, {"name": "导出", "description": "导出原材料"}]},
            {"id": "database", "name": "数据库管理", "description": "数据库备份与恢复", "category": "database",
             "actions": [{"name": "备份", "description": "备份数据库"}, {"name": "恢复", "description": "从备份恢复"}]},
            {"id": "system", "name": "系统设置", "description": "开机自启、打印配置等", "category": "system",
             "actions": [{"name": "开机启动", "description": "设置开机自启动"}, {"name": "打印设置", "description": "配置打印机"}]},
            {"id": "shipment_template", "name": "发货单模板", "description": "保存/展示模板、可编辑词条与字段映射、介绍抬头与金额计算", "category": "orders",
             "actions": [{"name": "保存模板", "description": "将指定 xlsx 保存为发货单模板.xlsx"}, {"name": "展示模板", "description": "展示可编辑词条与字段映射"}, {"name": "介绍功能", "description": "介绍抬头、业务字段与价格计算逻辑"}]},
            {"id": "template_preview", "name": "模板库", "description": "查看并维护模板预览与模板数据", "category": "excel",
             "actions": [{"name": "查看", "description": "跳转到模板库页"}, {"name": "列表", "description": "查看模板列表"}, {"name": "查询", "description": "按模板名查询"}, {"name": "创建", "description": "将分析结果中的指定 sheet 保存到模板库"}]},
            {"id": "tools_table", "name": "工具表", "description": "查看工具能力列表与入口", "category": "system",
             "actions": [{"name": "查看", "description": "跳转到工具表页"}, {"name": "列表", "description": "列出全部工具能力"}]},
            {"id": "other_tools", "name": "其他工具", "description": "打开其他工具集合页面", "category": "system",
             "actions": [{"name": "查看", "description": "跳转到其他工具页"}, {"name": "列表", "description": "列出其他工具入口"}]},
            {"id": "excel_decompose", "name": "Excel 模板分解", "description": "自动分解 Excel 结构，提取表头、可编辑词条与金额字段", "category": "excel",
             "actions": [{"name": "分解模板", "description": "输出表头、词条、样例行与金额字段"}]},
            {"id": "excel_analyzer", "name": "Excel 模板分析", "description": "深度分析Excel模板结构，识别可编辑区域、表头、数据区、汇总区、合并单元格", "category": "excel",
             "actions": [{"name": "分析模板", "description": "分析Excel模板结构和可编辑区域"}, {"name": "提取结构", "description": "提取模板的表头、数据区、汇总区信息"}]},
            {"id": "template_extract", "name": "提取模板", "description": "从现有 Excel 文件路径提取模板字段、样例行和网格预览", "category": "excel",
             "actions": [{"name": "提取模板", "description": "按文件路径提取模板结构"}, {"name": "提取结构", "description": "提取字段和网格预览信息"}]},
            {"id": "excel_toolkit", "name": "Excel 工具箱", "description": "查看Excel内容、合并单元格、样式信息，分析表格结构", "category": "excel",
             "actions": [{"name": "查看内容", "description": "查看Excel文件内容"}, {"name": "合并单元格", "description": "获取合并单元格信息"}, {"name": "样式信息", "description": "获取单元格样式"}]},
            {"id": "ocr", "name": "图片 OCR", "description": "识别图片中的文字", "category": "ocr",
             "actions": [{"name": "文字识别", "description": "上传图片识别文字"}, {"name": "结构化提取", "description": "从图片中提取结构化数据"}]},
            {"id": "wechat", "name": "微信任务", "description": "扫描微信消息，识别订单和发货单", "category": "wechat",
             "actions": [{"name": "查看", "description": "跳转到微信联系人页"}, {"name": "列表", "description": "查询联系人列表"}, {"name": "查询", "description": "按关键词搜索联系人"}, {"name": "刷新联系人缓存", "description": "从微信库刷新联系人"}, {"name": "刷新消息缓存", "description": "刷新解密消息缓存"}]},
        ]
        return jsonify({"success": True, "tools": tools})
    except Exception as e:
        logger.error(f"获取工具列表失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/tool-categories', methods=['GET'])
@swag_from({
    'summary': '获取工具分类',
    'description': '获取工具分类列表',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'categories': {'type': 'array'}
                }
            }
        }
    }
})
def get_tool_categories():
    """获取工具分类列表"""
    try:
        categories = [
            {"id": 1, "category_name": "产品管理", "category_key": "products", "description": "产品与型号管理", "icon": "📦", "sort_order": 1, "is_active": True},
            {"id": 2, "category_name": "客户/购买单位", "category_key": "customers", "description": "客户信息管理", "icon": "👥", "sort_order": 2, "is_active": True},
            {"id": 3, "category_name": "出货单", "category_key": "orders", "description": "订单与发货单管理", "icon": "📋", "sort_order": 3, "is_active": True},
            {"id": 4, "category_name": "标签打印", "category_key": "print", "description": "标签打印管理", "icon": "🖨️", "sort_order": 4, "is_active": True},
            {"id": 5, "category_name": "原材料仓库", "category_key": "materials", "description": "原材料库存管理", "icon": "🏭", "sort_order": 5, "is_active": True},
            {"id": 6, "category_name": "Excel 处理", "category_key": "excel", "description": "Excel 模板与数据处理", "icon": "📊", "sort_order": 6, "is_active": True},
            {"id": 7, "category_name": "图片 OCR", "category_key": "ocr", "description": "图片文字识别", "icon": "🔍", "sort_order": 7, "is_active": True},
            {"id": 8, "category_name": "数据库管理", "category_key": "database", "description": "数据库备份与恢复", "icon": "💾", "sort_order": 8, "is_active": True},
            {"id": 9, "category_name": "系统设置", "category_key": "system", "description": "系统配置与管理", "icon": "⚙️", "sort_order": 9, "is_active": True},
            {"id": 10, "category_name": "微信任务", "category_key": "wechat", "description": "微信消息处理", "icon": "💬", "sort_order": 10, "is_active": True},
        ]
        return jsonify({"success": True, "categories": categories})
    except Exception as e:
        logger.error(f"获取工具分类失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@tools_bp.route('/api/tools/execute', methods=['POST'])
@swag_from({
    'summary': '执行工具',
    'description': '执行工具操作，统一动作契约：view/list/query/create/update/delete/batch_delete/import/export/analyze/extract/preview/execute',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'tool_id': {'type': 'string', 'description': '工具 ID', 'enum': ['chat', 'ai_ecosystem', 'products', 'materials_list', 'materials', 'business_docking', 'shipment_records', 'customers', 'wechat', 'print', 'printer_list', 'template_preview', 'settings', 'tools_table', 'other_tools', 'orders', 'database', 'system', 'ocr', 'excel_decompose', 'excel_analyzer', 'excel_toolkit', 'shipment_template', 'shipment_generate', 'template_extract']},
                    'action': {'type': 'string', 'description': '操作类型', 'enum': ['view', 'list', 'query', 'create', 'update', 'delete', 'batch_delete', 'import', 'export', 'analyze', 'extract', 'preview', 'execute', 'backup', 'restore', 'get_startup_config', 'enable_startup', 'disable_startup', 'get_system_info', 'get_printer_config', 'set_default_printer', 'print_label', 'print_document', 'test', 'set_default', 'refresh_contact_cache', 'refresh_messages_cache']},
                    'params': {
                        'type': 'object',
                        'description': '操作参数',
                        'properties': {
                            'backup_file': {'type': 'string', 'description': '备份文件路径（用于 restore 和 delete 操作）'},
                            'printer_name': {'type': 'string', 'description': '打印机名称（用于 set_default_printer 操作）'},
                            'order_text': {'type': 'string', 'description': '订单文本（用于 shipment_generate 操作）'}
                        }
                    }
                },
                'required': ['tool_id', 'action']
            }
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'result': {'type': 'object'},
                    'message': {'type': 'string'},
                    'redirect': {'type': 'string', 'description': '重定向 URL（仅部分工具）'},
                    'data': {'type': 'object', 'description': '返回数据（system 工具）'},
                    'backups': {'type': 'array', 'description': '备份列表（database list 操作）'},
                    'count': {'type': 'integer', 'description': '数量（database list 操作）'}
                }
            }
        },
        '400': {
            'description': '请求参数错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        },
        '500': {
            'description': '服务器内部错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'message': {'type': 'string'}
                }
            }
        }
    }
})
def execute_tool():
    """执行工具操作"""
    try:
        from flask import request
        data = request.get_json()
        
        # 详细日志：记录请求数据
        logger.info(f"[DEBUG] /api/tools/execute 收到请求 - data: {data}")
        
        if not data:
            logger.error(f"[DEBUG] /api/tools/execute 请求数据为空")
            return jsonify({"success": False, "message": "未收到数据"}), 400
        
        tool_id = data.get('tool_id')
        action = _normalize_action(data.get('action', 'view'), data.get('params') or {})
        params = data.get('params') or {}

        valid, err_msg = _validate_required_params(str(tool_id or "").strip(), action, params)
        if not valid:
            return jsonify({
                "success": False,
                "error_code": "missing_required_params",
                "message": err_msg,
            }), 400

        # 新版统一 dispatcher：优先处理注册表中的工作流动作
        registry = get_workflow_tool_registry()
        if tool_id in registry and action in registry[tool_id].get("actions", {}):
            routed = execute_registered_workflow_tool(tool_id=tool_id, action=action, params=params)
            status_code = 200 if routed.get("success") else 400
            return jsonify(routed), status_code
        
        # 记录关键参数
        logger.info(f"[DEBUG] tool_id={tool_id}, action={action}, params_keys={list(params.keys())}")
        if 'order_text' in params:
            logger.info(f"[DEBUG] order_text={params.get('order_text')[:200] if params.get('order_text') else None}")
        
        if tool_id == 'products':
            from app.routes.products import products_bp
            effective_action = action
            if action in ('执行', 'exec', 'run', 'execute'):
                effective_action = params.get('action', 'view')

            keyword = (params.get("keyword") or "").strip()
            unit_name = (params.get("unit_name") or "").strip()
            model_number = (params.get("model_number") or "").strip()
            tin_spec = (params.get("tin_spec") or "").strip()

            search_verbs = ['search', 'query', 'find', '查找', '查询', '搜索']
            is_search = (effective_action in search_verbs) or keyword

            if is_search and keyword:
                return jsonify({
                    "success": True,
                    "redirect": f"/console?view=products&keyword={keyword}",
                    "message": f"已按关键词检索产品：{keyword}",
                    "data": {
                        "keyword": keyword,
                        "unit_name": unit_name,
                        "model_number": model_number,
                        "tin_spec": tin_spec
                    }
                })
            if effective_action == 'view':
                return jsonify({"success": True, "redirect": "/console?view=products"})
            return jsonify({"success": True, "message": "产品管理"})

        elif tool_id == 'chat':
            return jsonify({"success": True, "redirect": "/console?view=chat", "message": "已打开智能对话"})

        elif tool_id == 'ai_ecosystem':
            if action in ("list", "query"):
                return jsonify({
                    "success": True,
                    "data": {
                        "views": ["ai-ecosystem"],
                        "integrations": ["deepseek", "bert", "rasa", "workflow-planner"],
                    },
                }), 200
            return jsonify({"success": True, "redirect": "/console?view=ai-ecosystem", "message": "已打开AI生态"})

        elif tool_id == 'materials_list':
            if action in ("query", "list"):
                from app.application import get_material_application_service
                svc = get_material_application_service()
                result = svc.get_all_materials(
                    search=str(params.get("search") or params.get("keyword") or "").strip(),
                    category=str(params.get("category") or "").strip() or None,
                    page=int(params.get("page") or 1),
                    per_page=int(params.get("per_page") or 20),
                )
                return jsonify(result), 200
            return jsonify({"success": True, "redirect": "/console?view=materials-list", "message": "已打开原材料列表"})

        elif tool_id == 'business_docking':
            if action in ("extract", "preview", "analyze"):
                file_path = str(params.get("file_path") or "").strip()
                if not file_path:
                    return jsonify({"success": False, "message": "缺少参数：file_path（Excel文件路径）"}), 400
                from app.routes.templates import (
                    _extract_excel_grid_preview,
                    _extract_structured_excel_preview,
                    _list_excel_sheet_names,
                )
                if not os.path.exists(file_path):
                    return jsonify({"success": False, "message": f"文件不存在：{file_path}"}), 404
                sheet_name = str(params.get("sheet_name") or "").strip() or None
                return jsonify({
                    "success": True,
                    "file_path": file_path,
                    "sheet_names": _list_excel_sheet_names(file_path),
                    "structured": _extract_structured_excel_preview(file_path, sheet_name=sheet_name, sample_limit=8),
                    "grid_preview": _extract_excel_grid_preview(file_path, sheet_name=sheet_name, max_rows=24, max_cols=14),
                }), 200
            return jsonify({"success": True, "redirect": "/console?view=business-docking", "message": "已打开业务对接"})

        elif tool_id == 'shipment_records':
            from app.bootstrap import get_shipment_app_service
            svc = get_shipment_app_service()
            if action in ("list", "query"):
                unit = str(params.get("unit") or params.get("unit_name") or "").strip() or None
                return jsonify({"success": True, "data": svc.get_shipment_records(unit)}), 200
            if action == "update":
                record_id = int(params.get("id"))
                payload = {k: v for k, v in params.items() if k != "id"}
                return jsonify(svc.update_shipment_record(record_id=record_id, **payload)), 200
            if action == "delete":
                return jsonify(svc.delete_shipment_record(int(params.get("id")))), 200
            if action == "export":
                result = svc.export_shipment_records(
                    unit_name=str(params.get("unit") or params.get("unit_name") or "").strip() or None,
                    template_id=params.get("template_id"),
                    status_filter=params.get("status"),
                )
                return jsonify(result), 200
            return jsonify({"success": True, "redirect": "/console?view=shipment-records", "message": "已打开出货记录"})
        
        elif tool_id == 'customers':
            # pro 模式下 action 往往是固定的“执行”，但 TaskAgent/前端 params 里会携带真正的子动作（如 search/query）
            effective_action = action
            if (str(action) or "") in ("执行", "exec", "run") and params.get("action"):
                effective_action = params.get("action")

            # 不同上游/模型可能不会把自然语言放在 order_text 里，这里把常见字段都拼一下，提升意图识别鲁棒性。
            order_text = (
                params.get("order_text")
                or params.get("text")
                or params.get("message")
                or params.get("content")
                or ""
            ).strip()
            lower_text = order_text.lower()

            # 把 params 的值也一起纳入意图判断（避免 order_text 为空导致误走 search/query redirect）
            param_blob = " ".join([str(v) for v in (params or {}).values() if v is not None]).strip()
            lower_param_blob = param_blob.lower()

            has_add_verb = (
                any(v in order_text for v in ["添加", "新增", "创建", "新建", "增加"])
                or any(v in lower_text for v in ["add", "create", "new"])
                or any(v in param_blob for v in ["添加", "新增", "创建", "新建", "增加"])
                or any(v in lower_param_blob for v in ["add", "create", "new"])
            )
            has_del_verb = (
                any(v in order_text for v in ["删除", "移除", "去掉"])
                or any(v in lower_text for v in ["delete", "remove", "del"])
                or any(v in param_blob for v in ["删除", "移除", "去掉"])
                or any(v in lower_param_blob for v in ["delete", "remove", "del"])
            )

            keyword = (params.get("keyword") or "").strip()
            # 如果是“检索/搜索”但上游没给 keyword，就尽量用 params 里的名称兜底
            # 注意：一旦用户明确表达删除（has_del_verb），删除应当优先覆盖 search/query redirect。
            if effective_action in ("search", "query") and not keyword and not has_add_verb and not has_del_verb:
                keyword = (
                    params.get("unit_name")
                    or params.get("name")
                    or params.get("customer_name")
                    or ""
                ).strip()
            # 如果自然语言包含“添加/新增/创建”，即便 AI 把 action 判成 search/query，也应优先创建。
            if effective_action in ('search', 'query') and keyword and not has_add_verb and not has_del_verb:
                logger.info("customers: redirect search/query keyword=%s", keyword)
                return jsonify({"success": True, "redirect": f"/console?view=customers&keyword={keyword}", "message": f"已按关键词检索客户：{keyword}"})
            if effective_action == 'view' and not has_add_verb and not has_del_verb:
                logger.info("customers: redirect view")
                return jsonify({"success": True, "redirect": "/console?view=customers"})

            logger.info(
                "customers: attempt create? effective_action=%s has_add_verb=%s order_text_len=%s params_keys=%s",
                effective_action,
                has_add_verb,
                len(order_text or ""),
                list(params.keys()),
            )

            # 聊天/工具侧删除：支持 action=delete/remove/del，幂等删除（不存在也返回 success）
            if effective_action in ("delete", "remove", "del") or has_del_verb:
                from app.db.models import PurchaseUnit
                from app.services.unified_query_service import query_service

                target_id = params.get("customer_id") or params.get("id") or params.get("unit_id")
                target_name = (params.get("customer_name") or params.get("unit_name") or params.get("name") or "").strip()

                # 尽量从自然语言中提取名称：如“删除客户/购买单位叫XX”
                if not target_name and order_text:
                    import re

                    # 支持：包含“联系人/电话/地址”后缀的删除句式
                    # 例：删除购买单位小王公司联系人王总  -> 提取“小王公司”
                    m = re.search(
                        r"(?:删除|移除)?\s*(?:客户|购买单位|单位)\s*(?:叫|是|名称是|名为)?\s*[:：]?\s*([^\s，,。]{2,60}?)"
                        r"(?=(?:联系人|电话|手机|手机号|联系电话|联系号码|地址|住址)|\s*$)",
                        order_text
                    )
                    if m:
                        target_name = (m.group(1) or "").strip()

                deleted_count = 0
                if target_id:
                    try:
                        tid = int(target_id)
                        deleted_count = query_service.delete(PurchaseUnit, id=tid)
                    except Exception:
                        deleted_count = 0
                elif target_name:
                    deleted_count = query_service.delete(PurchaseUnit, unit_name=target_name)
                    if deleted_count == 0 and target_name:
                        try:
                            from app.infrastructure.lookups.purchase_unit_resolver import (
                                resolve_purchase_unit,
                            )
                            resolved = resolve_purchase_unit(target_name)
                            if resolved and getattr(resolved, "unit_name", None) and resolved.unit_name != target_name:
                                deleted_count = query_service.delete(PurchaseUnit, unit_name=resolved.unit_name)
                        except Exception as e:
                            logger.warning(f"解析购买单位失败: {e}")

                return jsonify({
                    "success": True,
                    "message": "删除成功" if deleted_count > 0 else "删除成功（未找到匹配记录）",
                    "deleted_count": deleted_count,
                }), 200

            # 聊天创建购买单位兜底：
            # 当用户表达“添加客户/购买单位 + 名称/联系人/电话/地址”时，直接写入 purchase_units。
            # 这与前端 pro-feature-widget 里 POST /api/purchase_units 的字段对齐。
            should_create_purchase_unit = str(effective_action) in {
                "add", "create", "添加", "新增", "添加客户", "添加购买单位", "create_purchase_unit"
            } or has_add_verb

            # 补充客户信息处理（他/她/它的 联系人/电话/地址）
            should_supplement = str(effective_action) in {"supplement", "补充"} or params.get("field_name")

            if should_supplement:
                from app.db.models import PurchaseUnit
                from app.db.session import get_db
                from app.services.unified_query_service import query_service
                from app.services import get_task_context_service

                ctx = get_task_context_service()
                user_id = params.get("user_id") or request.headers.get("X-User-ID", "default")

                last_customer = ctx.get_last_customer(user_id)
                field_name = params.get("field_name", "")
                field_value = params.get("field_value", "")

                if not field_name and order_text:
                    m = re.search(r"(?:联系人|联系电话|电话|手机|地址)\s*(?:是|：|:)?\s*(.{1,30})", order_text)
                    if m:
                        field_name = "contact_person"
                        field_value = m.group(1).strip()

                if not field_value and order_text:
                    if field_name == "contact_person":
                        m = re.search(r"(?:联系人|联系人是)\s*(?:是|：|:)?\s*([^\s，,。]{1,20})", order_text)
                        if m:
                            field_value = m.group(1).strip()
                    elif field_name in ("contact_phone", "contact_address"):
                        m = re.search(r"(?:电话|手机|地址)\s*(?:是|：|:)?\s*([^\s，,。]{1,50})", order_text)
                        if m:
                            field_value = m.group(1).strip()

                if not last_customer and not field_value:
                    return jsonify({"success": False, "message": "请先告诉我要补充哪个客户的联系人信息，例如：添加客户七彩乐园"}), 400

                target_name = last_customer.get("customer_name") if last_customer else None
                if not target_name:
                    m = re.search(r"(?:客户|购买单位|单位)\s*(?:是|叫|名称是|名为)?\s*[:：]?\s*([^\s，,。]{2,30})", order_text)
                    if m:
                        target_name = (m.group(1) or "").strip()

                if not target_name:
                    return jsonify({"success": False, "message": "请告诉我要补充哪个客户的联系人信息"}), 400

                field_map = {
                    "contact_person": "联系人",
                    "contact_phone": "联系电话",
                    "contact_address": "地址",
                }
                field_label = field_map.get(field_name, field_name)

                from app.db.session import get_db
                from app.services.unified_query_service import query_service

                customer = query_service.get_first(PurchaseUnit, unit_name=target_name)
                if not customer:
                    return jsonify({"success": False, "message": f"未找到客户：{target_name}"}), 404

                if field_name == "contact_person":
                    customer.contact_person = field_value
                elif field_name == "contact_phone":
                    customer.contact_phone = field_value
                elif field_name == "contact_address":
                    customer.address = field_value

                with get_db() as db:
                    db.commit()

                return jsonify({
                    "success": True,
                    "message": f"已为 {target_name} 补充 {field_label}：{field_value}",
                    "data": {
                        "id": customer.id,
                        "customer_name": customer.unit_name,
                        "contact_person": customer.contact_person,
                        "contact_phone": customer.contact_phone,
                        "contact_address": customer.address,
                    }
                }), 200

            if should_create_purchase_unit:
                import re
                from datetime import datetime

                from app.application import CustomerApplicationService, get_customer_app_service
                from app.db.session import get_db

                unit_name = (params.get("unit_name") or params.get("name") or params.get("customer_name") or "").strip()
                contact_person = (params.get("contact_person") or "").strip()
                contact_phone = (params.get("contact_phone") or "").strip()
                address = (params.get("address") or params.get("contact_address") or "").strip()

                # 兼容：有些模型/上游会把“购买单位 + 联系人”拼成一个字段，
                # 例如：unit_name = "七彩乐园联系人向总"。
                # 这里对 unit_name 做关键词前截断，避免把联系人尾部污染客户名。
                if unit_name:
                    m_unit = re.match(
                        r"^(.+?)(?=(联系人|电话|手机|手机号|联系电话|联系号码|地址|住址|联系地址|$))",
                        unit_name
                    )
                    if m_unit and (m_unit.group(1) or "").strip():
                        unit_name = m_unit.group(1).strip()

                # 从自然语言中尽量提取字段（例如：“添加一个客户叫七彩乐园，联系人是向总”）
                if not unit_name and order_text:
                    m = re.search(r"(?:客户|购买单位|单位)\s*(?:是|叫|名称是|名为)?\s*[:：]?\s*([^\s，,。]{2,30})", order_text)
                    if m:
                        unit_name = (m.group(1) or "").strip()

                if not contact_person and order_text:
                    m = re.search(r"(?:联系人|联系人是)\s*(?:是|：)?\s*([^\s，,。]{1,20})", order_text)
                    if m:
                        contact_person = (m.group(1) or "").strip()

                if not contact_phone and order_text:
                    m = re.search(r"(?:电话|手机|手机号|联系电话|联系号码)\s*(?:是|：)?\s*(\d{5,20})", order_text)
                    if m:
                        contact_phone = (m.group(1) or "").strip()

                if not address and order_text:
                    m = re.search(r"(?:地址|住址|联系地址)\s*(?:是|：)?\s*([^，,。]{2,80})", order_text)
                    if m:
                        address = (m.group(1) or "").strip()

                logger.info(
                    "customers: create extracted unit_name=%s contact_person=%s contact_phone=%s address=%s",
                    unit_name,
                    contact_person,
                    contact_phone,
                    address,
                )

                if not unit_name:
                    logger.warning("customers: create skipped due to missing unit_name")
                    return jsonify({"success": False, "message": "缺少购买单位参数（unit_name/name）"}), 400

                # 为了让聊天添加在界面上可见，同时保证发货单能解析：
                # - `customers` 表：系统唯一来源（发货单解析也只从 customers 解析）

                # 1) 写入 customers（用于前端显示 & 供发货单解析）
                customer_data = {
                    "customer_name": unit_name,
                    "contact_person": contact_person or None,
                    "contact_phone": contact_phone or None,
                    "contact_address": address or None,
                }
                customer_service = get_customer_app_service()
                customer_result = customer_service.create(customer_data)
                if customer_result.get("success"):
                    logger.info("customers: customer created customer_name=%s", unit_name)

                    from app.services import get_task_context_service
                    ctx = get_task_context_service()
                    user_id = request.headers.get("X-User-ID", "default")
                    ctx.set_last_customer(user_id, {
                        "customer_name": unit_name,
                        "contact_person": contact_person,
                        "contact_phone": contact_phone,
                        "contact_address": address,
                    })

                    return jsonify(customer_result), 201

                # 幂等：客户已存在也视为成功（避免前端把“已存在”当失败）
                msg = customer_result.get("message") or ""
                if "客户名称已存在" in msg:
                    from app.services.unified_query_service import find_purchase_unit

                    exists = find_purchase_unit(unit_name=unit_name)
                    customer_id = exists["id"] if exists else None
                    return jsonify({
                        "success": True,
                        "message": "已存在",
                        "data": {
                            "id": customer_id,
                            "customer_name": unit_name,
                            "contact_person": (exists.get("contact_person") if exists else None),
                            "contact_phone": (exists.get("contact_phone") if exists else None),
                            "contact_address": (exists.get("address") if exists else None),
                        }
                    }), 201

                return jsonify(customer_result), 400

            return jsonify({"success": True, "message": "客户管理"})
        
        elif tool_id == 'orders':
            if action == 'view':
                return jsonify({"success": True, "redirect": "/console?view=shipment-orders"})
            return jsonify({"success": True, "message": "出货单"})
        
        elif tool_id == 'shipment_generate':
            if action == 'view':
                return jsonify({"success": True, "redirect": "/console?view=shipment"})
            
            # 真正调用发货单生成 API
            try:
                order_text = params.get("order_text", "")
                direct_products = params.get("products") or []
                direct_unit_name = (params.get("unit_name") or "").strip()
                custom_order_number = (params.get("order_number") or "").strip()

                logger.info("收到发货单生成请求：order_text=%s", order_text)

                from app.services.shipment_number_mode_service import ShipmentNumberModeService

                number_mode_service = ShipmentNumberModeService()
                payload, status_code = number_mode_service.execute(
                    order_text=order_text,
                    custom_order_number=custom_order_number,
                    direct_unit_name=direct_unit_name,
                    direct_products=direct_products if isinstance(direct_products, list) else [],
                    parse_order_text=_parse_order_text,
                )
                return jsonify(payload), status_code

            except Exception as e:
                logger.error(f"生成发货单失败：{e}", exc_info=True)
                return jsonify({
                    "success": False,
                    "message": f"生成失败：{str(e)}"
                }), 500
        
        elif tool_id == 'print':
            from app.services import get_printer_service
            svc = get_printer_service()
            if action == 'view':
                return jsonify({"success": True, "redirect": "/console?view=print"})
            if action in ("list", "query"):
                return jsonify(svc.get_printers()), 200
            if action == "print_label":
                result = svc.print_label(
                    str(params.get("file_path") or "").strip(),
                    params.get("printer_name"),
                    int(params.get("copies") or 1),
                )
                return jsonify(result), 200
            if action == "print_document":
                result = svc.print_document(
                    str(params.get("file_path") or "").strip(),
                    params.get("printer_name"),
                    bool(params.get("use_automation", False)),
                )
                return jsonify(result), 200
            if action == "test":
                result = svc.test_printer(str(params.get("printer_name") or "").strip())
                return jsonify(result), 200
            return jsonify({"success": True, "message": "标签打印"})

        elif tool_id == 'printer_list':
            if action in ("list", "query"):
                from app.services import get_system_service
                return jsonify(get_system_service().get_printer_config()), 200
            if action == "set_default":
                from app.services import get_system_service
                return jsonify(get_system_service().set_default_printer(str(params.get("printer_name") or "").strip())), 200
            return jsonify({"success": True, "redirect": "/console?view=printer-list", "message": "已打开打印机列表"})
        
        elif tool_id == 'materials':
            from app.application import get_material_application_service
            svc = get_material_application_service()
            if action == 'view':
                return jsonify({"success": True, "redirect": "/console?view=materials"})
            if action in ("list", "query"):
                return jsonify(svc.get_all_materials(
                    search=str(params.get("search") or params.get("keyword") or "").strip(),
                    category=str(params.get("category") or "").strip() or None,
                    page=int(params.get("page") or 1),
                    per_page=int(params.get("per_page") or 20),
                )), 200
            if action == "create":
                return jsonify(svc.create_material(dict(params or {}))), 200
            if action == "update":
                material_id = int(params.get("id"))
                payload = {k: v for k, v in params.items() if k != "id"}
                return jsonify(svc.update_material(material_id, **payload)), 200
            if action == "delete":
                return jsonify(svc.delete_material(int(params.get("id")))), 200
            if action == "batch_delete":
                ids = [int(x) for x in (params.get("ids") or params.get("material_ids") or []) if str(x).strip()]
                return jsonify(svc.batch_delete_materials(ids)), 200
            if action == "export":
                return jsonify(svc.export_to_excel(
                    search=str(params.get("search") or params.get("keyword") or "").strip() or None,
                    category=str(params.get("category") or "").strip() or None,
                    template_id=params.get("template_id"),
                )), 200
            return jsonify({"success": True, "message": "原材料仓库"})
        
        elif tool_id == 'ocr':
            if action == 'view':
                return jsonify({"success": True, "redirect": "/console?view=ocr"})
            return jsonify({"success": True, "message": "图片 OCR"})
        
        elif tool_id == 'wechat':
            from app.application import get_wechat_contact_app_service
            svc = get_wechat_contact_app_service()
            if action == 'view':
                return jsonify({"success": True, "redirect": "/console?view=wechat-contacts"})
            if action in ("list", "query"):
                contacts = svc.get_contacts(
                    contact_type=str(params.get("type") or "all"),
                    keyword=str(params.get("keyword") or "").strip() or None,
                    limit=int(params.get("limit") or 100),
                )
                return jsonify({"success": True, "data": contacts, "total": len(contacts)}), 200
            if action in ("refresh_contact_cache", "refresh_messages_cache"):
                from app.routes.wechat_contacts import _ensure_decrypted_db
                return jsonify(_ensure_decrypted_db()), 200
            return jsonify({"success": True, "message": "微信任务"})
        
        elif tool_id == 'excel_decompose':
            if action == 'view':
                return jsonify({"success": True, "redirect": "/console?view=excel"})
            return jsonify({"success": True, "message": "Excel 模板分解"})

        elif tool_id == 'excel_analyzer':
            file_path = params.get('file_path')
            sheet_name = params.get('sheet_name')
            output_json = params.get('output_json')

            if not file_path:
                return jsonify({
                    "success": False,
                    "message": "缺少参数：file_path（Excel文件路径）"
                }), 400

            try:
                from app.infrastructure.skills.excel_analyzer.excel_template_analyzer import (
                    ExcelAnalyzerSkill,
                    get_excel_analyzer_skill,
                )
                skill = get_excel_analyzer_skill()
                result = skill.execute(file_path=file_path, sheet_name=sheet_name, output_json=output_json)
                return jsonify(result)
            except ImportError:
                return jsonify({
                    "success": False,
                    "message": "Excel分析技能未正确安装，请检查openpyxl库"
                }), 500
            except Exception as e:
                logger.error(f"Excel Analyzer执行失败: {e}")
                return jsonify({
                    "success": False,
                    "message": f"分析失败: {str(e)}"
                }), 500

        elif tool_id == 'template_extract':
            if action in (None, '', 'view'):
                return jsonify({
                    "success": True,
                    "redirect": "/console?view=business-docking",
                    "message": "请先上传 Excel 并提取模板"
                }), 200

            file_path = str(params.get('file_path') or "").strip()
            sheet_name = str(params.get('sheet_name') or "").strip() or None

            if not file_path:
                return jsonify({
                    "success": False,
                    "message": "缺少参数：file_path（Excel文件路径）"
                }), 400

            try:
                import os
                from app.routes.templates import (
                    _extract_excel_grid_preview,
                    _extract_structured_excel_preview,
                    _list_excel_sheet_names,
                )

                if not os.path.exists(file_path):
                    return jsonify({
                        "success": False,
                        "message": f"文件不存在：{file_path}"
                    }), 404

                sheet_names = _list_excel_sheet_names(file_path)
                structured = _extract_structured_excel_preview(file_path, sheet_name=sheet_name, sample_limit=8)
                grid_preview = _extract_excel_grid_preview(file_path, sheet_name=sheet_name, max_rows=24, max_cols=14)
                selected_sheet_name = (
                    structured.get("sheet_name")
                    or grid_preview.get("sheet_name")
                    or sheet_name
                    or (sheet_names[0] if sheet_names else "")
                )
                template_name = os.path.splitext(os.path.basename(file_path))[0]

                return jsonify({
                    "success": True,
                    "template_name": template_name,
                    "template_type": "excel",
                    "file_path": file_path,
                    "fields": structured.get("fields") or [],
                    "preview_data": {
                        "sample_rows": structured.get("sample_rows") or [],
                        "sheet_name": structured.get("sheet_name") or sheet_name or "",
                        "selected_sheet_name": selected_sheet_name,
                        "sheet_names": sheet_names,
                        "grid_preview": grid_preview,
                        "file_path": file_path,
                    }
                }), 200
            except Exception as e:
                logger.error(f"template_extract 执行失败: {e}", exc_info=True)
                return jsonify({
                    "success": False,
                    "message": f"提取失败: {str(e)}"
                }), 500

        elif tool_id == 'excel_toolkit':
            file_path = params.get('file_path')
            sheet_name = params.get('sheet_name')
            toolkit_action = params.get('action', 'view')

            if not file_path:
                return jsonify({
                    "success": False,
                    "message": "缺少参数：file_path（Excel文件路径）"
                }), 400

            try:
                from app.infrastructure.skills.excel_toolkit.excel_toolkit import (
                    ExcelToolkitSkill,
                    get_excel_toolkit_skill,
                )
                skill = get_excel_toolkit_skill()
                result = skill.execute(file_path=file_path, action=toolkit_action, sheet_name=sheet_name)
                return jsonify(result)
            except ImportError:
                return jsonify({
                    "success": False,
                    "message": "Excel工具技能未正确安装，请检查openpyxl库"
                }), 500
            except Exception as e:
                logger.error(f"Excel Toolkit执行失败: {e}")
                return jsonify({
                    "success": False,
                    "message": f"执行失败: {str(e)}"
                }), 500

        elif tool_id == 'shipment_template':
            if action == 'view':
                return jsonify({"success": True, "redirect": "/console?view=template-preview"})
            return jsonify({"success": True, "message": "发货单模板"})

        elif tool_id == 'template_preview':
            if action in ("list", "query"):
                from app.application import get_template_app_service
                result = get_template_app_service().get_templates()
                if isinstance(result, dict):
                    return jsonify(result), 200
                return jsonify({"success": True, "data": result}), 200
            return jsonify({"success": True, "redirect": "/console?view=template-preview", "message": "已打开模板预览"})

        elif tool_id == 'settings':
            from app.services import get_system_service
            svc = get_system_service()
            if action in ("query", "get_system_info"):
                return jsonify({"success": True, "data": svc.get_system_info()}), 200
            if action == "get_startup_config":
                return jsonify({"success": True, "data": svc.get_startup_config()}), 200
            if action == "enable_startup":
                return jsonify(svc.enable_startup()), 200
            if action == "disable_startup":
                return jsonify(svc.disable_startup()), 200
            return jsonify({"success": True, "redirect": "/console?view=settings", "message": "已打开系统设置"})

        elif tool_id == 'tools_table':
            if action in ("list", "query"):
                return get_tools_list()
            return jsonify({"success": True, "redirect": "/console?view=tools", "message": "已打开工具表"})

        elif tool_id == 'other_tools':
            if action in ("list", "query"):
                return jsonify({"success": True, "tools": ["database", "ocr", "excel_toolkit", "excel_analyzer", "template_extract"]}), 200
            return jsonify({"success": True, "redirect": "/console?view=other-tools", "message": "已打开其他工具"})
        
        elif tool_id == 'database':
            from app.services import get_database_service
            
            db_service = get_database_service()

            # 兼容测试：仅传 tool_id 时也视为可用（返回 200 success true）
            if action in (None, '', 'view'):
                return jsonify({"success": True, "message": "数据库管理"}), 200
            
            if action == 'backup':
                result = db_service.backup_database()
                return jsonify(result)
            
            elif action == 'restore':
                backup_file = params.get('backup_file')
                if not backup_file:
                    return jsonify({
                        "success": False,
                        "message": "缺少参数：backup_file"
                    }), 400
                result = db_service.restore_database(backup_file)
                return jsonify(result)
            
            elif action == 'list':
                result = db_service.list_backups()
                return jsonify(result)
            
            elif action == 'delete':
                backup_file = params.get('backup_file')
                if not backup_file:
                    return jsonify({
                        "success": False,
                        "message": "缺少参数：backup_file"
                    }), 400
                result = db_service.delete_backup(backup_file)
                return jsonify(result)
            
            else:
                return jsonify({
                    "success": False,
                    "message": f"未知的数据库操作：{action}"
                }), 400
        
        elif tool_id == 'system':
            from app.services import get_system_service
            
            system_service = get_system_service()

            # 兼容测试：仅传 tool_id 时也视为可用（返回 200 success true）
            if action in (None, '', 'view'):
                return jsonify({"success": True, "message": "系统设置"}), 200
            
            if action == 'get_startup_config':
                result = system_service.get_startup_config()
                return jsonify({"success": True, "data": result})
            
            elif action == 'enable_startup':
                result = system_service.enable_startup()
                return jsonify(result)
            
            elif action == 'disable_startup':
                result = system_service.disable_startup()
                return jsonify(result)
            
            elif action == 'get_system_info':
                result = system_service.get_system_info()
                return jsonify({"success": True, "data": result})
            
            elif action == 'get_printer_config':
                result = system_service.get_printer_config()
                return jsonify(result)
            
            elif action == 'set_default_printer':
                printer_name = params.get('printer_name')
                if not printer_name:
                    return jsonify({
                        "success": False,
                        "message": "缺少参数：printer_name"
                    }), 400
                result = system_service.set_default_printer(printer_name)
                return jsonify(result)
            
            else:
                return jsonify({
                    "success": False,
                    "message": f"未知的系统操作：{action}"
                }), 400
        
        elif tool_id == 'upload_file':
            # upload_file 是“让用户上传文件”的 UI 引导工具。
            # 该接口本身不执行解析/入库，仅返回前端可触发上传浮层的提示文案。
            msg = "请上传文件以继续（Excel / 图片 / CSV 均可）。"
            return jsonify({"success": True, "message": msg}), 200
        
        return jsonify({"success": False, "message": f"未知工具: {tool_id}"}), 400
        
    except Exception as e:
        logger.error(f"执行工具失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500