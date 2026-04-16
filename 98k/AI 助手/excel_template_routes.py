"""
Excel 模板分析和管理 API 路由
提供 Excel 文件分析、模板保存、模板应用等功能
"""

from flask import Blueprint, request, jsonify, send_file
from pathlib import Path
import json
import os
import uuid
from datetime import datetime

# 导入 Excel 分析器
from excel_template_analyzer import ExcelTemplateAnalyzer

# 导入数据库
from db import get_db_connection

templates_bp = Blueprint('excel_templates', __name__)

# 上传目录
UPLOAD_FOLDER = Path(__file__).parent / 'uploads' / 'templates'
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

# 模板生成目录
GENERATED_FOLDER = Path(__file__).parent / 'dist' / 'templates'
GENERATED_FOLDER.mkdir(parents=True, exist_ok=True)


@templates_bp.route('/api/excel/analyze', methods=['POST'])
def analyze_excel():
    """
    分析 Excel 文件
    请求：POST multipart/form-data 包含 file 字段
    返回：分析结果 JSON
    """
    try:
        # 检查文件
        if 'file' not in request.files:
            return jsonify({'error': '未找到上传文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '文件名为空'}), 400
        
        # 检查文件类型
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'error': '只支持 Excel 文件 (.xlsx, .xls)'}), 400
        
        # 保存上传文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = UPLOAD_FOLDER / safe_filename
        file.save(str(file_path))
        
        # 分析 Excel
        analyzer = ExcelTemplateAnalyzer(str(file_path))
        result = analyzer.analyze()
        
        # 添加文件路径信息
        result['uploaded_file_path'] = str(file_path)
        
        # 自动识别模板类型
        template_type = auto_detect_template_type(result)
        result['detected_template_type'] = template_type
        
        # 记录使用日志
        log_template_usage(None, 'analyze', json.dumps(result, ensure_ascii=False))
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': f'分析失败：{str(e)}'}), 500


@templates_bp.route('/api/templates', methods=['GET'])
def list_templates():
    """
    获取模板列表
    支持按类型过滤：?type=送货单
    """
    try:
        template_type = request.args.get('type')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if template_type:
            cursor.execute('''
                SELECT id, template_key, template_name, template_type, 
                       created_at, updated_at
                FROM templates
                WHERE template_type = ? AND is_active = 1
                ORDER BY created_at DESC
            ''', (template_type,))
        else:
            cursor.execute('''
                SELECT id, template_key, template_name, template_type,
                       created_at, updated_at
                FROM templates
                WHERE is_active = 1
                ORDER BY created_at DESC
            ''')
        
        templates = []
        for row in cursor.fetchall():
            templates.append({
                'id': row[0],
                'template_key': row[1],
                'template_name': row[2],
                'template_type': row[3],
                'created_at': row[4],
                'updated_at': row[5]
            })
        
        conn.close()
        return jsonify({'templates': templates})
    
    except Exception as e:
        return jsonify({'error': f'获取模板列表失败：{str(e)}'}), 500


@templates_bp.route('/api/templates/<int:template_id>', methods=['GET'])
def get_template(template_id):
    """
    获取模板详情
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM templates
            WHERE id = ? AND is_active = 1
        ''', (template_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'error': '模板不存在'}), 404
        
        # 构建模板对象
        template = {
            'id': row[0],
            'template_key': row[1],
            'template_name': row[2],
            'template_type': row[3],
            'original_file_path': row[4],
            'created_at': row[12],
            'updated_at': row[13]
        }
        
        # 解析 JSON 字段
        if row[5]:  # analyzed_data
            template['analyzed_data'] = json.loads(row[5])
        if row[6]:  # editable_config
            template['editable_config'] = json.loads(row[6])
        if row[7]:  # zone_config
            template['zone_config'] = json.loads(row[7])
        if row[8]:  # merged_cells_config
            template['merged_cells_config'] = json.loads(row[8])
        if row[9]:  # style_config
            template['style_config'] = json.loads(row[9])
        if row[10]:  # business_rules
            template['business_rules'] = json.loads(row[10])
        
        return jsonify(template)
    
    except Exception as e:
        return jsonify({'error': f'获取模板详情失败：{str(e)}'}), 500


@templates_bp.route('/api/templates', methods=['POST'])
def save_template():
    """
    保存模板配置
    请求 JSON:
    {
        "template_name": "模板名称",
        "template_type": "送货单",
        "uploaded_file_path": "上传的文件路径",
        "analyzed_data": {...},
        "editable_config": {...},
        "zone_config": {...},
        "merged_cells_config": {...},
        "style_config": {...},
        "business_rules": {...}
    }
    """
    try:
        data = request.json
        
        # 验证必填字段
        required = ['template_name', 'uploaded_file_path', 'analyzed_data']
        for field in required:
            if field not in data:
                return jsonify({'error': f'缺少必填字段：{field}'}), 400
        
        # 生成模板 key
        template_key = f"TPL_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8].upper()}"
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO templates (
                template_key, template_name, template_type,
                original_file_path, analyzed_data, editable_config,
                zone_config, merged_cells_config, style_config,
                business_rules
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            template_key,
            data['template_name'],
            data.get('template_type', '通用'),
            data['uploaded_file_path'],
            json.dumps(data['analyzed_data'], ensure_ascii=False),
            json.dumps(data.get('editable_config', {}), ensure_ascii=False),
            json.dumps(data.get('zone_config', {}), ensure_ascii=False),
            json.dumps(data.get('merged_cells_config', {}), ensure_ascii=False),
            json.dumps(data.get('style_config', {}), ensure_ascii=False),
            json.dumps(data.get('business_rules', {}), ensure_ascii=False)
        ))
        
        template_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # 记录使用日志
        log_template_usage(template_id, 'save', f'保存模板：{data["template_name"]}')
        
        return jsonify({
            'success': True,
            'template_id': template_id,
            'template_key': template_key,
            'message': '模板保存成功'
        })
    
    except Exception as e:
        return jsonify({'error': f'保存模板失败：{str(e)}'}), 500


@templates_bp.route('/api/templates/<int:template_id>', methods=['PUT'])
def update_template(template_id):
    """
    更新模板配置
    """
    try:
        data = request.json
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 构建更新字段
        update_fields = []
        values = []
        
        if 'template_name' in data:
            update_fields.append('template_name = ?')
            values.append(data['template_name'])
        
        if 'template_type' in data:
            update_fields.append('template_type = ?')
            values.append(data['template_type'])
        
        if 'editable_config' in data:
            update_fields.append('editable_config = ?')
            values.append(json.dumps(data['editable_config'], ensure_ascii=False))
        
        if 'business_rules' in data:
            update_fields.append('business_rules = ?')
            values.append(json.dumps(data['business_rules'], ensure_ascii=False))
        
        # 总是更新时间
        update_fields.append('updated_at = CURRENT_TIMESTAMP')
        
        values.append(template_id)
        
        sql = f'''
            UPDATE templates
            SET {', '.join(update_fields)}
            WHERE id = ?
        '''
        
        cursor.execute(sql, values)
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': '模板不存在'}), 404
        
        conn.commit()
        conn.close()
        
        # 记录使用日志
        log_template_usage(template_id, 'update', f'更新模板')
        
        return jsonify({'success': True, 'message': '模板更新成功'})
    
    except Exception as e:
        return jsonify({'error': f'更新模板失败：{str(e)}'}), 500


@templates_bp.route('/api/templates/<int:template_id>', methods=['DELETE'])
def delete_template(template_id):
    """
    删除模板（软删除）
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE templates
            SET is_active = 0, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (template_id,))
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({'error': '模板不存在'}), 404
        
        conn.commit()
        conn.close()
        
        # 记录使用日志
        log_template_usage(template_id, 'delete', '删除模板')
        
        return jsonify({'success': True, 'message': '模板删除成功'})
    
    except Exception as e:
        return jsonify({'error': f'删除模板失败：{str(e)}'}), 500


@templates_bp.route('/api/templates/apply', methods=['POST'])
def apply_template():
    """
    应用模板生成新文件
    请求 JSON:
    {
        "template_id": 1,
        "data": {...},  # 要填充的数据
        "output_filename": "可选的输出文件名"
    }
    """
    try:
        data = request.json
        
        if 'template_id' not in data:
            return jsonify({'error': '缺少 template_id'}), 400
        
        if 'data' not in data:
            return jsonify({'error': '缺少填充数据'}), 400
        
        # 获取模板
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM templates
            WHERE id = ? AND is_active = 1
        ''', (data['template_id'],))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'error': '模板不存在或已禁用'}), 404
        
        # 解析模板数据
        analyzed_data = json.loads(row[5]) if row[5] else {}
        editable_config = json.loads(row[6]) if row[6] else {}
        style_config = json.loads(row[9]) if row[9] else {}
        
        # 生成输出文件
        output_filename = data.get('output_filename', f"template_output_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        output_path = GENERATED_FOLDER / output_filename
        
        # 使用分析器生成文件
        from excel_template_analyzer import generate_from_template
        generate_from_template(
            template_file=row[4],  # original_file_path
            output_file=str(output_path),
            data=data['data'],
            editable_config=editable_config
        )
        
        # 记录使用日志
        log_template_usage(data['template_id'], 'apply', f'生成文件：{output_filename}')
        
        return jsonify({
            'success': True,
            'output_path': str(output_path),
            'output_filename': output_filename,
            'message': '文件生成成功'
        })
    
    except Exception as e:
        return jsonify({'error': f'应用模板失败：{str(e)}'}), 500


def auto_detect_template_type(analyzed_data: dict) -> str:
    """
    自动识别模板类型
    根据分析结果中的关键词判断
    """
    cells = analyzed_data.get('cells', {})
    
    # 收集所有单元格的值
    all_values = []
    for cell_data in cells.values():
        if cell_data.get('value'):
            all_values.append(str(cell_data['value']))
    
    all_text = ' '.join(all_values).upper()
    
    # 匹配关键词
    if '送货单' in all_text or '发货单' in all_text:
        return '送货单'
    elif '订单' in all_text:
        return '订单'
    elif '清单' in all_text:
        return '清单'
    elif '收据' in all_text:
        return '收据'
    elif '报表' in all_text:
        return '报表'
    elif '产品' in all_text:
        return '产品表'
    elif '客户' in all_text:
        return '客户表'
    else:
        return '通用'


def log_template_usage(template_id: int, action: str, result: str):
    """记录模板使用日志"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO template_usage_log (template_id, action, result)
            VALUES (?, ?, ?)
        ''', (template_id, action, result))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"记录模板使用日志失败：{e}")


# 导出蓝图
def init_templates_routes(app):
    """初始化模板路由"""
    app.register_blueprint(templates_bp)
