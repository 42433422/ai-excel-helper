from __future__ import annotations

import json
import logging

from app.http.json_response import json_response
from app.services.document_templates.renderer import (
    _parse_json_dict,
    _parse_json_list,
)
from app.services.document_templates.variables import (
    _infer_business_scope,
    _validate_required_terms,
)

logger = logging.getLogger(__name__)


def _j(data: dict, status: int = 200):
    return json_response(data, status)


def _normalize_db_template_id(raw_id):
    value = str(raw_id or "").strip()
    if not value:
        return None
    if value.startswith("db:"):
        value = value.split(":", 1)[1].strip()
    if value.isdigit():
        return int(value)
    return None


def _ensure_template_tables_ready():
    try:
        from app.db.init_db import init_template_tables

        init_template_tables()
    except Exception as e:
        logger.warning(f"确保模板表结构失败: {e}")


def _build_template_payload_from_row(row):
    analyzed_data = _parse_json_dict(getattr(row, "analyzed_data", None))
    business_rules = _parse_json_dict(getattr(row, "business_rules", None))
    business_scope = str(
        business_rules.get("business_scope")
        or analyzed_data.get("business_scope")
        or _infer_business_scope(getattr(row, "template_type", ""))
        or ""
    ).strip()
    fields = analyzed_data.get("fields")
    if not isinstance(fields, list):
        fields = _parse_json_list(getattr(row, "editable_config", None))
    preview_data = analyzed_data.get("preview_data")
    if not isinstance(preview_data, dict):
        preview_data = {}
    category = str(analyzed_data.get("category") or "").strip().lower()
    if category not in ("excel", "word"):
        category = "excel"
    return {
        "id": f"db:{row.id}",
        "db_id": row.id,
        "name": getattr(row, "template_name", "") or "",
        "template_type": getattr(row, "template_type", "") or "",
        "business_scope": business_scope,
        "category": category,
        "source": business_rules.get("source") or analyzed_data.get("source") or "db",
        "file_path": getattr(row, "original_file_path", None),
        "fields": fields if isinstance(fields, list) else [],
        "preview_data": preview_data,
    }


def create_template_with_payload(payload: dict | None):
    return _create_template_with_payload_inner(payload or {})


def _create_template_with_payload_inner(payload: dict):
    try:
        import uuid
        from datetime import datetime

        from sqlalchemy import text

        from app.db.session import get_db

        _ensure_template_tables_ready()
        template_name = str(payload.get("name") or payload.get("template_name") or "").strip()
        if not template_name:
            return _j({"success": False, "message": "模板名称不能为空"}, 400)
        template_type = str(payload.get("template_type") or "Excel").strip()
        business_scope = str(
            payload.get("business_scope") or _infer_business_scope(template_type) or ""
        ).strip()
        fields = payload.get("fields") if isinstance(payload.get("fields"), list) else []
        preview_data = (
            payload.get("preview_data") if isinstance(payload.get("preview_data"), dict) else {}
        )
        source = str(payload.get("source") or "generated").strip() or "generated"
        file_path = (
            str(payload.get("file_path") or payload.get("original_file_path") or "").strip() or None
        )
        if business_scope:
            valid, missing_terms = _validate_required_terms({}, fields, business_scope)
            if not valid:
                return _j(
                    {
                        "success": False,
                        "message": "必填字段未匹配，不能保存模板",
                        "business_scope": business_scope,
                        "missing_terms": missing_terms,
                    },
                    400,
                )
        incoming_category = str(payload.get("category") or "").strip().lower()
        if incoming_category not in ("excel", "word"):
            incoming_category = "excel"
        analyzed_data = {
            "category": incoming_category,
            "source": source,
            "business_scope": business_scope,
            "fields": fields,
            "preview_data": preview_data,
        }
        editable_config = fields
        business_rules = {
            "business_scope": business_scope,
            "source": source,
            "selected_sheet_name": preview_data.get("selected_sheet_name")
            or preview_data.get("sheet_name")
            or "",
        }

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
            try:
                db.execute(
                    text(
                        """
                        INSERT INTO template_usage_log (template_id, action, result)
                        VALUES (:template_id, 'create', :result)
                    """
                    ),
                    {"template_id": template_id, "result": f"创建模板：{template_name}"},
                )
                db.commit()
            except Exception as e:
                logger.warning(f"记录模板创建日志失败: {e}")

        return _j(
            {
                "success": True,
                "message": "模板创建成功",
                "template": {
                    "id": f"db:{template_id}",
                    "db_id": template_id,
                    "name": template_name,
                    "template_type": template_type,
                    "business_scope": business_scope,
                    "category": incoming_category,
                    "source": source,
                    "file_path": file_path,
                    "fields": fields,
                    "preview_data": preview_data,
                },
            }
        )
    except Exception as e:
        return _j({"success": False, "message": f"创建失败：{str(e)}"}, 500)


def update_template_with_payload(payload: dict | None):
    return _update_template_with_payload_inner(payload or {})


def _update_template_with_payload_inner(payload: dict):
    try:
        from datetime import datetime

        from sqlalchemy import text

        from app.db.session import get_db

        _ensure_template_tables_ready()
        db_id = _normalize_db_template_id(payload.get("id"))
        if db_id is None:
            return _j({"success": False, "message": "模板 id 无效"}, 400)
        with get_db() as db:
            row = db.execute(
                text(
                    """
                    SELECT id, template_name, template_type, original_file_path,
                           analyzed_data, editable_config, business_rules
                    FROM templates
                    WHERE id = :id
                """
                ),
                {"id": db_id},
            ).fetchone()
            if not row:
                return _j({"success": False, "message": "模板不存在"}, 404)
            existing_analyzed_data = _parse_json_dict(getattr(row, "analyzed_data", None))
            existing_business_rules = _parse_json_dict(getattr(row, "business_rules", None))
            existing_scope = str(
                existing_business_rules.get("business_scope")
                or existing_analyzed_data.get("business_scope")
                or _infer_business_scope(getattr(row, "template_type", ""))
                or ""
            ).strip()

            incoming_template_type = str(
                payload.get("template_type") or getattr(row, "template_type", "") or ""
            ).strip()
            incoming_scope = str(
                payload.get("business_scope")
                or existing_scope
                or _infer_business_scope(incoming_template_type)
                or ""
            ).strip()
            enforce_scope_match = bool(
                payload.get("enforce_scope_match") or payload.get("replace_mode")
            )
            if (
                enforce_scope_match
                and existing_scope
                and incoming_scope
                and existing_scope != incoming_scope
            ):
                return _j(
                    {
                        "success": False,
                        "message": f"仅允许替换同业务范围模板：当前为 {existing_scope}，目标为 {incoming_scope}",
                    },
                    400,
                )
            updates = []
            params = {"id": db_id, "updated_at": datetime.now()}

            new_name = str(payload.get("name") or payload.get("template_name") or "").strip()
            if new_name:
                updates.append("template_name = :template_name")
                params["template_name"] = new_name

            if incoming_template_type:
                updates.append("template_type = :template_type")
                params["template_type"] = incoming_template_type

            file_path = str(
                payload.get("file_path") or payload.get("original_file_path") or ""
            ).strip()
            if file_path:
                updates.append("original_file_path = :original_file_path")
                params["original_file_path"] = file_path

            incoming_fields = payload.get("fields")
            incoming_preview_data = payload.get("preview_data")
            source = str(
                payload.get("source")
                or existing_business_rules.get("source")
                or existing_analyzed_data.get("source")
                or "db"
            ).strip()
            fields_for_validation = (
                incoming_fields
                if isinstance(incoming_fields, list)
                else (
                    existing_analyzed_data.get("fields")
                    if isinstance(existing_analyzed_data.get("fields"), list)
                    else []
                )
            )
            if incoming_scope:
                valid, missing_terms = _validate_required_terms(
                    {}, fields_for_validation, incoming_scope
                )
                if not valid:
                    return _j(
                        {
                            "success": False,
                            "message": "必填字段未匹配，不能替换模板",
                            "business_scope": incoming_scope,
                            "missing_terms": missing_terms,
                        },
                        400,
                    )
            new_analyzed_data = {
                **existing_analyzed_data,
                "source": source,
                "business_scope": incoming_scope,
            }
            incoming_category = str(payload.get("category") or "").strip().lower()
            if incoming_category in ("excel", "word"):
                new_analyzed_data["category"] = incoming_category
            if isinstance(incoming_fields, list):
                new_analyzed_data["fields"] = incoming_fields
                updates.append("editable_config = :editable_config")
                params["editable_config"] = json.dumps(incoming_fields, ensure_ascii=False)
            if isinstance(incoming_preview_data, dict):
                merged_preview = {
                    **(
                        existing_analyzed_data.get("preview_data")
                        if isinstance(existing_analyzed_data.get("preview_data"), dict)
                        else {}
                    ),
                    **incoming_preview_data,
                }
                new_analyzed_data["preview_data"] = merged_preview

            updates.append("analyzed_data = :analyzed_data")
            params["analyzed_data"] = json.dumps(new_analyzed_data, ensure_ascii=False)

            new_business_rules = {
                **existing_business_rules,
                "business_scope": incoming_scope,
                "source": source,
            }
            if isinstance(incoming_preview_data, dict):
                selected_sheet_name = incoming_preview_data.get(
                    "selected_sheet_name"
                ) or incoming_preview_data.get("sheet_name")
                if selected_sheet_name:
                    new_business_rules["selected_sheet_name"] = selected_sheet_name
            updates.append("business_rules = :business_rules")
            params["business_rules"] = json.dumps(new_business_rules, ensure_ascii=False)

            updates.append("updated_at = :updated_at")

            allowed_fields = {
                "template_name",
                "template_type",
                "original_file_path",
                "editable_config",
                "analyzed_data",
                "business_rules",
                "updated_at",
            }
            for update_clause in updates:
                field_name = update_clause.split("=")[0].strip()
                if field_name not in allowed_fields:
                    return _j({"success": False, "message": f"无效的更新字段: {field_name}"}, 400)
            db.execute(text(f"UPDATE templates SET {', '.join(updates)} WHERE id = :id"), params)
            db.commit()

            try:
                db.execute(
                    text(
                        """
                        INSERT INTO template_usage_log (template_id, action, result)
                        VALUES (:template_id, 'update', :result)
                    """
                    ),
                    {"template_id": db_id, "result": "更新模板配置"},
                )
                db.commit()
            except Exception as e:
                logger.warning(f"记录模板更新日志失败: {e}")

            refreshed = db.execute(
                text(
                    """
                    SELECT id, template_name, template_type, original_file_path,
                           analyzed_data, business_rules
                    FROM templates
                    WHERE id = :id
                """
                ),
                {"id": db_id},
            ).fetchone()

        return _j(
            {
                "success": True,
                "message": "模板更新成功",
                "template": _build_template_payload_from_row(refreshed),
            }
        )
    except Exception as e:
        return _j({"success": False, "message": f"更新失败：{str(e)}"}, 500)
