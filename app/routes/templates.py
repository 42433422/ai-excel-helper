# -*- coding: utf-8 -*-
"""
通用模板 API 路由
提供 /api/templates/* 路径的 API 端点
"""

from flask import Blueprint, jsonify, request
from flask_cors import CORS
import os
import threading

templates_bp = Blueprint('templates', __name__, url_prefix='/api/templates')
CORS(templates_bp)

# 全局进度跟踪字典
analysis_progress = {}
progress_lock = threading.Lock()


@templates_bp.route('/progress/<task_id>', methods=['GET'])
def get_analysis_progress(task_id):
    """获取分析任务进度"""
    with progress_lock:
        progress = analysis_progress.get(task_id, {})
    
    return jsonify({
        "success": True,
        "task_id": task_id,
        "progress": progress.get('percent', 0),
        "step": progress.get('step', 1),
        "message": progress.get('message', '准备中...'),
        "completed": progress.get('completed', False)
    })


@templates_bp.route('/list', methods=['GET'])
def list_templates():
    """获取模板列表（兼容前端调用）"""
    try:
        from app.routes.excel_templates import _get_template_list

        templates = _get_template_list()

        return jsonify({
            "success": True,
            "templates": templates
        })
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"获取模板列表失败：{e}")

        return jsonify({
            "success": False,
            "message": str(e),
            "templates": []
        }), 500


@templates_bp.route('/detail/<template_id>', methods=['GET'])
def get_template_detail(template_id):
    """获取模板详情（包括预览数据）"""
    try:
        from app.services.skills.excel_analyzer.excel_template_analyzer import get_excel_analyzer_skill
        from app.services.skills.excel_toolkit.excel_toolkit import view_excel_content
        import logging
        logger = logging.getLogger(__name__)
        
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        shipment_template_path = os.path.join(base_dir, 'templates', '发货单.xlsx')

        if not os.path.exists(shipment_template_path):
            return jsonify({
                "success": False,
                "message": f"发货单模板文件不存在"
            }), 404

        skill = get_excel_analyzer_skill()
        analyze_result = skill.execute(file_path=shipment_template_path, sheet_name='出货')

        if analyze_result.get('success'):
            cells = analyze_result.get('cells', {})
            editable_entries = analyze_result.get('editable_ranges', [])
            
            view_result = view_excel_content(shipment_template_path, sheet_name='出货', max_rows=10)
            sample_rows = []
            if view_result.get('success'):
                for row in view_result.get('content', []):
                    row_data = {}
                    for cell in row.get('cells', []):
                        if cell.get('value') is not None:
                            row_data[cell.get('coordinate', '')] = cell.get('value')
                    if row_data:
                        sample_rows.append(row_data)

            fields = []
            for cell_ref, cell_info in list(cells.items())[:20]:
                if cell_info.get('value') and cell_info.get('purpose') != '系统保留':
                    fields.append({
                        "label": str(cell_info.get('value', '')),
                        "value": '',
                        "type": "dynamic"
                    })

            return jsonify({
                "success": True,
                "template": {
                    "id": template_id,
                    "name": "发货单模板",
                    "category": "excel",
                    "template_type": "发货单",
                    "fields": fields,
                    "preview_data": {
                        "cells": cells,
                        "editable_ranges": editable_entries,
                        "sample_rows": sample_rows
                    }
                }
            })
        else:
            return jsonify({
                "success": False,
                "message": analyze_result.get('error', '获取详情失败')
            }), 500

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"获取模板详情失败：{e}")
        import traceback
        traceback.print_exc()

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500


@templates_bp.route('/analyze', methods=['POST'])
def analyze_template():
    """分析上传的文件，自动识别为 Excel 模板或标签模板"""
    from flask import request
    import os
    import uuid
    import logging
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"收到 analyze 请求，files: {request.files.keys()}")
        logger.info(f"收到 analyze 请求，form: {request.form}")
        
        if 'file' not in request.files:
            logger.error("没有上传文件")
            return jsonify({
                "success": False,
                "message": "没有上传文件"
            }), 400

        file = request.files['file']
        template_name = request.form.get('template_name', '')

        logger.info(f"文件名：{file.filename}, 模板名：{template_name}")

        if file.filename == '':
            logger.error("文件名为空")
            return jsonify({
                "success": False,
                "message": "文件名为空"
            }), 400

        file_ext = os.path.splitext(file.filename)[1].lower()

        upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads', 'templates')
        os.makedirs(upload_dir, exist_ok=True)

        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        file_path = os.path.join(upload_dir, unique_filename)
        file.save(file_path)

        # 生成任务 ID 并初始化进度
        task_id = uuid.uuid4().hex
        with progress_lock:
            analysis_progress[task_id] = {
                'percent': 0,
                'step': 1,
                'message': '准备上传文件...',
                'completed': False
            }

        if file_ext in ['.xlsx', '.xls']:
            return _analyze_excel_template(file_path, template_name, file.filename, task_id)
        elif file_ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp']:
            return _analyze_label_template(file_path, template_name, file.filename, task_id)
        else:
            with progress_lock:
                if task_id in analysis_progress:
                    del analysis_progress[task_id]
            return jsonify({
                "success": False,
                "message": f"不支持的文件类型：{file_ext}"
            }), 400

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"分析模板失败：{e}")
        import traceback
        traceback.print_exc()

        return jsonify({
            "success": False,
            "message": f"分析失败：{str(e)}"
        }), 500


def _analyze_excel_template(file_path: str, template_name: str, original_filename: str, task_id: str):
    """分析 Excel 模板 - 结合 excel_analyzer 和 excel_toolkit 技能"""
    try:
        from app.services.skills.excel_analyzer.excel_template_analyzer import get_excel_analyzer_skill
        from app.services.skills.excel_toolkit.excel_toolkit import view_excel_content

        # 步骤 1: 上传完成 (10%)
        _update_progress(task_id, 10, 1, '文件上传成功')
        
        skill = get_excel_analyzer_skill()
        
        # 步骤 2: 开始分析 Excel (50%)
        _update_progress(task_id, 50, 2, '分析 Excel 结构...')

        analyze_result = skill.execute(file_path=file_path, sheet_name='出货')
        
        # 步骤 3: 完成 (100%)
        _update_progress(task_id, 100, 3, '分析完成！')
        with progress_lock:
            if task_id in analysis_progress:
                analysis_progress[task_id]['completed'] = True

        if analyze_result.get('success'):
            cells = analyze_result.get('cells', {})
            editable_entries = analyze_result.get('editable_ranges', [])
            merged_cells = analyze_result.get('merged_cells', [])
            structure = analyze_result.get('structure', {})

            fields = []
            for cell_ref, cell_info in list(cells.items())[:20]:
                if cell_info.get('value') and cell_info.get('purpose') != '系统保留':
                    fields.append({
                        "label": str(cell_info.get('value', '')),
                        "value": '',
                        "type": "dynamic"
                    })

            view_result = view_excel_content(file_path, sheet_name='出货', max_rows=10)
            sample_rows = []
            if view_result.get('success'):
                for row in view_result.get('content', []):
                    row_data = {}
                    for cell in row.get('cells', []):
                        if cell.get('value') is not None:
                            row_data[cell.get('coordinate', '')] = cell.get('value')
                    if row_data:
                        sample_rows.append(row_data)

            name = template_name if template_name else original_filename.replace('.xlsx', '').replace('.xls', '')

            return jsonify({
                "success": True,
                "task_id": task_id,
                "template_name": name,
                "template_type": "excel",
                "fields": fields,
                "preview_data": {
                    "cells": cells,
                    "editable_ranges": editable_entries,
                    "merged_cells": merged_cells,
                    "sample_rows": sample_rows,
                    "structure": structure,
                    "file_path": file_path
                }
            })
        else:
            return jsonify({
                "success": False,
                "message": analyze_result.get('error', 'Excel 分析失败')
            }), 500

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"分析 Excel 模板失败：{e}")
        import traceback
        traceback.print_exc()

        return jsonify({
            "success": False,
            "message": f"分析 Excel 失败：{str(e)}"
        }), 500


def _update_progress(task_id: str, percent: int, step: int, message: str):
    """更新任务进度"""
    with progress_lock:
        if task_id in analysis_progress:
            analysis_progress[task_id].update({
                'percent': percent,
                'step': step,
                'message': message
            })

def _analyze_label_template(file_path: str, template_name: str, original_filename: str, task_id: str):
    """分析标签模板（图片）- 结合 OCR 和 PIL 生成技能"""
    try:
        from app.services.skills.label_template_generator.label_template_generator import (
            LabelTemplateGeneratorSkill
        )
        import logging
        logger = logging.getLogger(__name__)

        # 步骤 1: 上传完成 (10%)
        _update_progress(task_id, 10, 1, '文件上传成功')
        
        skill = LabelTemplateGeneratorSkill()
        
        # 步骤 2: 开始检测网格 (25%)
        _update_progress(task_id, 25, 2, '检测表格网格...')

        ocr_result = skill.execute(
            image_path=file_path,
            class_name=template_name.replace(' ', '') + 'Generator' if template_name else 'LabelGenerator',
            enable_ocr=True,
            verbose=True
        )
        
        # 步骤 3: OCR 识别完成 (75%)
        _update_progress(task_id, 75, 3, 'OCR 识别文字...')
        
        # 步骤 4: 分析字段 (90%)
        _update_progress(task_id, 90, 4, '分析字段...')

        logger.info(f"OCR 识别结果：{ocr_result}")

        if ocr_result.get('success'):
            fields = []
            
            # 提前获取 ocr_data 以便后续使用 grid 信息
            image_analysis = ocr_result.get('analysis', {})
            ocr_data = ocr_result.get('ocr_result', {})
            
            if ocr_data and ocr_data.get('fields'):
                ocr_fields = ocr_data['fields']
                logger.info(f"OCR 提取到 {len(ocr_fields)} 个字段")
                
                import uuid
                for field in ocr_fields:
                    logger.info(f"字段：{field}")
                    fields.append({
                        "id": uuid.uuid4().hex,
                        "label": field.get('label', ''),
                        "value": field.get('value', ''),
                        "type": 'fixed' if field.get('type') == 'fixed_label' else 'dynamic',
                        "position": field.get('position', {}),
                        "confidence": field.get('confidence', 0)
                    })
            else:
                logger.warning("OCR 未提取到字段，使用默认字段")
                fields = [
                    {"label": "品名", "value": "示例产品", "type": "fixed"},
                    {"label": "货号", "value": "00000", "type": "dynamic"},
                    {"label": "颜色", "value": "黑色", "type": "dynamic"},
                    {"label": "码段", "value": "00000", "type": "dynamic"},
                    {"label": "等级", "value": "合格品", "type": "fixed"},
                    {"label": "执行标准", "value": "QB/Txxxx-xxxx", "type": "fixed"},
                    {"label": "统一零售价", "value": "¥0", "type": "dynamic"}
                ]

            name = template_name if template_name else original_filename.replace('.' + original_filename.split('.')[-1], '')
            
            # 标记任务完成 (100%)
            _update_progress(task_id, 100, 4, '分析完成！')
            with progress_lock:
                if task_id in analysis_progress:
                    analysis_progress[task_id]['completed'] = True

            # 构建 preview_data
            preview_data = {
                "image_path": file_path,
                "image_size": image_analysis.get('size', {}),
                "colors": image_analysis.get('colors', {}),
                "ocr_fields": fields
            }
            
            # 添加网格信息
            if ocr_data and ocr_data.get('grid'):
                preview_data['grid'] = ocr_data['grid']
                logger.info(f"网格信息：{ocr_data['grid']}")
            else:
                logger.warning("未找到网格信息")

            return jsonify({
                "success": True,
                "task_id": task_id,
                "template_name": name,
                "template_type": "label",
                "fields": fields,
                "generated_code": ocr_result.get('code', ''),
                "preview_data": preview_data
            })
        else:
            return jsonify({
                "success": False,
                "message": ocr_result.get('error', '标签生成失败')
            }), 500

    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"分析标签模板失败：{e}")
        import traceback
        traceback.print_exc()

        return jsonify({
            "success": False,
            "message": f"分析标签失败：{str(e)}"
        }), 500
