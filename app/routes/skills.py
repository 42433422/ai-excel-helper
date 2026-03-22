# -*- coding: utf-8 -*-
"""
Skills 路由模块

提供技能列表、分类和执行 API
"""

import logging

from flasgger import swag_from
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)
skills_bp = Blueprint('skills', __name__, url_prefix="/api/skills")


@skills_bp.route('/list', methods=['GET'])
@swag_from({
    'summary': '获取技能列表',
    'description': '获取所有已注册技能的列表',
    'responses': {
        '200': {
            'description': '成功响应',
            'schema': {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'skills': {'type': 'array'}
                }
            }
        }
    }
})
def list_skills():
    """获取所有已注册的技能列表"""
    try:
        from app.infrastructure.skills import get_skill_registry
        registry = get_skill_registry()
        skills = registry.list_all()
        return jsonify({"success": True, "skills": skills})
    except Exception as e:
        logger.error(f"获取技能列表失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@skills_bp.route('/info/<skill_id>', methods=['GET'])
@swag_from({
    'summary': '获取技能详情',
    'description': '获取指定技能的详细信息',
    'parameters': [
        {
            'name': 'skill_id',
            'in': 'path',
            'type': 'string',
            'required': True,
            'description': '技能ID'
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应'
        }
    }
})
def get_skill_info(skill_id):
    """获取指定技能的详细信息"""
    try:
        from app.infrastructure.skills import get_skill_registry
        registry = get_skill_registry()
        skill_info = registry.get(skill_id)
        if skill_info:
            return jsonify({
                "success": True,
                "skill": {
                    "id": skill_id,
                    "name": skill_info.get("name", ""),
                    "description": skill_info.get("description", ""),
                    "keywords": skill_info.get("keywords", []),
                    "category": skill_info.get("category", "general")
                }
            })
        else:
            return jsonify({"success": False, "message": f"未找到技能: {skill_id}"}), 404
    except Exception as e:
        logger.error(f"获取技能信息失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@skills_bp.route('/execute', methods=['POST'])
@swag_from({
    'summary': '执行技能',
    'description': '执行指定的技能',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'skill_id': {'type': 'string', 'description': '技能ID'},
                    'file_path': {'type': 'string', 'description': '文件路径'},
                    'action': {'type': 'string', 'description': '操作类型'},
                    'sheet_name': {'type': 'string', 'description': 'Sheet名称'}
                },
                'required': ['skill_id']
            }
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应'
        }
    }
})
def execute_skill():
    """执行指定的技能"""
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "message": "请求数据不能为空"}), 400

        skill_id = data.get('skill_id')
        if not skill_id:
            return jsonify({"success": False, "message": "缺少参数: skill_id"}), 400

        from app.infrastructure.skills import execute_skill

        params = {
            "file_path": data.get('file_path'),
            "action": data.get('action'),
            "sheet_name": data.get('sheet_name'),
            "output_json": data.get('output_json')
        }
        params = {k: v for k, v in params.items() if v is not None}

        result = execute_skill(skill_id, **params)
        return jsonify(result)
    except Exception as e:
        logger.error(f"执行技能失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@skills_bp.route('/analyze/excel', methods=['POST'])
@swag_from({
    'summary': '分析Excel模板',
    'description': '深度分析Excel模板结构，识别可编辑区域、表头、数据区等',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'file_path': {'type': 'string', 'description': 'Excel文件路径'},
                    'sheet_name': {'type': 'string', 'description': 'Sheet名称（可选）'}
                },
                'required': ['file_path']
            }
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应'
        }
    }
})
def analyze_excel():
    """分析Excel模板"""
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "message": "请求数据不能为空"}), 400

        file_path = data.get('file_path')
        if not file_path:
            return jsonify({"success": False, "message": "缺少参数: file_path"}), 400

        from app.infrastructure.skills.excel_analyzer.excel_template_analyzer import (
            get_excel_analyzer_skill,
        )
        skill = get_excel_analyzer_skill()
        result = skill.execute(file_path=file_path, sheet_name=data.get('sheet_name'))
        return jsonify(result)
    except Exception as e:
        logger.error(f"分析Excel失败: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@skills_bp.route('/view/excel', methods=['POST'])
@swag_from({
    'summary': '查看 Excel 内容',
    'description': '查看 Excel 文件内容、合并单元格、样式等信息',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'file_path': {'type': 'string', 'description': 'Excel 文件路径'},
                    'action': {'type': 'string', 'description': '操作类型：view/merged/styles/structure'},
                    'sheet_name': {'type': 'string', 'description': 'Sheet 名称（可选）'}
                },
                'required': ['file_path']
            }
        }
    ],
    'responses': {
        '200': {
            'description': '成功响应'
        }
    }
})
def view_excel():
    """查看 Excel 内容"""
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "message": "请求数据不能为空"}), 400

        file_path = data.get('file_path')
        if not file_path:
            return jsonify({"success": False, "message": "缺少参数：file_path"}), 400

        from app.infrastructure.skills.excel_toolkit.excel_toolkit import get_excel_toolkit_skill
        skill = get_excel_toolkit_skill()
        result = skill.execute(
            file_path=file_path,
            action=data.get('action', 'view'),
            sheet_name=data.get('sheet_name')
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"查看 Excel 失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500


@skills_bp.route('/generate-label-template', methods=['POST'])
@swag_from({
    'summary': '从图片生成标签模板',
    'description': '上传标签图片，自动生成对应的 Python 标签模板代码',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'image_path': {'type': 'string', 'description': '图片文件路径'},
                    'class_name': {'type': 'string', 'description': '生成的类名', 'default': 'LabelTemplateGenerator'},
                    'enable_ocr': {'type': 'boolean', 'description': '是否启用 OCR 识别', 'default': True}
                },
                'required': ['image_path']
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
                    'code': {'type': 'string', 'description': '生成的 Python 代码'},
                    'fields': {'type': 'array', 'description': '识别到的字段列表'}
                }
            }
        }
    }
})
def generate_label_template():
    """从图片生成标签模板代码"""
    try:
        data = request.json
        if not data:
            return jsonify({"success": False, "message": "请求数据不能为空"}), 400

        image_path = data.get('image_path')
        if not image_path:
            return jsonify({"success": False, "message": "缺少参数：image_path"}), 400

        class_name = data.get('class_name', 'LabelTemplateGenerator')
        enable_ocr = data.get('enable_ocr', True)

        from app.infrastructure.skills.label_template_generator import (
            get_label_template_generator_skill,
        )
        skill = get_label_template_generator_skill()
        result = skill.execute(
            image_path=image_path,
            class_name=class_name,
            enable_ocr=enable_ocr,
            verbose=True
        )

        return jsonify(result)
    except Exception as e:
        logger.error(f"生成标签模板失败：{e}")
        return jsonify({"success": False, "message": str(e)}), 500