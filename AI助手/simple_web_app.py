#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的Web应用，同时提供前端页面和API服务
"""

import os
import sys
import logging
import sqlite3
import json
from flask import Flask, request, jsonify, send_from_directory
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 获取脚本所在目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 创建Flask应用
app = Flask(__name__)

# 确保templates目录存在
os.makedirs(os.path.join(BASE_DIR, 'templates'), exist_ok=True)

# 注意：保持端口分离 - 发货单生成器在5000端口

def get_db_path():
    """获取数据库路径"""
    db_path = os.path.join(BASE_DIR, 'products.db')
    logger.info(f"数据库路径: {db_path}")
    return db_path

def query_db(sql, params=(), fetch_one=False):
    """查询数据库"""
    try:
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql, params)
        
        if fetch_one:
            result = cursor.fetchone()
        else:
            result = cursor.fetchall()
        
        conn.close()
        return result
    except Exception as e:
        logger.error(f"数据库查询失败: {e}")
        return None

def execute_db(sql, params=()):
    """执行数据库操作"""
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id
    except Exception as e:
        logger.error(f"数据库操作失败: {e}")
        return None

# ==================== 页面路由 ====================

@app.route('/')
def index():
    """主页"""
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>发货单生成系统</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 40px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            .header { text-align: center; margin-bottom: 40px; }
            .nav { display: flex; justify-content: center; gap: 20px; }
            .nav a { padding: 12px 24px; background: #007bff; color: white; text-decoration: none; border-radius: 6px; transition: background 0.3s; }
            .nav a:hover { background: #0056b3; }
            .description { margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 8px; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎯 发货单生成系统</h1>
                <p>专业的数据库管理和发货单生成平台</p>
            </div>
            
            <div class="nav">
                <a href="/database">📊 数据库管理</a>
                <a href="/shipment">📋 发货单生成</a>
            </div>
            
            <div class="description">
                <h3>🚀 功能介绍</h3>
                <ul>
                    <li><strong>数据库管理</strong>：以客户单位为中心查看和管理产品信息</li>
                    <li><strong>发货单生成</strong>：智能解析订单并生成专业Excel发货单</li>
                    <li><strong>价格管理</strong>：实时查看和调整产品价格</li>
                    <li><strong>客户管理</strong>：管理客户信息和产品关联</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/database')
def database():
    """数据库管理页面"""
    return send_from_directory('templates', 'database_management.html')

@app.route('/shipment')
def shipment():
    """发货单生成页面"""
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        logger.error(f"无法读取发货单页面: {e}")
        return '''
        <div style="text-align: center; padding: 50px;">
            <h1>发货单生成页面加载失败</h1>
            <p>错误: ''' + str(e) + '''</p>
            <a href="/">返回主页</a>
        </div>
        '''

# ==================== API路由 ====================

@app.route('/api/customers', methods=['GET'])
def get_customers():
    """获取所有客户单位"""
    try:
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 查询采购单位
        cursor.execute("""
            SELECT id, unit_name, contact_person, contact_phone, address, 
                   is_active, created_at
            FROM purchase_units 
            WHERE is_active = 1
            ORDER BY unit_name
        """)
        customers = cursor.fetchall()
        
        conn.close()
        
        result = []
        for customer in customers:
            result.append({
                'id': customer['id'],
                'unit_name': customer['unit_name'],
                'contact_person': customer['contact_person'],
                'contact_phone': customer['contact_phone'],
                'address': customer['address'],
                'is_active': customer['is_active']
            })
        
        return jsonify({
            "success": True,
            "customers": result,
            "count": len(result)
        })
        
    except Exception as e:
        logger.error(f"获取客户单位失败: {e}")
        return jsonify({"success": False, "message": f"获取客户单位失败: {str(e)}"}), 500


@app.route('/api/customers/<int:customer_id>', methods=['PUT'])
def update_customer(customer_id):
    """更新客户信息"""
    try:
        data = request.get_json()
        
        # 验证必需字段
        if not data:
            return jsonify({"success": False, "message": "缺少请求数据"}), 400
        
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        
        # 检查客户是否存在
        cursor.execute("SELECT id FROM purchase_units WHERE id = ?", [customer_id])
        if not cursor.fetchone():
            conn.close()
            return jsonify({"success": False, "message": "客户不存在"}), 404
        
        # 更新客户信息
        cursor.execute("""
            UPDATE purchase_units 
            SET contact_person = ?, contact_phone = ?, address = ?, 
                is_active = ?, updated_at = datetime('now')
            WHERE id = ?
        """, (
            data.get('contact_person'),
            data.get('contact_phone'),
            data.get('address'),
            data.get('is_active', 1),
            customer_id
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "客户信息更新成功"
        })
        
    except Exception as e:
        logger.error(f"更新客户信息失败: {e}")
        return jsonify({"success": False, "message": f"更新客户信息失败: {str(e)}"}), 500


@app.route('/api/products/<int:customer_id>', methods=['GET'])
def get_products_by_customer(customer_id):
    """获取指定客户的产品列表"""
    try:
        # 首先从统一数据库获取客户信息
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM purchase_units WHERE id = ? AND is_active = 1
        """, [customer_id])
        customer = cursor.fetchone()
        
        if not customer:
            conn.close()
            return jsonify({"success": False, "message": "客户不存在"}), 404
        
        customer_name = customer['unit_name']
        conn.close()
        
        # 从单位数据库读取产品
        units_dir = os.path.join(BASE_DIR, 'unit_databases')
        db_path = os.path.join(units_dir, f'{customer_name}.db')
        
        if not os.path.exists(db_path):
            return jsonify({
                "success": True,
                "customer_name": customer_name,
                "products": [],
                "count": 0,
                "message": f"未找到客户 {customer_name} 的产品数据库"
            })
        
        # 连接单位数据库
        unit_conn = sqlite3.connect(db_path)
        unit_conn.row_factory = sqlite3.Row
        unit_cursor = unit_conn.cursor()
        
        # 获取产品列表
        unit_cursor.execute("SELECT * FROM products ORDER BY id ASC")
        unit_products = unit_cursor.fetchall()
        
        # 转换结果格式
        products = []
        for product in unit_products:
            product_dict = dict(product)  # 将sqlite3.Row转换为字典
            products.append({
                'id': product_dict.get('id', 0),
                'model_number': product_dict.get('model_number', ''),
                'name': product_dict.get('name', ''),
                'specification': product_dict.get('specification', ''),
                'price': float(product_dict.get('price', 0)),
                'quantity': product_dict.get('quantity', 1),
                'description': product_dict.get('description', ''),
                'category': product_dict.get('category', ''),
                'brand': product_dict.get('brand', ''),
                'unit': product_dict.get('unit', ''),
                'is_active': 1,
                'custom_price': float(product_dict.get('price', 0)) if product_dict.get('price') else 0.0,
                'created_at': product_dict.get('created_at', ''),
                'updated_at': product_dict.get('updated_at', '')
            })
        
        unit_conn.close()
        
        return jsonify({
            "success": True,
            "customer_name": customer_name,
            "products": products,
            "count": len(products)
        })
        
    except Exception as e:
        logger.error(f"获取客户产品列表失败: {e}")
        return jsonify({"success": False, "message": f"获取客户产品列表失败: {str(e)}"}), 500


@app.route('/api/products', methods=['POST'])
def add_product():
    """添加新产品"""
    try:
        data = request.get_json()
        
        # 验证必需字段
        required_fields = ['model_number', 'name', 'price', 'unit']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    "success": False, 
                    "message": f"缺少必需字段: {field}"
                }), 400
        
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        
        # 插入新产品
        cursor.execute("""
            INSERT INTO products (model_number, name, specification, price, quantity, 
                                description, category, brand, unit, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now'), datetime('now'))
        """, (
            data['model_number'],
            data['name'],
            data.get('specification', ''),
            float(data['price']),
            data.get('quantity', 1),
            data.get('description', ''),
            data.get('category', ''),
            data.get('brand', ''),
            data['unit']
        ))
        
        product_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "产品添加成功",
            "product_id": product_id
        })
        
    except Exception as e:
        logger.error(f"添加产品失败: {e}")
        return jsonify({"success": False, "message": f"添加产品失败: {str(e)}"}), 500


@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """更新产品信息"""
    try:
        data = request.get_json()
        
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        
        # 构建更新语句
        update_fields = []
        update_values = []
        
        allowed_fields = ['model_number', 'name', 'specification', 'price', 'quantity', 
                         'description', 'category', 'brand', 'unit', 'is_active']
        
        for field in allowed_fields:
            if field in data:
                update_fields.append(f"{field} = ?")
                if field == 'price':
                    update_values.append(float(data[field]))
                else:
                    update_values.append(data[field])
        
        if not update_fields:
            conn.close()
            return jsonify({"success": False, "message": "没有有效的更新字段"}), 400
        
        update_values.append(product_id)
        
        # 执行更新
        sql = f"""
            UPDATE products 
            SET {', '.join(update_fields)}, updated_at = datetime('now')
            WHERE id = ?
        """
        cursor.execute(sql, update_values)
        
        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"success": False, "message": "产品不存在"}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "产品更新成功"
        })
        
    except Exception as e:
        logger.error(f"更新产品失败: {e}")
        return jsonify({"success": False, "message": f"更新产品失败: {str(e)}"}), 500


@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """删除产品"""
    try:
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        
        # 先检查产品是否存在
        cursor.execute("SELECT id FROM products WHERE id = ?", [product_id])
        if not cursor.fetchone():
            conn.close()
            return jsonify({"success": False, "message": "产品不存在"}), 404
        
        # 删除产品（这里使用软删除，设置is_active = 0）
        cursor.execute("""
            UPDATE products 
            SET is_active = 0, updated_at = datetime('now')
            WHERE id = ?
        """, [product_id])
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "产品删除成功"
        })
        
    except Exception as e:
        logger.error(f"删除产品失败: {e}")
        return jsonify({"success": False, "message": f"删除产品失败: {str(e)}"}), 500


@app.route('/api/products', methods=['GET'])
def get_products_api():
    """获取产品列表API - 支持从单位数据库加载"""
    try:
        # 获取单位参数
        unit_name = request.args.get('unit', '')
        
        products = []
        
        if unit_name:
            # 从单位数据库加载产品
            units_dir = os.path.join(BASE_DIR, 'unit_databases')
            db_path = os.path.join(units_dir, f'{unit_name}.db')
            
            if os.path.exists(db_path):
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('SELECT * FROM products ORDER BY id ASC')
                db_products = cursor.fetchall()
                
                for product in db_products:
                    # sqlite3.Row转换为字典
                    product_dict = dict(product)
                    products.append({
                        'id': product_dict.get('id', 0),
                        'model_number': product_dict.get('model_number', ''),
                        'name': product_dict.get('name', ''),
                        'specification': product_dict.get('specification', ''),
                        'price': float(product_dict.get('price', 0)),
                        'quantity': product_dict.get('quantity', 1),
                        'description': product_dict.get('description', ''),
                        'created_at': product_dict.get('created_at', '')
                    })
                
                conn.close()
                
                return jsonify({
                    "success": True,
                    "data": products,
                    "count": len(products),
                    "source": "unit_database",
                    "unit": unit_name
                })
            else:
                return jsonify({
                    "success": False,
                    "message": f"未找到单位数据库: {unit_name}"
                }), 404
        else:
            # 从旧版统一数据库加载
            all_products = query_db('SELECT * FROM products WHERE is_active = 1 ORDER BY created_at DESC')
            
            if all_products:
                for product in all_products:
                    product_dict = dict(product) if hasattr(product, 'keys') else product
                    products.append({
                        'id': product_dict.get('id', 0),
                        'model_number': product_dict.get('model_number', ''),
                        'name': product_dict.get('name', ''),
                        'specification': product_dict.get('specification', ''),
                        'price': float(product_dict.get('price', 0)) if product_dict.get('price') else 0,
                        'quantity': product_dict.get('quantity', 1),
                        'description': product_dict.get('description', ''),
                        'created_at': product_dict.get('created_at', '')
                    })
            
            return jsonify({
                "success": True,
                "data": products,
                "count": len(products),
                "source": "unified_database"
            })
    
    except Exception as e:
        logger.error(f"获取产品列表失败: {e}")
        return jsonify({"success": False, "message": f"获取产品列表失败：{str(e)}"})


@app.route('/api/units', methods=['GET'])
def get_units_api():
    """获取所有可用单位列表"""
    try:
        import glob
        
        units_dir = os.path.join(BASE_DIR, 'unit_databases')
        
        if not os.path.exists(units_dir):
            return jsonify({
                "success": True,
                "data": [],
                "count": 0
            })
        
        # 获取所有数据库文件
        db_files = glob.glob(os.path.join(units_dir, '*.db'))
        
        units = []
        for db_path in db_files:
            db_filename = os.path.basename(db_path)
            unit_name = db_filename[:-3]  # 移除 .db 后缀
            
            # 获取产品数量
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM products')
                product_count = cursor.fetchone()[0]
                conn.close()
                
                units.append({
                    'name': unit_name,
                    'product_count': product_count
                })
            except Exception as ex:
                logger.warning(f"读取单位数据库 {unit_name} 失败: {ex}")
        
        return jsonify({
            "success": True,
            "data": units,
            "count": len(units)
        })
    
    except Exception as e:
        logger.error(f"获取单位列表失败: {e}")
        return jsonify({"success": False, "message": f"获取单位列表失败：{str(e)}"})


@app.route('/api/customer-products/<int:customer_id>/<int:product_id>', methods=['PUT'])
def update_customer_product_price(customer_id, product_id):
    """更新客户专属产品价格"""
    try:
        data = request.get_json()
        
        if 'custom_price' not in data:
            return jsonify({"success": False, "message": "缺少custom_price字段"}), 400
        
        custom_price = float(data['custom_price'])
        is_active = data.get('is_active', True)
        
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        
        # 检查是否已存在记录
        cursor.execute("""
            SELECT id FROM customer_products 
            WHERE unit_id = ? AND product_id = ?
        """, [customer_id, product_id])
        
        existing = cursor.fetchone()
        
        if existing:
            # 更新现有记录
            cursor.execute("""
                UPDATE customer_products 
                SET custom_price = ?, is_active = ?, updated_at = datetime('now')
                WHERE unit_id = ? AND product_id = ?
            """, [custom_price, is_active, customer_id, product_id])
        else:
            # 创建新记录
            cursor.execute("""
                INSERT INTO customer_products (unit_id, product_id, custom_price, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
            """, [customer_id, product_id, custom_price, is_active])
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "客户专属价格更新成功"
        })
        
    except Exception as e:
        logger.error(f"更新客户专属价格失败: {e}")
        return jsonify({"success": False, "message": f"更新客户专属价格失败: {str(e)}"}), 500


@app.route('/health')
def health_check():
    """健康检查"""
    return jsonify({"status": "ok", "service": "database-management-system"})


if __name__ == '__main__':
    logger.info("🚀 启动数据库管理系统...")
    logger.info(f"📁 工作目录: {BASE_DIR}")
    logger.info(f"🗄️  数据库: {get_db_path()}")
    logger.info("🌐 服务地址: http://localhost:5000")
    logger.info("📊 数据库管理: http://localhost:5000/database")
    
    # 启动Flask应用
    app.run(host='0.0.0.0', port=5000, debug=True)