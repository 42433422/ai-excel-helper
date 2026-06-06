"""Legacy /api/tools/execute 分支（原 tools_execution_service 巨型 elif）。"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def dispatch_legacy_tool_payload(
    tool_id,
    action: str,
    params: dict,
    *,
    json_response_fn,
    hdr_getter,
    parse_order_text_fn,
):
    """返回与原先 elif 分支相同的 Werkzeug JSON Response。"""
    _j = json_response_fn
    _hdr = hdr_getter
    _parse_order_text = parse_order_text_fn

    if tool_id == "products":
        effective_action = action
        if action in ("执行", "exec", "run", "execute"):
            effective_action = params.get("action", "view")

        keyword = (params.get("keyword") or "").strip()
        unit_name = (params.get("unit_name") or "").strip()
        model_number = (params.get("model_number") or "").strip()
        tin_spec = (params.get("tin_spec") or "").strip()

        search_verbs = ["search", "query", "find", "查找", "查询", "搜索"]
        is_search = (effective_action in search_verbs) or keyword

        if is_search and keyword:
            return _j(
                {
                    "success": True,
                    "redirect": f"/console?view=products&keyword={keyword}",
                    "message": f"已按关键词检索产品：{keyword}",
                    "data": {
                        "keyword": keyword,
                        "unit_name": unit_name,
                        "model_number": model_number,
                        "tin_spec": tin_spec,
                    },
                }
            )
        if effective_action == "view":
            return _j({"success": True, "redirect": "/console?view=products"})
        return _j({"success": True, "message": "产品管理"})

    elif tool_id == "chat":
        return _j({"success": True, "redirect": "/console?view=chat", "message": "已打开智能对话"})

    elif tool_id == "ai_ecosystem":
        if action in ("list", "query"):
            return _j(
                {
                    "success": True,
                    "data": {
                        "views": ["ai-ecosystem"],
                        "integrations": ["deepseek", "bert", "rasa", "workflow-planner"],
                    },
                },
                200,
            )
        return _j(
            {"success": True, "redirect": "/console?view=ai-ecosystem", "message": "已打开AI生态"}
        )

    elif tool_id == "materials_list":
        if action in ("query", "list"):
            from app.application import get_material_application_service

            svc = get_material_application_service()
            result = svc.get_all_materials(
                search=str(params.get("search") or params.get("keyword") or "").strip(),
                category=str(params.get("category") or "").strip() or None,
                page=int(params.get("page") or 1),
                per_page=int(params.get("per_page") or 20),
            )
            return _j(result, 200)
        return _j(
            {
                "success": True,
                "redirect": "/console?view=materials-list",
                "message": "已打开原材料列表",
            }
        )

    elif tool_id == "business_docking":
        if action in ("extract", "preview", "analyze"):
            file_path = str(params.get("file_path") or "").strip()
            if not file_path:
                return _j(
                    {"success": False, "message": "缺少参数：file_path（Excel文件路径）"}, 400
                )
            from app.services.document_templates_service import (
                _extract_excel_grid_preview,
                _extract_structured_excel_preview,
                _list_excel_sheet_names,
            )

            if not os.path.exists(file_path):
                return _j({"success": False, "message": f"文件不存在：{file_path}"}, 404)
            sheet_name = str(params.get("sheet_name") or "").strip() or None
            return _j(
                {
                    "success": True,
                    "file_path": file_path,
                    "sheet_names": _list_excel_sheet_names(file_path),
                    "structured": _extract_structured_excel_preview(
                        file_path, sheet_name=sheet_name, sample_limit=8
                    ),
                    "grid_preview": _extract_excel_grid_preview(
                        file_path, sheet_name=sheet_name, max_rows=24, max_cols=14
                    ),
                },
                200,
            )
        return _j(
            {
                "success": True,
                "redirect": "/console?view=business-docking",
                "message": "已打开业务对接",
            }
        )

    elif tool_id == "shipment_records":
        from app.bootstrap import get_shipment_app_service

        svc = get_shipment_app_service()
        if action in ("list", "query"):
            unit = str(params.get("unit") or params.get("unit_name") or "").strip() or None
            return _j({"success": True, "data": svc.get_shipment_records(unit)}, 200)
        if action == "update":
            record_id = int(params.get("id"))
            payload = {k: v for k, v in params.items() if k != "id"}
            return _j(svc.update_shipment_record(record_id=record_id, **payload), 200)
        if action == "delete":
            return _j(svc.delete_shipment_record(int(params.get("id"))), 200)
        if action == "export":
            result = svc.export_shipment_records(
                unit_name=str(params.get("unit") or params.get("unit_name") or "").strip() or None,
                template_id=params.get("template_id"),
                status_filter=params.get("status"),
            )
            return _j(result, 200)
        return _j(
            {
                "success": True,
                "redirect": "/console?view=shipment-records",
                "message": "已打开出货记录",
            }
        )

    elif tool_id == "customers":
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
        if (
            effective_action in ("search", "query")
            and not keyword
            and not has_add_verb
            and not has_del_verb
        ):
            keyword = (
                params.get("unit_name") or params.get("name") or params.get("customer_name") or ""
            ).strip()
        # 如果自然语言包含“添加/新增/创建”，即便 AI 把 action 判成 search/query，也应优先创建。
        if (
            effective_action in ("search", "query")
            and keyword
            and not has_add_verb
            and not has_del_verb
        ):
            logger.info("customers: redirect search/query keyword=%s", keyword)
            return _j(
                {
                    "success": True,
                    "redirect": f"/console?view=customers&keyword={keyword}",
                    "message": f"已按关键词检索客户：{keyword}",
                }
            )
        if effective_action == "view" and not has_add_verb and not has_del_verb:
            logger.info("customers: redirect view")
            return _j({"success": True, "redirect": "/console?view=customers"})

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
            target_name = (
                params.get("customer_name") or params.get("unit_name") or params.get("name") or ""
            ).strip()

            # 尽量从自然语言中提取名称：如“删除客户/购买单位叫XX”
            if not target_name and order_text:
                import re

                # 支持：包含“联系人/电话/地址”后缀的删除句式
                # 例：删除购买单位小王公司联系人王总  -> 提取“小王公司”
                m = re.search(
                    r"(?:删除|移除)?\s*(?:客户|购买单位|单位)\s*(?:叫|是|名称是|名为)?\s*[:：]?\s*([^\s，,。]{2,60}?)"
                    r"(?=(?:联系人|电话|手机|手机号|联系电话|联系号码|地址|住址)|\s*$)",
                    order_text,
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
                        if (
                            resolved
                            and getattr(resolved, "unit_name", None)
                            and resolved.unit_name != target_name
                        ):
                            deleted_count = query_service.delete(
                                PurchaseUnit, unit_name=resolved.unit_name
                            )
                    except Exception as e:
                        logger.warning(f"解析购买单位失败: {e}")

            return _j(
                {
                    "success": True,
                    "message": "删除成功" if deleted_count > 0 else "删除成功（未找到匹配记录）",
                    "deleted_count": deleted_count,
                },
                200,
            )
        # 聊天创建购买单位兜底：
        # 当用户表达“添加客户/购买单位 + 名称/联系人/电话/地址”时，直接写入 purchase_units。
        # 这与前端 pro-feature-widget 里 POST /api/purchase_units 的字段对齐。
        should_create_purchase_unit = (
            str(effective_action)
            in {"add", "create", "添加", "新增", "添加客户", "添加购买单位", "create_purchase_unit"}
            or has_add_verb
        )

        # 补充客户信息处理（他/她/它的 联系人/电话/地址）
        should_supplement = str(effective_action) in {"supplement", "补充"} or params.get(
            "field_name"
        )

        if should_supplement:
            from app.db.models import PurchaseUnit
            from app.db.session import get_db
            from app.services import get_task_context_service
            from app.services.unified_query_service import query_service

            ctx = get_task_context_service()
            user_id = params.get("user_id") or _hdr("X-User-ID", "default")

            last_customer = ctx.get_last_customer(user_id)
            field_name = params.get("field_name", "")
            field_value = params.get("field_value", "")

            if not field_name and order_text:
                m = re.search(
                    r"(?:联系人|联系电话|电话|手机|地址)\s*(?:是|：|:)?\s*(.{1,30})", order_text
                )
                if m:
                    field_name = "contact_person"
                    field_value = m.group(1).strip()

            if not field_value and order_text:
                if field_name == "contact_person":
                    m = re.search(
                        r"(?:联系人|联系人是)\s*(?:是|：|:)?\s*([^\s，,。]{1,20})", order_text
                    )
                    if m:
                        field_value = m.group(1).strip()
                elif field_name in ("contact_phone", "contact_address"):
                    m = re.search(
                        r"(?:电话|手机|地址)\s*(?:是|：|:)?\s*([^\s，,。]{1,50})", order_text
                    )
                    if m:
                        field_value = m.group(1).strip()

            if not last_customer and not field_value:
                return _j(
                    {
                        "success": False,
                        "message": "请先告诉我要补充哪个客户的联系人信息，例如：添加客户七彩乐园",
                    },
                    400,
                )

            target_name = last_customer.get("customer_name") if last_customer else None
            if not target_name:
                m = re.search(
                    r"(?:客户|购买单位|单位)\s*(?:是|叫|名称是|名为)?\s*[:：]?\s*([^\s，,。]{2,30})",
                    order_text,
                )
                if m:
                    target_name = (m.group(1) or "").strip()

            if not target_name:
                return _j({"success": False, "message": "请告诉我要补充哪个客户的联系人信息"}, 400)

            field_map = {
                "contact_person": "联系人",
                "contact_phone": "联系电话",
                "contact_address": "地址",
            }
            field_label = field_map.get(field_name, field_name)

            from app.services.unified_query_service import query_service

            customer = query_service.get_first(PurchaseUnit, unit_name=target_name)
            if not customer:
                return _j({"success": False, "message": f"未找到客户：{target_name}"}, 404)

            if field_name == "contact_person":
                customer.contact_person = field_value
            elif field_name == "contact_phone":
                customer.contact_phone = field_value
            elif field_name == "contact_address":
                customer.address = field_value

            with get_db() as db:
                db.commit()

            return _j(
                {
                    "success": True,
                    "message": f"已为 {target_name} 补充 {field_label}：{field_value}",
                    "data": {
                        "id": customer.id,
                        "customer_name": customer.unit_name,
                        "contact_person": customer.contact_person,
                        "contact_phone": customer.contact_phone,
                        "contact_address": customer.address,
                    },
                },
                200,
            )
        if should_create_purchase_unit:
            import re

            from app.application import get_customer_app_service
            from app.db.session import get_db

            unit_name = (
                params.get("unit_name") or params.get("name") or params.get("customer_name") or ""
            ).strip()
            contact_person = (params.get("contact_person") or "").strip()
            contact_phone = (params.get("contact_phone") or "").strip()
            address = (params.get("address") or params.get("contact_address") or "").strip()

            # 兼容：有些模型/上游会把“购买单位 + 联系人”拼成一个字段，
            # 例如：unit_name = "七彩乐园联系人向总"。
            # 这里对 unit_name 做关键词前截断，避免把联系人尾部污染客户名。
            if unit_name:
                m_unit = re.match(
                    r"^(.+?)(?=(联系人|电话|手机|手机号|联系电话|联系号码|地址|住址|联系地址|$))",
                    unit_name,
                )
                if m_unit and (m_unit.group(1) or "").strip():
                    unit_name = m_unit.group(1).strip()

            # 从自然语言中尽量提取字段（例如：“添加一个客户叫七彩乐园，联系人是向总”）
            if not unit_name and order_text:
                m = re.search(
                    r"(?:客户|购买单位|单位)\s*(?:是|叫|名称是|名为)?\s*[:：]?\s*([^\s，,。]{2,30})",
                    order_text,
                )
                if m:
                    unit_name = (m.group(1) or "").strip()

            if not contact_person and order_text:
                m = re.search(r"(?:联系人|联系人是)\s*(?:是|：)?\s*([^\s，,。]{1,20})", order_text)
                if m:
                    contact_person = (m.group(1) or "").strip()

            if not contact_phone and order_text:
                m = re.search(
                    r"(?:电话|手机|手机号|联系电话|联系号码)\s*(?:是|：)?\s*(\d{5,20})", order_text
                )
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
                return _j({"success": False, "message": "缺少购买单位参数（unit_name/name）"}, 400)

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
                user_id = _hdr("X-User-ID", "default")
                ctx.set_last_customer(
                    user_id,
                    {
                        "customer_name": unit_name,
                        "contact_person": contact_person,
                        "contact_phone": contact_phone,
                        "contact_address": address,
                    },
                )

                return _j(customer_result, 201)

            # 幂等：客户已存在也视为成功（避免前端把“已存在”当失败）
            msg = customer_result.get("message") or ""
            if "客户名称已存在" in msg:
                from app.services.unified_query_service import find_purchase_unit

                exists = find_purchase_unit(unit_name=unit_name)
                customer_id = exists["id"] if exists else None
                return _j(
                    {
                        "success": True,
                        "message": "已存在",
                        "data": {
                            "id": customer_id,
                            "customer_name": unit_name,
                            "contact_person": (exists.get("contact_person") if exists else None),
                            "contact_phone": (exists.get("contact_phone") if exists else None),
                            "contact_address": (exists.get("address") if exists else None),
                        },
                    },
                    201,
                )
            return _j(customer_result, 400)

        return _j({"success": True, "message": "客户管理"})

    elif tool_id == "orders":
        if action == "view":
            return _j({"success": True, "redirect": "/console?view=shipment-orders"})
        return _j({"success": True, "message": "出货单"})

    elif tool_id == "shipment_generate":
        if action == "view":
            return _j({"success": True, "redirect": "/console?view=shipment"})

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
            return _j(payload, status_code)

        except Exception as e:
            logger.error(f"生成发货单失败：{e}", exc_info=True)
            return _j({"success": False, "message": f"生成失败：{str(e)}"}, 500)
    elif tool_id == "print":
        from app.services import get_printer_service

        svc = get_printer_service()
        if action == "view":
            return _j({"success": True, "redirect": "/console?view=print"})
        if action in ("list", "query"):
            return _j(svc.get_printers(), 200)
        if action == "print_label":
            result = svc.print_label(
                str(params.get("file_path") or "").strip(),
                params.get("printer_name"),
                int(params.get("copies") or 1),
            )
            return _j(result, 200)
        if action == "print_document":
            result = svc.print_document(
                str(params.get("file_path") or "").strip(),
                params.get("printer_name"),
                bool(params.get("use_automation", False)),
            )
            return _j(result, 200)
        if action == "test":
            result = svc.test_printer(str(params.get("printer_name") or "").strip())
            return _j(result, 200)
        return _j({"success": True, "message": "标签打印"})

    elif tool_id == "printer_list":
        if action in ("list", "query"):
            from app.services import get_system_service

            return _j(get_system_service().get_printer_config(), 200)
        if action == "set_default":
            from app.services import get_system_service

            return _j(
                get_system_service().set_default_printer(
                    str(params.get("printer_name") or "").strip()
                ),
                200,
            )
        return _j(
            {
                "success": True,
                "redirect": "/console?view=printer-list",
                "message": "已打开打印机列表",
            }
        )

    elif tool_id == "materials":
        from app.application import get_material_application_service

        svc = get_material_application_service()
        if action == "view":
            return _j({"success": True, "redirect": "/console?view=materials"})
        if action in ("list", "query"):
            return (
                _j(
                    svc.get_all_materials(
                        search=str(params.get("search") or params.get("keyword") or "").strip(),
                        category=str(params.get("category") or "").strip() or None,
                        page=int(params.get("page") or 1),
                        per_page=int(params.get("per_page") or 20),
                    )
                ),
                200,
            )
        if action == "create":
            return _j(svc.create_material(dict(params or {})), 200)
        if action == "update":
            material_id = int(params.get("id"))
            payload = {k: v for k, v in params.items() if k != "id"}
            return _j(svc.update_material(material_id, **payload), 200)
        if action == "delete":
            return _j(svc.delete_material(int(params.get("id"))), 200)
        if action == "batch_delete":
            ids = [
                int(x)
                for x in (params.get("ids") or params.get("material_ids") or [])
                if str(x).strip()
            ]
            return _j(svc.batch_delete_materials(ids), 200)
        if action == "export":
            return (
                _j(
                    svc.export_to_excel(
                        search=str(params.get("search") or params.get("keyword") or "").strip()
                        or None,
                        category=str(params.get("category") or "").strip() or None,
                        template_id=params.get("template_id"),
                    )
                ),
                200,
            )
        return _j({"success": True, "message": "原材料仓库"})

    elif tool_id == "ocr":
        if action == "view":
            return _j({"success": True, "redirect": "/console?view=ocr"})
        return _j({"success": True, "message": "图片 OCR"})

    elif tool_id == "wechat":
        from app.application import get_wechat_contact_app_service

        svc = get_wechat_contact_app_service()
        if action == "view":
            return _j({"success": True, "redirect": "/console?view=wechat-contacts"})
        if action in ("list", "query"):
            contacts = svc.get_contacts(
                contact_type=str(params.get("type") or "all"),
                keyword=str(params.get("keyword") or "").strip() or None,
                limit=int(params.get("limit") or 100),
            )
            return _j({"success": True, "data": contacts, "total": len(contacts)}, 200)
        if action in ("refresh_contact_cache", "refresh_messages_cache"):
            from app.services.wechat_contact_cache_import import (
                ensure_decrypted_wechat_dbs as _ensure_decrypted_db,
            )

            return _j(_ensure_decrypted_db(), 200)
        return _j({"success": True, "message": "微信任务"})

    elif tool_id == "excel_decompose":
        if action == "view":
            return _j({"success": True, "redirect": "/console?view=excel"})
        return _j({"success": True, "message": "Excel 模板分解"})

    elif tool_id == "excel_analyzer":
        file_path = params.get("file_path")
        sheet_name = params.get("sheet_name")
        output_json = params.get("output_json")

        if not file_path:
            return _j({"success": False, "message": "缺少参数：file_path（Excel文件路径）"}, 400)
        try:
            from app.infrastructure.skills.excel_analyzer.excel_template_analyzer import (
                ExcelAnalyzerSkill,
                get_excel_analyzer_skill,
            )

            skill = get_excel_analyzer_skill()
            result = skill.execute(
                file_path=file_path, sheet_name=sheet_name, output_json=output_json
            )
            return _j(result)
        except ImportError:
            return _j(
                {"success": False, "message": "Excel分析技能未正确安装，请检查openpyxl库"}, 500
            )
        except Exception as e:
            logger.error(f"Excel Analyzer执行失败: {e}")
            return _j({"success": False, "message": f"分析失败: {str(e)}"}, 500)
    elif tool_id == "template_extract":
        if action in (None, "", "view"):
            return _j(
                {
                    "success": True,
                    "redirect": "/console?view=business-docking",
                    "message": "请先上传 Excel 并提取模板",
                },
                200,
            )
        file_path = str(params.get("file_path") or "").strip()
        sheet_name = str(params.get("sheet_name") or "").strip() or None

        if not file_path:
            return _j({"success": False, "message": "缺少参数：file_path（Excel文件路径）"}, 400)
        try:
            import os

            from app.services.document_templates_service import (
                _extract_excel_grid_preview,
                _extract_structured_excel_preview,
                _list_excel_sheet_names,
            )

            if not os.path.exists(file_path):
                return _j({"success": False, "message": f"文件不存在：{file_path}"}, 404)
            sheet_names = _list_excel_sheet_names(file_path)
            structured = _extract_structured_excel_preview(
                file_path, sheet_name=sheet_name, sample_limit=8
            )
            grid_preview = _extract_excel_grid_preview(
                file_path, sheet_name=sheet_name, max_rows=24, max_cols=14
            )
            selected_sheet_name = (
                structured.get("sheet_name")
                or grid_preview.get("sheet_name")
                or sheet_name
                or (sheet_names[0] if sheet_names else "")
            )
            template_name = os.path.splitext(os.path.basename(file_path))[0]

            return _j(
                {
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
                    },
                },
                200,
            )
        except Exception as e:
            logger.error(f"template_extract 执行失败: {e}", exc_info=True)
            return _j({"success": False, "message": f"提取失败: {str(e)}"}, 500)
    elif tool_id == "excel_toolkit":
        file_path = params.get("file_path")
        sheet_name = params.get("sheet_name")
        toolkit_action = params.get("action", "view")

        if not file_path:
            return _j({"success": False, "message": "缺少参数：file_path（Excel文件路径）"}, 400)
        try:
            from app.infrastructure.skills.excel_toolkit.excel_toolkit import (
                ExcelToolkitSkill,
                get_excel_toolkit_skill,
            )

            skill = get_excel_toolkit_skill()
            result = skill.execute(
                file_path=file_path, action=toolkit_action, sheet_name=sheet_name
            )
            return _j(result)
        except ImportError:
            return _j(
                {"success": False, "message": "Excel工具技能未正确安装，请检查openpyxl库"}, 500
            )
        except Exception as e:
            logger.error(f"Excel Toolkit执行失败: {e}")
            return _j({"success": False, "message": f"执行失败: {str(e)}"}, 500)
    elif tool_id == "shipment_template":
        if action == "view":
            return _j({"success": True, "redirect": "/console?view=template-preview"})
        return _j({"success": True, "message": "发货单模板"})

    elif tool_id == "template_preview":
        if action in ("list", "query"):
            from app.application import get_template_app_service

            result = get_template_app_service().get_templates()
            if isinstance(result, dict):
                return _j(result, 200)
            return _j({"success": True, "data": result}, 200)
        return _j(
            {
                "success": True,
                "redirect": "/console?view=template-preview",
                "message": "已打开模板预览",
            }
        )

    elif tool_id == "settings":
        from app.services import get_system_service

        svc = get_system_service()
        if action in ("query", "get_system_info"):
            return _j({"success": True, "data": svc.get_system_info()}, 200)
        if action == "get_startup_config":
            return _j({"success": True, "data": svc.get_startup_config()}, 200)
        if action == "enable_startup":
            return _j(svc.enable_startup(), 200)
        if action == "disable_startup":
            return _j(svc.disable_startup(), 200)
        return _j(
            {"success": True, "redirect": "/console?view=settings", "message": "已打开系统设置"}
        )

    elif tool_id == "tools_table":
        if action in ("list", "query"):
            from app.services.tools_execution_service import get_workflow_tool_registry

            return _j(
                {"success": True, "tool_ids": list(get_workflow_tool_registry().keys())},
                200,
            )
        return _j({"success": True, "redirect": "/console?view=tools", "message": "已打开工具表"})

    elif tool_id == "other_tools":
        if action in ("list", "query"):
            return _j(
                {
                    "success": True,
                    "tools": [
                        "database",
                        "ocr",
                        "excel_toolkit",
                        "excel_analyzer",
                        "template_extract",
                    ],
                },
                200,
            )
        return _j(
            {"success": True, "redirect": "/console?view=other-tools", "message": "已打开其他工具"}
        )

    elif tool_id == "database":
        from app.services import get_database_service

        db_service = get_database_service()

        # 兼容测试：仅传 tool_id 时也视为可用（返回 200 success true）
        if action in (None, "", "view"):
            return _j({"success": True, "message": "数据库管理"}, 200)

        if action == "backup":
            result = db_service.backup_database()
            return _j(result)

        elif action == "restore":
            backup_file = params.get("backup_file")
            if not backup_file:
                return _j({"success": False, "message": "缺少参数：backup_file"}, 400)
            result = db_service.restore_database(backup_file)
            return _j(result)

        elif action == "list":
            result = db_service.list_backups()
            return _j(result)

        elif action == "delete":
            backup_file = params.get("backup_file")
            if not backup_file:
                return _j({"success": False, "message": "缺少参数：backup_file"}, 400)
            result = db_service.delete_backup(backup_file)
            return _j(result)

        else:
            return _j({"success": False, "message": f"未知的数据库操作：{action}"}, 400)
    elif tool_id == "system":
        from app.services import get_system_service

        system_service = get_system_service()

        # 兼容测试：仅传 tool_id 时也视为可用（返回 200 success true）
        if action in (None, "", "view"):
            return _j({"success": True, "message": "系统设置"}, 200)

        if action == "get_startup_config":
            result = system_service.get_startup_config()
            return _j({"success": True, "data": result})

        elif action == "enable_startup":
            result = system_service.enable_startup()
            return _j(result)

        elif action == "disable_startup":
            result = system_service.disable_startup()
            return _j(result)

        elif action == "get_system_info":
            result = system_service.get_system_info()
            return _j({"success": True, "data": result})

        elif action == "get_printer_config":
            result = system_service.get_printer_config()
            return _j(result)

        elif action == "set_default_printer":
            printer_name = params.get("printer_name")
            if not printer_name:
                return _j({"success": False, "message": "缺少参数：printer_name"}, 400)
            result = system_service.set_default_printer(printer_name)
            return _j(result)

        else:
            return _j({"success": False, "message": f"未知的系统操作：{action}"}, 400)
    elif tool_id == "upload_file":
        # upload_file 是“让用户上传文件”的 UI 引导工具。
        # 该接口本身不执行解析/入库，仅返回前端可触发上传浮层的提示文案。
        msg = "请上传文件以继续（Excel / 图片 / CSV 均可）。"
        return _j({"success": True, "message": msg}, 200)

    return _j({"success": False, "message": f"未知工具: {tool_id}"}, 400)
