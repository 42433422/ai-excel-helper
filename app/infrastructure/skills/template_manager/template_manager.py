# -*- coding: utf-8 -*-
"""
Template Manager Skill Module
"""

import os
from typing import Any, Dict, List, Optional


def get_base_dir():
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))


def get_template_app_service():
    from app.bootstrap import get_template_app_service
    return get_template_app_service()


def list_all_templates() -> List[Dict]:
    svc = get_template_app_service()
    return svc.list_templates()


def list_templates_by_type(template_type: str, active_only: bool = True) -> List[Dict]:
    svc = get_template_app_service()
    return svc.list_by_type(template_type, active_only)


def get_template_file_path(template_id: str) -> Optional[str]:
    svc = get_template_app_service()
    return svc.resolve_template_file(template_id)


def get_default_template(template_type: str = "发货单") -> Optional[Dict]:
    svc = get_template_app_service()
    return svc.get_default_for_type(template_type)


def decompose_template_file(file_path: str, sheet_name: str = None, sample_rows: int = 5) -> Dict[str, Any]:
    from app.routes.excel_templates import _decompose_template
    result, status = _decompose_template(file_path, sheet_name, sample_rows)
    return result


def resolve_template_path(filename: str) -> Optional[str]:
    from app.routes.excel_templates import _resolve_template_path
    return _resolve_template_path(filename)


def save_template_file(source_name: str, target_name: str, overwrite: bool = False) -> Dict:
    svc = get_template_app_service()
    return svc.save_template_file(source_name, target_name, overwrite)


def get_template_info(template_id: int) -> Optional[Dict]:
    import json

    from sqlalchemy import text

    from app.db.session import get_db

    with get_db() as db:
        result = db.execute(
            text("SELECT * FROM templates WHERE id = :id AND is_active = 1"),
            {'id': template_id}
        )
        row = result.fetchone()

        if not row:
            return None

        return {
            'id': row.id,
            'template_key': row.template_key,
            'template_name': row.template_name,
            'template_type': row.template_type,
            'original_file_path': row.original_file_path,
            'analyzed_data': json.loads(row.analyzed_data) if row.analyzed_data else None,
            'editable_config': json.loads(row.editable_config) if row.editable_config else None,
            'zone_config': json.loads(row.zone_config) if row.zone_config else None,
            'merged_cells_config': json.loads(row.merged_cells_config) if row.merged_cells_config else None,
            'style_config': json.loads(row.style_config) if row.style_config else None,
            'business_rules': json.loads(row.business_rules) if row.business_rules else None,
            'created_at': str(row.created_at) if row.created_at else None,
            'updated_at': str(row.updated_at) if row.updated_at else None
        }


def create_template(template_name: str, template_type: str = "通用", **kwargs) -> Dict:
    import json
    import uuid
    from datetime import datetime

    from sqlalchemy import text

    from app.db.session import get_db

    template_key = f"TPL_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8].upper()}"

    with get_db() as db:
        result = db.execute(
            text("""
                INSERT INTO templates (
                    template_key, template_name, template_type,
                    original_file_path, analyzed_data, editable_config,
                    zone_config, merged_cells_config, style_config,
                    business_rules
                ) VALUES (
                    :template_key, :template_name, :template_type,
                    :original_file_path, :analyzed_data, :editable_config,
                    :zone_config, :merged_cells_config, :style_config,
                    :business_rules
                )
            """),
            {
                'template_key': template_key,
                'template_name': template_name,
                'template_type': template_type,
                'original_file_path': kwargs.get('original_file_path'),
                'analyzed_data': json.dumps(kwargs.get('analyzed_data', {}), ensure_ascii=False),
                'editable_config': json.dumps(kwargs.get('editable_config', {}), ensure_ascii=False),
                'zone_config': json.dumps(kwargs.get('zone_config', {}), ensure_ascii=False),
                'merged_cells_config': json.dumps(kwargs.get('merged_cells_config', {}), ensure_ascii=False),
                'style_config': json.dumps(kwargs.get('style_config', {}), ensure_ascii=False),
                'business_rules': json.dumps(kwargs.get('business_rules', {}), ensure_ascii=False)
            }
        )
        template_id = result.lastrowid
        db.commit()

        db.execute(
            text("""
                INSERT INTO template_usage_log (template_id, action, result)
                VALUES (:template_id, 'create', :result)
            """),
            {'template_id': template_id, 'result': f'创建模板：{template_name}'}
        )
        db.commit()

        return {
            'success': True,
            'template_id': template_id,
            'template_key': template_key,
            'message': '模板创建成功'
        }


def update_template(template_id: int, **updates) -> Dict:
    import json
    from datetime import datetime

    from sqlalchemy import text

    from app.db.session import get_db

    with get_db() as db:
        result = db.execute(
            text("SELECT id FROM templates WHERE id = :id"),
            {'id': template_id}
        )
        if not result.fetchone():
            return {'success': False, 'message': '模板不存在'}

        db_updates = []
        params = {'id': template_id}

        for key, value in updates.items():
            if value is not None:
                db_updates.append(f'{key} = :{key}')
                params[key] = json.dumps(value) if isinstance(value, dict) else value

        if db_updates:
            db_updates.append('updated_at = :updated_at')
            params['updated_at'] = datetime.now()

            sql = f"UPDATE templates SET {', '.join(db_updates)} WHERE id = :id"
            db.execute(text(sql), params)
            db.commit()

        db.execute(
            text("""
                INSERT INTO template_usage_log (template_id, action, result)
                VALUES (:template_id, 'update', :result)
            """),
            {'template_id': template_id, 'result': '更新模板配置'}
        )
        db.commit()

        return {'success': True, 'message': '模板更新成功'}


def delete_template(template_id: int) -> Dict:
    from datetime import datetime

    from sqlalchemy import text

    from app.db.session import get_db

    with get_db() as db:
        result = db.execute(
            text("SELECT id FROM templates WHERE id = :id"),
            {'id': template_id}
        )
        if not result.fetchone():
            return {'success': False, 'message': '模板不存在'}

        db.execute(
            text("UPDATE templates SET is_active = 0, updated_at = :updated_at WHERE id = :id"),
            {'id': template_id, 'updated_at': datetime.now()}
        )

        db.execute(
            text("""
                INSERT INTO template_usage_log (template_id, action, result)
                VALUES (:template_id, 'delete', :result)
            """),
            {'template_id': template_id, 'result': '删除模板'}
        )
        db.commit()

        return {'success': True, 'message': '模板删除成功'}


def list_shipment_templates(active_only: bool = True) -> List[Dict]:
    return list_templates_by_type("发货单", active_only)


def list_shipment_record_templates(active_only: bool = True) -> List[Dict]:
    return list_templates_by_type("出货记录", active_only)


def list_product_templates(active_only: bool = True) -> List[Dict]:
    return list_templates_by_type("产品列表", active_only)


def list_purchase_unit_templates(active_only: bool = True) -> List[Dict]:
    return list_templates_by_type("购买单位列表", active_only)


def list_label_templates(active_only: bool = True) -> List[Dict]:
    return list_templates_by_type("标签", active_only)


def export_products_with_template(unit_name: str = None, keyword: str = None) -> Dict:
    from app.bootstrap import get_products_service
    service = get_products_service()
    return service.export_to_excel(unit_name=unit_name, keyword=keyword)


def list_physical_template_files() -> List[Dict]:
    base_dir = get_base_dir()
    template_dir = os.path.join(base_dir, "templates")
    temp_dir = os.path.join(base_dir, "temp_excel")

    results = []

    for directory, dir_name in [(template_dir, "templates"), (temp_dir, "temp_excel")]:
        if os.path.exists(directory):
            for filename in os.listdir(directory):
                if filename.lower().endswith(('.xlsx', '.xls')):
                    full_path = os.path.join(directory, filename)
                    file_size = os.path.getsize(full_path)
                    results.append({
                        'filename': filename,
                        'full_path': full_path,
                        'directory': dir_name,
                        'size_bytes': file_size,
                        'exists': True
                    })

    return results


def get_template_file(filename: str) -> Optional[Dict]:
    base_dir = get_base_dir()
    template_dir = os.path.join(base_dir, "templates")
    temp_dir = os.path.join(base_dir, "temp_excel")

    for directory in [template_dir, temp_dir]:
        if os.path.exists(directory):
            full_path = os.path.join(directory, filename)
            if os.path.exists(full_path):
                return {
                    'filename': filename,
                    'full_path': full_path,
                    'directory': os.path.basename(directory),
                    'size_bytes': os.path.getsize(full_path),
                    'exists': True
                }

    return None


def get_template_manager_skill():
    return {
        'name': 'template-manager',
        'functions': {
            'list_all_templates': list_all_templates,
            'list_templates_by_type': list_templates_by_type,
            'list_shipment_templates': list_shipment_templates,
            'list_shipment_record_templates': list_shipment_record_templates,
            'list_product_templates': list_product_templates,
            'list_purchase_unit_templates': list_purchase_unit_templates,
            'list_label_templates': list_label_templates,
            'get_template_file_path': get_template_file_path,
            'get_default_template': get_default_template,
            'decompose_template_file': decompose_template_file,
            'resolve_template_path': resolve_template_path,
            'save_template_file': save_template_file,
            'get_template_info': get_template_info,
            'create_template': create_template,
            'update_template': update_template,
            'delete_template': delete_template,
            'export_products_with_template': export_products_with_template,
        }
    }