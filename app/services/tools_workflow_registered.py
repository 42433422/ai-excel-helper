"""已注册工作流工具：按 tool_id 路由到实现（自 tools_execution_service 拆分）。"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable

logger = logging.getLogger(__name__)


def _registered_router_normal_slot_dispatch(
    action: str, params: dict, runtime_context: dict, profile: str, user_message: str
) -> dict:
    from app.application.normal_chat_dispatch import (
        run_normal_slot_product_query_from_message,
        run_normal_slot_shipment_preview,
    )

    if action == "product_query":
        text = user_message or str(params.get("message") or "").strip()
        return run_normal_slot_product_query_from_message(text)
    if action == "shipment_preview":
        order_text = str(params.get("order_text") or user_message or "").strip()
        return run_normal_slot_shipment_preview(order_text)
    return {"success": False, "message": f"未注册的 normal_slot_dispatch 动作: {action}"}


def _registered_router_customers(
    action: str, params: dict, runtime_context: dict, profile: str, user_message: str
) -> dict:
    from app.application import get_customer_app_service

    svc = get_customer_app_service()
    unit_name = str(
        params.get("unit_name") or params.get("customer_name") or params.get("name") or ""
    ).strip()
    if action == "query":
        keyword = str(params.get("keyword") or unit_name or "").strip()
        result = svc.get_all(keyword=keyword, page=1, per_page=20)
        return {
            "success": bool(result.get("success")),
            "data": result.get("data", []),
            "raw": result,
        }

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


def _registered_router_products(
    action: str, params: dict, runtime_context: dict, profile: str, user_message: str
) -> dict:
    from app.application.normal_chat_dispatch import run_workflow_products_query_normal_profile
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
        return {
            "success": bool(result.get("success")),
            "data": result.get("data", []),
            "raw": result,
        }

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


def _registered_router_materials(
    action: str, params: dict, runtime_context: dict, profile: str, user_message: str
) -> dict:
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
        payload.setdefault(
            "name", str(payload.get("name") or payload.get("material_name") or "").strip()
        )
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


def _registered_router_shipment_records(
    action: str, params: dict, runtime_context: dict, profile: str, user_message: str
) -> dict:
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


def _registered_router_business_docking_family(
    action: str, params: dict, runtime_context: dict, profile: str, user_message: str
) -> dict:
    if action in ("view",):
        return {"success": True, "redirect": "/console?view=business-docking"}
    file_path = str(params.get("file_path") or "").strip()
    if not file_path:
        return {"success": False, "message": "缺少参数：file_path"}
    from app.services.document_templates_service import (
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
    grid_preview = _extract_excel_grid_preview(
        file_path, sheet_name=sheet_name, max_rows=24, max_cols=14
    )
    style_cache = _extract_excel_grid_style_cache(
        file_path, sheet_name=sheet_name, max_rows=24, max_cols=14
    )
    all_sheets = _extract_excel_all_sheets_preview(
        file_path, sample_limit=8, max_rows=24, max_cols=14
    )
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


def _registered_router_template_preview(
    action: str, params: dict, runtime_context: dict, profile: str, user_message: str
) -> dict:
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
        from app.services.document_templates_service import (
            _ensure_template_tables_ready,
            _infer_business_scope,
            _validate_required_terms,
        )

        excel_analysis = params.get("excel_analysis")
        if not isinstance(excel_analysis, dict):
            excel_analysis = runtime_context.get("excel_analysis")
        if not isinstance(excel_analysis, dict):
            fallback_ctx = runtime_context.get("last_excel_analysis_context")
            if isinstance(fallback_ctx, dict):
                excel_analysis = (
                    fallback_ctx.get("result")
                    if isinstance(fallback_ctx.get("result"), dict)
                    else fallback_ctx
                )
        excel_analysis = excel_analysis if isinstance(excel_analysis, dict) else {}

        sheets = excel_analysis.get("sheets")
        if not isinstance(sheets, list):
            preview_data = (
                excel_analysis.get("preview_data")
                if isinstance(excel_analysis.get("preview_data"), dict)
                else {}
            )
            sheets = (
                preview_data.get("all_sheets")
                if isinstance(preview_data.get("all_sheets"), list)
                else []
            )

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

        fields = (
            selected_sheet.get("fields") if isinstance(selected_sheet.get("fields"), list) else []
        )
        preview_data = {
            "sheet_name": picked_sheet_name,
            "selected_sheet_name": picked_sheet_name,
            "sample_rows": (
                selected_sheet.get("sample_rows")
                if isinstance(selected_sheet.get("sample_rows"), list)
                else []
            ),
            "grid_preview": (
                selected_sheet.get("grid_preview")
                if isinstance(selected_sheet.get("grid_preview"), dict)
                else {}
            ),
            "grid_style_cache": (
                selected_sheet.get("style_cache")
                if isinstance(selected_sheet.get("style_cache"), dict)
                else {}
            ),
        }
        template_type = str(params.get("template_type") or "Excel").strip()
        business_scope = str(
            params.get("business_scope") or _infer_business_scope(template_type) or ""
        ).strip()
        source = str(params.get("source") or "ai-natural-language").strip() or "ai-natural-language"
        file_path = (
            str(params.get("file_path") or excel_analysis.get("file_path") or "").strip() or None
        )

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
        template_key = (
            f"TPL_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8].upper()}"
        )
        with get_db() as db:
            result = db.execute(
                text(
                    """
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
                """
                ),
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


def _registered_router_wechat(
    action: str, params: dict, runtime_context: dict, profile: str, user_message: str
) -> dict:
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
        from app.services.wechat_contact_cache_import import (
            ensure_decrypted_wechat_dbs as _ensure_decrypted_db,
        )

        return _ensure_decrypted_db()


def _registered_router_print(
    action: str, params: dict, runtime_context: dict, profile: str, user_message: str
) -> dict:
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


def _registered_router_printer_list(
    action: str, params: dict, runtime_context: dict, profile: str, user_message: str
) -> dict:
    from app.services import get_system_service

    svc = get_system_service()
    if action == "view":
        return {"success": True, "redirect": "/console?view=printer-list"}
    if action in ("list", "query"):
        return svc.get_printer_config()
    if action == "set_default":
        return svc.set_default_printer(str(params.get("printer_name") or "").strip())


def _registered_router_settings(
    action: str, params: dict, runtime_context: dict, profile: str, user_message: str
) -> dict:
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


def _registered_router_excel_analysis(
    action: str, params: dict, runtime_context: dict, profile: str, user_message: str
) -> dict:
    file_path = str(params.get("file_path") or "").strip()
    if not file_path:
        excel_ctx = (
            runtime_context.get("excel_analysis")
            if isinstance(runtime_context.get("excel_analysis"), dict)
            else None
        )
        if not excel_ctx:
            last_ctx = runtime_context.get("last_excel_analysis_context")
            if isinstance(last_ctx, dict):
                excel_ctx = (
                    last_ctx.get("result") if isinstance(last_ctx.get("result"), dict) else last_ctx
                )
        if isinstance(excel_ctx, dict):
            file_path = str(excel_ctx.get("file_path") or "").strip()
    if not file_path:
        return {"success": False, "message": "excel_analysis 缺少 file_path 参数"}

    question = str(params.get("question") or "").strip()

    try:
        from app.infrastructure.skills.excel_analyzer.excel_template_analyzer import (
            get_excel_analyzer_skill,
        )
        from app.infrastructure.skills.excel_toolkit.excel_toolkit import get_excel_toolkit_skill
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
            for cell in row.get("cells") or []:
                v = cell.get("value")
                if v is not None:
                    try:
                        all_values.append(float(v))
                    except (TypeError, ValueError):
                        pass
        if all_values:
            stats = {
                "count": len(all_values),
                "sum": round(sum(all_values), 4),
                "avg": round(sum(all_values) / len(all_values), 4),
                "min": min(all_values),
                "max": max(all_values),
            }
        else:
            stats = {"count": 0}
        return {
            "success": True,
            "file_path": file_path,
            "total_rows": total_rows,
            "statistics": stats,
        }

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
                for cell in row.get("cells") or []:
                    try:
                        all_vals.append(float(cell.get("value")))
                    except (TypeError, ValueError):
                        pass
            total = sum(all_vals) if all_vals else 0
            return {"success": True, "answer": f"所有数值总和为 {round(total, 4)}", "total": total}
        if any(kw in question_lower for kw in ["最大", "最高", "max"]):
            all_vals = [
                float(c.get("value"))
                for row in content
                for c in (row.get("cells") or [])
                if c.get("value") is not None
            ]
            try:
                mx = max(all_vals)
                return {"success": True, "answer": f"最大值为 {mx}", "max": mx}
            except ValueError:
                return {"success": True, "answer": "未找到数值"}
        return {
            "success": True,
            "data": content[:20],
            "message": f"已读取前 {min(20, len(content))} 行数据",
        }

    return {"success": False, "message": f"未知 excel_analysis action: {action}"}


def _registered_router_excel_import(
    action: str, params: dict, runtime_context: dict, profile: str, user_message: str
) -> dict:
    if action == "execute_import":
        pending_import_id = str(params.get("pending_import_id") or "").strip()
        if not pending_import_id:
            return {"success": False, "message": "缺少 pending_import_id 参数"}

        # 从 AI Chat Service 获取待处理的导入数据
        from app.application import get_ai_chat_app_service

        ai_chat_service = get_ai_chat_app_service()
        pending_imports = getattr(ai_chat_service, "_pending_excel_imports", {})
        import_data = pending_imports.get(pending_import_id)

        if not import_data:
            return {"success": False, "message": "未找到待处理的导入数据或已过期"}

        records = import_data.get("records", [])
        if not records:
            return {"success": False, "message": "没有可导入的记录"}

        try:
            from app.bootstrap import get_customer_app_service, get_products_service

            products_service = get_products_service()
            customer_service = get_customer_app_service()

            created_units = 0
            created_products = 0
            skipped_products = 0
            touched_units: set[str] = set()

            for row in records:
                unit_name = str(row.get("unit_name") or "").strip()
                product_name = str(row.get("product_name") or "").strip()
                model_number = str(row.get("model_number") or "").strip().upper()
                unit_price = float(row.get("unit_price") or 0.0)
                touched_units.add(unit_name)

                # 检查/创建购买单位
                if customer_service is not None:
                    matched = customer_service.match_purchase_unit(unit_name)
                    if not matched:
                        create_unit = customer_service.create({"customer_name": unit_name})
                        if create_unit.get("success"):
                            created_units += 1

                # 检查产品是否已存在
                exists_result = products_service.get_products(
                    unit_name=unit_name,
                    model_number=model_number or None,
                    keyword=(product_name or model_number or None),
                    page=1,
                    per_page=5,
                )
                existed = False
                if exists_result.get("success"):
                    rows_data = exists_result.get("data") or []
                    for item in rows_data:
                        item_name = str(item.get("name") or item.get("product_name") or "").strip()
                        item_model = str(item.get("model_number") or "").strip().upper()
                        if model_number and item_model == model_number:
                            existed = True
                            break
                        if product_name and item_name == product_name:
                            existed = True
                            break
                if existed:
                    skipped_products += 1
                    continue

                # 创建产品
                create_product = products_service.create_product(
                    {
                        "name": product_name or model_number,
                        "product_name": product_name or model_number,
                        "product_code": model_number or None,
                        "model_number": model_number or None,
                        "unit_price": unit_price,
                        "price": unit_price,
                        "unit": unit_name,
                    }
                )
                if create_product.get("success"):
                    created_products += 1

            # 清理已处理的导入数据
            pending_imports.pop(pending_import_id, None)

            return {
                "success": True,
                "message": "Excel 导入完成",
                "data": {
                    "result": {
                        "records": len(records),
                        "touched_units": len(touched_units),
                        "created_units": created_units,
                        "created_products": created_products,
                        "skipped_products": skipped_products,
                    }
                },
            }
        except Exception as err:
            logger.error("Excel 导入执行失败: %s", err, exc_info=True)
            return {"success": False, "message": f"导入执行失败：{str(err)}"}

    return {"success": False, "message": f"未知 excel_import action: {action}"}


_REGISTERED_WORKFLOW_ROUTERS: dict[str, Callable[..., dict]] = {
    "normal_slot_dispatch": _registered_router_normal_slot_dispatch,
    "customers": _registered_router_customers,
    "products": _registered_router_products,
    "materials": _registered_router_materials,
    "shipment_records": _registered_router_shipment_records,
    "business_docking": _registered_router_business_docking_family,
    "template_extract": _registered_router_business_docking_family,
    "template_preview": _registered_router_template_preview,
    "wechat": _registered_router_wechat,
    "print": _registered_router_print,
    "printer_list": _registered_router_printer_list,
    "settings": _registered_router_settings,
    "excel_analysis": _registered_router_excel_analysis,
    "excel_import": _registered_router_excel_import,
}


def execute_registered_workflow_tool(tool_id: str, action: str, params: dict | None = None) -> dict:
    """统一 dispatcher（供 WorkflowEngine 与 /api/tools/execute 复用）。"""
    from app.application.normal_chat_dispatch import resolve_tool_execution_profile

    params = dict(params or {})
    runtime_context = dict(params.pop("_runtime_context", None) or {})
    profile = resolve_tool_execution_profile(runtime_context)
    user_message = str(runtime_context.get("message") or "").strip()

    router = _REGISTERED_WORKFLOW_ROUTERS.get(tool_id)
    if router is not None:
        return router(action, params, runtime_context, profile, user_message)
    return {"success": False, "message": f"未注册的工具动作: {tool_id}.{action}"}
