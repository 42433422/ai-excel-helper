"""
Excel 数据提取和导入 API 路由
"""

from flask import Blueprint, request, jsonify
from pathlib import Path
import json
from datetime import datetime
from typing import Dict, List, Any

# 导入数据提取器
from excel_data_extractor import ExcelDataExtractor, extract_data, clean_and_validate

# 导入数据库
from db import get_db_connection

extract_bp = Blueprint('excel_extract', __name__)

# 上传目录
UPLOAD_FOLDER = Path(__file__).parent / 'uploads' / 'templates'


@extract_bp.route('/api/extract/analyze', methods=['POST'])
def analyze_and_extract():
    """
    分析并提取 Excel 数据
    POST /api/extract/analyze
    {
        "file_path": "uploads/templates/xxx.xlsx",
        "template_id": 1,  // 可选
        "auto_detect": true
    }
    """
    try:
        data = request.json
        file_path = data.get('file_path')
        
        if not file_path:
            return jsonify({'error': '缺少 file_path 参数'}), 400
        
        # 检查文件是否存在
        full_path = Path(file_path)
        if not full_path.exists():
            full_path = UPLOAD_FOLDER / file_path
            if not full_path.exists():
                return jsonify({'error': '文件不存在'}), 404
        
        # 提取数据
        extractor = ExcelDataExtractor(str(full_path))
        result = extractor.extract()
        
        # 构建响应
        response = {
            'success': True,
            'data_type': result.data_type,
            'confidence': result.confidence,
            'field_mapping': result.field_mapping,
            'extracted_data': result.data,
            'validation': result.validation,
            'headers': extractor.headers
        }
        
        # 记录日志
        log_extraction(
            file_name=full_path.name,
            data_type=result.data_type,
            total_rows=len(result.data),
            valid_rows=result.validation['valid']
        )
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({'error': f'提取失败：{str(e)}'}), 500


@extract_bp.route('/api/extract/preview/<int:log_id>', methods=['GET'])
def get_preview(log_id: int):
    """
    获取提取数据预览
    GET /api/extract/preview/{log_id}
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM extract_logs
            WHERE id = ?
        ''', (log_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({'error': '日志不存在'}), 404
        
        # 这里应该从缓存或临时存储中获取数据
        # 简化版本直接返回日志信息
        return jsonify({
            'id': row[0],
            'file_name': row[1],
            'data_type': row[2],
            'total_rows': row[3],
            'status': row[7]
        })
    
    except Exception as e:
        return jsonify({'error': f'获取预览失败：{str(e)}'}), 500


@extract_bp.route('/api/extract/import_products', methods=['POST'])
def import_products():
    """
    导入产品数据
    POST /api/extract/import_products
    {
        "data": [...],
        "field_mapping": {...},
        "options": {
            "skip_duplicates": true,
            "validate_before_import": true,
            "clean_data": true
        }
    }
    """
    try:
        data = request.json
        extracted_data = data.get('data', [])
        options = data.get('options', {})
        
        if not extracted_data:
            return jsonify({'error': '缺少数据'}), 400
        
        # 清洗数据
        if options.get('clean_data', True):
            # 这里应该调用清洗函数
            pass
        
        # 验证数据
        if options.get('validate_before_import', True):
            # 这里应该调用验证函数
            pass
        
        # 导入数据库
        conn = get_db_connection()
        cursor = conn.cursor()
        
        imported = 0
        skipped = 0
        failed = 0
        skipped_items = []
        failed_items = []
        
        for row_data in extracted_data:
            try:
                # 检查是否重复
                if options.get('skip_duplicates', True):
                    cursor.execute('''
                        SELECT id FROM products
                        WHERE product_code = ?
                    ''', (row_data.get('product_code'),))
                    
                    if cursor.fetchone():
                        skipped += 1
                        skipped_items.append(row_data.get('product_code'))
                        continue
                
                # 插入产品
                cursor.execute('''
                    INSERT INTO products (
                        product_code, product_name, specification,
                        unit_price, unit, remark
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    row_data.get('product_code'),
                    row_data.get('product_name'),
                    row_data.get('specification'),
                    row_data.get('unit_price'),
                    row_data.get('unit'),
                    row_data.get('remark')
                ))
                
                imported += 1
                
            except Exception as e:
                failed += 1
                failed_items.append({
                    'data': row_data,
                    'error': str(e)
                })
        
        conn.commit()
        conn.close()
        
        # 记录日志
        log_import(
            file_name="products_import",
            data_type="products",
            total_rows=len(extracted_data),
            imported_rows=imported,
            skipped_rows=skipped,
            failed_rows=failed,
            status="completed"
        )
        
        return jsonify({
            'success': True,
            'imported': imported,
            'skipped': skipped,
            'failed': failed,
            'details': {
                'skipped_items': skipped_items,
                'failed_items': failed_items
            }
        })
    
    except Exception as e:
        return jsonify({'error': f'导入失败：{str(e)}'}), 500


@extract_bp.route('/api/extract/import_customers', methods=['POST'])
def import_customers():
    """
    导入客户数据
    POST /api/extract/import_customers
    """
    try:
        data = request.json
        extracted_data = data.get('data', [])
        options = data.get('options', {})
        
        if not extracted_data:
            return jsonify({'error': '缺少数据'}), 400
        
        # 导入数据库
        conn = get_db_connection()
        cursor = conn.cursor()
        
        imported = 0
        skipped = 0
        failed = 0
        skipped_items = []
        failed_items = []
        
        for row_data in extracted_data:
            try:
                # 检查是否重复
                if options.get('skip_duplicates', True):
                    customer_name = row_data.get('customer_name') or row_data.get('company_name')
                    cursor.execute('''
                        SELECT id FROM purchase_units
                        WHERE unit_name = ?
                    ''', (customer_name,))
                    
                    if cursor.fetchone():
                        skipped += 1
                        skipped_items.append(customer_name)
                        continue
                
                # 插入客户
                cursor.execute('''
                    INSERT INTO purchase_units (
                        unit_name, contact_person, phone,
                        address, remark
                    ) VALUES (?, ?, ?, ?, ?)
                ''', (
                    row_data.get('customer_name') or row_data.get('company_name'),
                    row_data.get('contact_person'),
                    row_data.get('phone') or row_data.get('mobile'),
                    row_data.get('address'),
                    row_data.get('remark')
                ))
                
                imported += 1
                
            except Exception as e:
                failed += 1
                failed_items.append({
                    'data': row_data,
                    'error': str(e)
                })
        
        conn.commit()
        conn.close()
        
        # 记录日志
        log_import(
            file_name="customers_import",
            data_type="customers",
            total_rows=len(extracted_data),
            imported_rows=imported,
            skipped_rows=skipped,
            failed_rows=failed,
            status="completed"
        )
        
        return jsonify({
            'success': True,
            'imported': imported,
            'skipped': skipped,
            'failed': failed,
            'details': {
                'skipped_items': skipped_items,
                'failed_items': failed_items
            }
        })
    
    except Exception as e:
        return jsonify({'error': f'导入失败：{str(e)}'}), 500


@extract_bp.route('/api/extract/import_orders', methods=['POST'])
def import_orders():
    """
    导入订单数据
    POST /api/extract/import_orders
    """
    try:
        data = request.json
        extracted_data = data.get('data', [])
        options = data.get('options', {})
        
        if not extracted_data:
            return jsonify({'error': '缺少数据'}), 400
        
        # 导入数据库
        conn = get_db_connection()
        cursor = conn.cursor()
        
        imported = 0
        failed = 0
        failed_items = []
        
        for row_data in extracted_data:
            try:
                # 插入出货记录
                cursor.execute('''
                    INSERT INTO shipment_records (
                        order_number, customer_id, order_date,
                        total_amount, status, remark
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    row_data.get('order_number'),
                    row_data.get('customer_id'),
                    row_data.get('date'),
                    row_data.get('total_amount'),
                    'pending',
                    row_data.get('remark')
                ))
                
                imported += 1
                
            except Exception as e:
                failed += 1
                failed_items.append({
                    'data': row_data,
                    'error': str(e)
                })
        
        conn.commit()
        conn.close()
        
        # 记录日志
        log_import(
            file_name="orders_import",
            data_type="orders",
            total_rows=len(extracted_data),
            imported_rows=imported,
            skipped_rows=0,
            failed_rows=failed,
            status="completed"
        )
        
        return jsonify({
            'success': True,
            'imported': imported,
            'failed': failed,
            'details': {
                'failed_items': failed_items
            }
        })
    
    except Exception as e:
        return jsonify({'error': f'导入失败：{str(e)}'}), 500


@extract_bp.route('/api/extract/logs', methods=['GET'])
def get_logs():
    """
    获取导入日志
    GET /api/extract/logs?data_type=products&limit=50
    """
    try:
        data_type = request.args.get('data_type')
        limit = request.args.get('limit', 50)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if data_type:
            cursor.execute('''
                SELECT * FROM extract_logs
                WHERE data_type = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (data_type, limit))
        else:
            cursor.execute('''
                SELECT * FROM extract_logs
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        logs = []
        for row in rows:
            logs.append({
                'id': row[0],
                'file_name': row[1],
                'data_type': row[2],
                'total_rows': row[3],
                'imported_rows': row[4],
                'skipped_rows': row[5],
                'failed_rows': row[6],
                'status': row[7],
                'error_message': row[8],
                'created_at': row[9]
            })
        
        return jsonify({'logs': logs})
    
    except Exception as e:
        return jsonify({'error': f'获取日志失败：{str(e)}'}), 500


def log_extraction(file_name: str, data_type: str, total_rows: int, valid_rows: int):
    """记录提取日志"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO extract_logs (
                file_name, data_type, total_rows,
                imported_rows, status
            ) VALUES (?, ?, ?, ?, ?)
        ''', (file_name, data_type, total_rows, valid_rows, 'completed'))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"记录提取日志失败：{e}")


def log_import(file_name: str, data_type: str, total_rows: int,
               imported_rows: int, skipped_rows: int, failed_rows: int, status: str):
    """记录导入日志"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO extract_logs (
                file_name, data_type, total_rows,
                imported_rows, skipped_rows, failed_rows, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (file_name, data_type, total_rows, imported_rows, skipped_rows, failed_rows, status))
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"记录导入日志失败：{e}")


# 导出蓝图
def init_extract_routes(app):
    """初始化提取路由"""
    app.register_blueprint(extract_bp)
