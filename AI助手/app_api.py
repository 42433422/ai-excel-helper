#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发货单生成系统后端API
"""

import os
import glob
import sys
import logging
import sqlite3
import re
import urllib.parse
from datetime import datetime
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS


def get_unit_db_connection(unit):
    """
    获取单位数据库连接
    :param unit: 单位名称
    :return: (conn, cursor) 或 None
    """
    try:
        # 解码URL编码的单位名称
        unit = urllib.parse.unquote(unit)
        
        # 构建数据库路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(current_dir, 'unit_databases', f'{unit}.db')
        
        if not os.path.exists(db_path):
            logger.error(f"单位数据库不存在: {unit}, 路径: {db_path}")
            return None
        
        # 连接数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查products表是否存在
        cursor.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="products"')
        if not cursor.fetchone():
            logger.error(f"单位数据库中不存在products表: {unit}")
            conn.close()
            return None
        
        return conn, cursor
        
    except Exception as e:
        logger.error(f"获取单位数据库连接失败: {e}")
        return None
from shipment_document import DocumentAPIGenerator
from shipment_api import shipment_bp
from print_utils import get_printers, print_document
from flask import send_from_directory
from label_generator import ProductLabelGenerator
from ratio_rules_manager_fixed import RatioRulesManager

# 创建参考配比规则管理器实例
ratio_manager = RatioRulesManager()

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
logger = logging.getLogger(__name__)

# 获取脚本所在目录（兼容PyInstaller打包）
def get_base_dir():
    """获取应用基础目录（兼容PyInstaller打包）"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller打包后的临时目录
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = get_base_dir()
logger.info(f"Flask应用运行目录: {BASE_DIR}")

# 获取应用程序数据目录（用于存储数据库）
def get_app_data_dir():
    """获取应用程序数据目录"""
    if hasattr(sys, '_MEIPASS'):
        app_data = os.environ.get('APPDATA')
        if not app_data:
            app_data = os.environ.get('LOCALAPPDATA')
        app_data_dir = os.path.join(app_data, 'AI助手系统')
    else:
        app_data_dir = BASE_DIR
    os.makedirs(app_data_dir, exist_ok=True)
    return app_data_dir

APP_DATA_DIR = get_app_data_dir()
logger.info(f"应用程序数据目录: {APP_DATA_DIR}")

# 在PyInstaller打包环境下，从资源目录复制数据库文件到应用数据目录
def initialize_databases():
    """初始化数据库（PyInstaller打包环境需要）"""
    import shutil
    
    is_frozen = hasattr(sys, '_MEIPASS')
    source_dir = sys._MEIPASS if is_frozen else BASE_DIR
    work_dir = APP_DATA_DIR
    
    logger.info(f"PyInstaller打包环境: {is_frozen}")
    logger.info(f"源目录: {source_dir}")
    logger.info(f"工作目录: {work_dir}")
    
    db_files = ['products.db', 'customers.db', 'inventory.db', 'voice_learning.db', 'error_collection.db']
    
    for db_file in db_files:
        source_path = os.path.join(source_dir, db_file)
        work_path = os.path.join(work_dir, db_file)
        
        logger.info(f"检查数据库: {db_file}")
        
        if not os.path.exists(source_path):
            logger.warning(f"  源数据库文件不存在: {source_path}")
            continue
            
        if os.path.exists(work_path):
            logger.info(f"  工作数据库已存在，跳过复制")
            continue
            
        try:
            shutil.copy2(source_path, work_path)
            logger.info(f"  已复制数据库文件: {db_file}")
            
            if os.path.exists(work_path):
                cursor = sqlite3.connect(work_path).cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [t[0] for t in cursor.fetchall()]
                logger.info(f"  数据库表: {tables}")
        except Exception as e:
            logger.error(f"  处理数据库文件失败 {db_file}: {e}")

# 初始化数据库
initialize_databases()

# 创建Flask应用
app = Flask(__name__)
app.secret_key = os.urandom(24)  # 用于session加密

# 启用CORS支持
CORS(app, resources={
    r"/api/*": {
        "origins": "*",
        "methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type"]
    }
})

# 注册发货单API蓝图（在Flask应用创建之后）
app.register_blueprint(shipment_bp)

# 注册OCR API蓝图
from ocr_api import ocr_bp
app.register_blueprint(ocr_bp)

# 测试路由
@app.route('/test')
def test():
    """测试路由"""
    return jsonify({"success": True, "message": "测试成功"})

@app.route('/database')
def database():
    """数据库管理页面"""
    import sqlite3
    
    # 开发模式下跳过验证
    if DEV_MODE:
        return send_from_directory('templates', 'database_management.html')
    
    # 尝试从URL参数、cookie或header获取session_id
    session_id = (request.args.get('session_id') or 
                  request.cookies.get('session_id') or 
                  request.headers.get('X-Session-ID'))
    
    if not session_id:
        return '''
        <!DOCTYPE html>
        <html>
        <head><title>需要登录</title></head>
        <body style="font-family: Arial; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #f5f5f5;">
            <div style="background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center;">
                <h2 style="color: #333;">🔒 需要登录</h2>
                <p style="color: #666;">请先登录后再访问数据库管理页面</p>
                <a href="/" style="display: inline-block; margin-top: 20px; padding: 10px 30px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px;">返回首页登录</a>
            </div>
        </body>
        </html>
        ''', 401
    
    try:
        conn = sqlite3.connect(USER_DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.id, u.username, u.role FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.session_id = ? AND s.expires_at > datetime('now')
        ''', (session_id,))
        user = cursor.fetchone()
        conn.close()
        
        if not user or user[2] != 'admin':
            return '''
            <!DOCTYPE html>
            <html>
            <head><title>权限不足</title></head>
            <body style="font-family: Arial; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #f5f5f5;">
                <div style="background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center;">
                    <h2 style="color: #f44336;">⚠️ 权限不足</h2>
                    <p style="color: #666;">只有管理员才能访问数据库管理页面</p>
                    <a href="/" style="display: inline-block; margin-top: 20px; padding: 10px 30px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px;">返回首页</a>
                </div>
            </body>
            </html>
            ''', 403
        
        return send_from_directory('templates', 'database_management.html')
        
    except Exception as e:
        logger.error(f"验证失败: {e}")
        return '''
        <!DOCTYPE html>
        <html>
        <head><title>验证失败</title></head>
        <body style="font-family: Arial; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #f5f5f5;">
            <div style="background: white; padding: 40px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center;">
                <h2 style="color: #f44336;">验证失败</h2>
                <p style="color: #666;">请重新登录</p>
                <a href="/" style="display: inline-block; margin-top: 20px; padding: 10px 30px; background: #4CAF50; color: white; text-decoration: none; border-radius: 5px;">返回首页</a>
            </div>
        </body>
        </html>
        ''', 401

# 设置静态文件目录为AI助手目录
app.static_folder = BASE_DIR

# 确保outputs目录存在（使用绝对路径）
OUTPUTS_DIR = os.path.join(BASE_DIR, 'outputs')
os.makedirs(OUTPUTS_DIR, exist_ok=True)
logger.info(f"输出目录: {OUTPUTS_DIR}")

# 数据库配置
def get_db_path():
    """获取数据库路径（兼容PyInstaller打包）"""
    if hasattr(sys, '_MEIPASS'):
        db_path = os.path.join(APP_DATA_DIR, 'products.db')
    else:
        db_path = os.path.join(BASE_DIR, 'products.db')
    logger.info(f"数据库路径: {db_path}")
    return db_path

# 用户认证数据库初始化
def init_user_db():
    """初始化用户数据库（兼容PyInstaller打包）"""
    if hasattr(sys, '_MEIPASS'):
        db_path = os.path.join(APP_DATA_DIR, 'users.db')
    else:
        db_path = os.path.join(BASE_DIR, 'users.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            display_name TEXT DEFAULT '',
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    conn.close()
    return db_path

USER_DB_PATH = init_user_db()

# 默认管理员账户（如果不存在则创建）
def create_default_admin():
    """创建默认管理员账户"""
    import hashlib
    conn = sqlite3.connect(USER_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('SELECT id FROM users WHERE username = ?', ('970882904',))
    if not cursor.fetchone():
        hashed_password = hashlib.sha256('1499383833'.encode()).hexdigest()
        cursor.execute('''
            INSERT INTO users (username, password, display_name, role)
            VALUES (?, ?, ?, ?)
        ''', ('970882904', hashed_password, '管理员', 'admin'))
        logger.info("管理员账户已创建 (970882904/1499383833)")
    
    conn.commit()
    conn.close()

create_default_admin()

# 用户认证API
@app.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录"""
    import hashlib
    import uuid
    from datetime import datetime, timedelta
    
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        
        if not username or not password:
            return jsonify({"success": False, "message": "用户名和密码不能为空"}), 400
        
        conn = sqlite3.connect(USER_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, password, display_name, role FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({"success": False, "message": "用户名或密码错误"}), 401
        
        user_id, stored_password, display_name, role = user
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        if hashed_password != stored_password:
            conn.close()
            return jsonify({"success": False, "message": "用户名或密码错误"}), 401
        
        cursor.execute('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', (user_id,))
        
        session_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(hours=24)
        cursor.execute('''
            INSERT INTO sessions (session_id, user_id, expires_at)
            VALUES (?, ?, ?)
        ''', (session_id, user_id, expires_at))
        
        conn.commit()
        conn.close()
        
        logger.info(f"用户 {username} 登录成功")
        
        return jsonify({
            "success": True,
            "message": "登录成功",
            "data": {
                "session_id": session_id,
                "user": {
                    "id": user_id,
                    "username": username,
                    "display_name": display_name or username,
                    "role": role
                }
            }
        })
        
    except Exception as e:
        logger.error(f"登录失败: {e}")
        return jsonify({"success": False, "message": f"登录失败: {str(e)}"}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """用户登出"""
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id')
        
        if session_id:
            conn = sqlite3.connect(USER_DB_PATH)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM sessions WHERE session_id = ?', (session_id,))
            conn.commit()
            conn.close()
        
        return jsonify({"success": True, "message": "登出成功"})
        
    except Exception as e:
        logger.error(f"登出失败: {e}")
        return jsonify({"success": False, "message": f"登出失败: {str(e)}"}), 500

@app.route('/api/auth/check', methods=['POST'])
def check_auth():
    """验证session"""
    import uuid
    from datetime import datetime, timedelta
    
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({"success": False, "message": "未登录"})
        
        conn = sqlite3.connect(USER_DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.id, u.username, u.display_name, u.role, s.expires_at
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.session_id = ? AND s.expires_at > datetime('now')
        ''', (session_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            return jsonify({"success": False, "message": "登录已过期"})
        
        user_id, username, display_name, role, expires_at = user
        
        return jsonify({
            "success": True,
            "data": {
                "user": {
                    "id": user_id,
                    "username": username,
                    "display_name": display_name or username,
                    "role": role
                },
                "expires_at": expires_at
            }
        })
        
    except Exception as e:
        logger.error(f"验证失败: {e}")
        return jsonify({"success": False, "message": f"验证失败: {str(e)}"}), 500

# 开发模式：True=禁用登录验证，False=启用登录验证
DEV_MODE = True

# 登录验证装饰器
def login_required(f):
    """验证用户是否已登录"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 开发模式下跳过验证
        if DEV_MODE:
            request.current_user = {
                'id': 1,
                'username': 'admin',
                'display_name': '管理员',
                'role': 'admin'
            }
            return f(*args, **kwargs)
        
        try:
            data = request.get_json(silent=True) or {}
            session_id = data.get('session_id') or request.headers.get('X-Session-ID')
            
            if not session_id:
                return jsonify({"success": False, "message": "请先登录", "need_login": True}), 401
            
            conn = sqlite3.connect(USER_DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT u.id, u.username, u.display_name, u.role, s.expires_at
                FROM sessions s
                JOIN users u ON s.user_id = u.id
                WHERE s.session_id = ? AND s.expires_at > datetime('now')
            ''', (session_id,))
            
            user = cursor.fetchone()
            conn.close()
            
            if not user:
                return jsonify({"success": False, "message": "登录已过期，请重新登录", "need_login": True}), 401
            
            # 将用户信息存入request对象
            request.current_user = {
                'id': user[0],
                'username': user[1],
                'display_name': user[2] or user[1],
                'role': user[3]
            }
            
            return f(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"验证失败: {e}")
            return jsonify({"success": False, "message": f"验证失败: {str(e)}"}), 500
    
    return decorated_function

# 初始化文档生成器
document_generator = DocumentAPIGenerator()

# 程序启动时自动同步出货记录数据
def startup_shipment_sync():
    """程序启动时自动同步出货记录到数据库"""
    try:
        logger.info("🚀 程序启动，开始同步出货记录数据...")
        
        # 导入完整导入功能
        import sys
        import os
        
        # 获取当前文件所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        import_path = os.path.join(current_dir, 'complete_import_shipment.py')
        
        if os.path.exists(import_path):
            # 动态导入并执行
            import importlib.util
            spec = importlib.util.spec_from_file_location("complete_import_shipment", import_path)
            complete_import_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(complete_import_module)
            
            # 执行导入
            success = complete_import_module.complete_import_shipment_records()
            if success:
                logger.info("✅ 程序启动数据同步完成")
            else:
                logger.warning("⚠️ 程序启动数据同步未找到新数据")
        else:
            logger.warning("⚠️ 完整导入模块不存在，跳过启动同步")
            
    except Exception as e:
        logger.error(f"❌ 程序启动数据同步失败: {e}")

# 自动配置默认的Excel出货记录文件
DEFAULT_EXCEL_PATH = os.path.join(BASE_DIR, '..', '出货记录', '七彩乐园', '七彩乐园.xlsx')
DEFAULT_WORKSHEET = '25出货'

if os.path.exists(DEFAULT_EXCEL_PATH):
    success = document_generator.enable_excel_sync(DEFAULT_EXCEL_PATH, DEFAULT_WORKSHEET)
    if success:
        logger.info(f"✅ 已自动启用Excel同步: {DEFAULT_EXCEL_PATH}")
    else:
        logger.warning(f"❌ 自动启用Excel同步失败: {DEFAULT_EXCEL_PATH}")
else:
    # 尝试备用路径
    backup_path = r'C:\Users\97088\Desktop\新建文件夹 (4)\出货记录\七彩乐园\七彩乐园.xlsx'
    if os.path.exists(backup_path):
        success = document_generator.enable_excel_sync(backup_path, DEFAULT_WORKSHEET)
        if success:
            logger.info(f"✅ 已使用备用路径启用Excel同步: {backup_path}")
        else:
            logger.warning(f"❌ 备用路径Excel同步失败: {backup_path}")
    else:
        logger.warning(f"⚠️ 默认Excel文件不存在: {DEFAULT_EXCEL_PATH}")
        logger.warning(f"⚠️ 备用Excel文件不存在: {backup_path}")

# 执行启动数据同步
startup_shipment_sync()

# 启动时清理备份文件（避免过多备份文件）
def startup_cleanup_backups():
    """程序启动时清理多余的备份文件"""
    try:
        logger.info("🧹 程序启动，开始清理多余备份文件...")
        
        import os
        import glob
        import shutil
        
        # 构建出货记录文件路径
        base_dir = os.path.dirname(os.path.abspath(__file__))
        shipment_dir = os.path.join(base_dir, '..', '出货记录')
        
        if not os.path.exists(shipment_dir):
            logger.info("出货记录文件夹不存在，跳过备份清理")
            return
        
        # 遍历所有客户文件夹
        for item in os.listdir(shipment_dir):
            item_path = os.path.join(shipment_dir, item)
            if os.path.isdir(item_path) and item != '__pycache__':
                # 查找所有备份文件
                backup_pattern = os.path.join(item_path, "*.backup_*")
                backup_files = glob.glob(backup_pattern)
                
                if len(backup_files) > 1:
                    # 按修改时间排序，保留最新的1个
                    backup_files.sort(key=os.path.getmtime, reverse=True)
                    for old_backup in backup_files[1:]:  # 删除除最新外的所有
                        try:
                            os.remove(old_backup)
                            logger.info(f"已删除旧备份: {os.path.basename(old_backup)}")
                        except Exception as e:
                            logger.warning(f"删除备份文件失败 {old_backup}: {e}")
        
        logger.info("✅ 备份文件清理完成")
        
    except Exception as e:
        logger.error(f"❌ 启动时备份清理失败: {e}")

# 执行启动备份清理
startup_cleanup_backups()

# ==================== 数据库操作函数 ====================

def query_db(sql, params=(), fetch_one=False):
    """查询数据库"""
    try:
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row  # 使结果可以通过列名访问
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

def row_to_dict(row):
    """将sqlite3.Row对象转换为字典"""
    if row is None:
        return None
    return {key: row[key] for key in row.keys()}

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

# ==================== 购买单位管理API ====================

@app.route("/api/purchase_units", methods=["GET"])
def get_purchase_units():
    """获取购买单位列表"""
    try:
        # 从正确的purchase_units表查询购买单位
        units = query_db("SELECT * FROM purchase_units WHERE is_active = 1 ORDER BY unit_name")
        
        if units:
            result = []
            for unit in units:
                result.append({
                    "id": unit["id"],
                    "unit_name": unit["unit_name"],
                    "contact_person": unit["contact_person"] if unit["contact_person"] else "",
                    "contact_phone": unit["contact_phone"] if unit["contact_phone"] else "",
                    "address": unit["address"] if unit["address"] else ""
                })
            return jsonify({
                "success": True,
                "data": result,
                "count": len(result)
            })
        else:
            return jsonify({
                "success": True,
                "data": [],
                "count": 0
            })
    
    except Exception as e:
        logger.error(f"获取购买单位列表失败: {e}")
        return jsonify({"success": False, "message": f"获取购买单位列表失败：{str(e)}"}), 500

@app.route("/api/purchase_units", methods=["POST"])
def add_purchase_unit():
    """添加新的购买单位"""
    try:
        data = request.get_json()
        unit_name = data.get('unit_name', '').strip()
        contact_person = data.get('contact_person', '').strip()
        contact_phone = data.get('contact_phone', '').strip()
        address = data.get('address', '').strip()
        
        if not unit_name:
            return jsonify({"success": False, "message": "单位名称不能为空"}), 400
        
        # 检查单位是否已存在
        existing_unit = query_db("SELECT id FROM purchase_units WHERE unit_name = ? AND is_active = 1", [unit_name], fetch_one=True)
        if existing_unit:
            return jsonify({"success": False, "message": "购买单位已存在"}), 400
        
        # 插入新单位
        query_db("""
            INSERT INTO purchase_units (unit_name, contact_person, contact_phone, address, is_active, created_at)
            VALUES (?, ?, ?, ?, 1, datetime('now'))
        """, [unit_name, contact_person, contact_phone, address])
        
        # 获取新插入的单位ID
        new_unit_id = query_db("SELECT last_insert_rowid() as id", fetch_one=True)["id"]
        
        return jsonify({
            "success": True,
            "message": "购买单位添加成功",
            "unit_id": new_unit_id
        })
        
    except Exception as e:
        logger.error(f"添加购买单位失败: {e}")
        return jsonify({"success": False, "message": f"添加购买单位失败：{str(e)}"}), 500

@app.route("/api/purchase_units/<int:unit_id>", methods=["DELETE"])
def delete_purchase_unit(unit_id):
    """删除购买单位（软删除）"""
    try:
        # 检查单位是否存在
        existing_unit = query_db("SELECT id, unit_name FROM purchase_units WHERE id = ? AND is_active = 1", [unit_id], fetch_one=True)
        if not existing_unit:
            return jsonify({"success": False, "message": "购买单位不存在"}), 404
        
        # 软删除
        query_db("UPDATE purchase_units SET is_active = 0, updated_at = datetime('now') WHERE id = ?", [unit_id])
        
        return jsonify({
            "success": True,
            "message": f"购买单位 '{existing_unit['unit_name']}' 删除成功"
        })
        
    except Exception as e:
        logger.error(f"删除购买单位失败: {e}")
        return jsonify({"success": False, "message": f"删除购买单位失败：{str(e)}"}), 500

@app.route("/api/purchase_units/<int:unit_id>", methods=["PUT"])
def update_purchase_unit(unit_id):
    """更新购买单位信息"""
    try:
        data = request.get_json()
        unit_name = data.get('unit_name', '').strip()
        contact_person = data.get('contact_person', '').strip()
        contact_phone = data.get('contact_phone', '').strip()
        address = data.get('address', '').strip()
        
        if not unit_name:
            return jsonify({"success": False, "message": "单位名称不能为空"}), 400
        
        # 检查单位是否存在
        existing_unit = query_db("SELECT id, unit_name FROM purchase_units WHERE id = ? AND is_active = 1", [unit_id], fetch_one=True)
        if not existing_unit:
            return jsonify({"success": False, "message": "购买单位不存在"}), 404
        
        # 检查单位名称是否与其他单位重复
        name_conflict = query_db("SELECT id FROM purchase_units WHERE unit_name = ? AND id != ? AND is_active = 1", [unit_name, unit_id], fetch_one=True)
        if name_conflict:
            return jsonify({"success": False, "message": "单位名称已存在"}), 400
        
        # 更新单位信息
        query_db("""
            UPDATE purchase_units 
            SET unit_name = ?, contact_person = ?, contact_phone = ?, address = ?, updated_at = datetime('now')
            WHERE id = ?
        """, [unit_name, contact_person, contact_phone, address, unit_id])
        
        return jsonify({
            "success": True,
            "message": "购买单位更新成功"
        })
        
    except Exception as e:
        logger.error(f"更新购买单位失败: {e}")
        return jsonify({"success": False, "message": f"更新购买单位失败：{str(e)}"}), 500

@app.route("/api/purchase_units/by_name/<unit_name>", methods=["GET"])
def get_purchase_unit_by_name(unit_name):
    """根据名称获取购买单位"""
    try:
        unit = query_db("SELECT * FROM purchase_units WHERE unit_name = ? AND is_active = 1", [unit_name], fetch_one=True)
        
        if unit:
            result = {
                "id": unit["id"],
                "unit_name": unit["unit_name"],
                "contact_person": unit["contact_person"] if unit["contact_person"] else "",
                "contact_phone": unit["contact_phone"] if unit["contact_phone"] else "",
                "address": unit["address"] if unit["address"] else ""
            }
            return jsonify({"success": True, "data": result})
        else:
            return jsonify({"success": False, "message": "购买单位不存在"}), 404
    except Exception as e:
        logger.error(f"获取购买单位信息失败: {e}")
        return jsonify({"success": False, "message": f"服务器错误: {str(e)}"}), 500

# ==================== 产品管理API ====================

@app.route("/api/products", methods=["GET"])
def get_products():
    """获取产品列表（支持单位参数）"""
    try:
        unit = request.args.get('unit', '').strip()
        
        if unit:
            # 从单位数据库获取产品
            import os
            import urllib.parse
            
            # 解码URL编码的单位名称
            unit = urllib.parse.unquote(unit)
            
            # 构建数据库路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(current_dir, 'unit_databases', f'{unit}.db')
            
            if not os.path.exists(db_path):
                return jsonify({"success": False, "message": f"单位数据库不存在: {unit}"}), 404
            
            # 连接数据库
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 检查products表是否存在
            cursor.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="products"')
            if not cursor.fetchone():
                conn.close()
                return jsonify({"success": False, "message": f"单位数据库中不存在products表: {unit}"}), 404
            
            # 查询产品
            cursor.execute('''
                SELECT id, model_number, name, specification, price, quantity, description
                FROM products 
                ORDER BY name
            ''')
            products = cursor.fetchall()
            conn.close()
            
            # 处理结果
            result = []
            for product in products:
                result.append({
                    "id": product[0],
                    "name": product[2],
                    "model_number": product[1] if product[1] else "",
                    "specification": product[3] if product[3] else "",
                    "price": float(product[4]) if product[4] else 0.0,
                    "quantity": product[5] if product[5] else 1,
                    "description": product[6] if product[6] else ""
                })
        else:
            # 从主数据库获取产品
            products = query_db('''
                SELECT id, model_number, name, specification, price, quantity, description
                FROM products 
                ORDER BY name
            ''')
            
            # 处理结果
            result = []
            for product in products:
                result.append({
                    "id": product["id"],
                    "name": product["name"],
                    "model_number": product["model_number"] if product["model_number"] else "",
                    "specification": product["specification"] if product["specification"] else "",
                    "price": float(product["price"]) if product["price"] else 0.0,
                    "quantity": product["quantity"] if product["quantity"] else 1,
                    "description": product["description"] if product["description"] else ""
                })
        
        return jsonify({
            "success": True,
            "data": result,
            "count": len(result)
        })
        
    except Exception as e:
        logger.error(f"获取产品列表失败: {e}")
        return jsonify({"success": False, "message": f"获取产品列表失败: {str(e)}"}), 500




# ==================== 产品名称管理API ====================

@app.route("/api/product_names", methods=["GET"])
def get_product_names():
    """获取产品名称列表"""
    try:
        # 获取所有单位的产品数据
        products = []
        
        # 从单位数据库读取产品
        units_dir = os.path.join(BASE_DIR, 'unit_databases')
        if os.path.exists(units_dir):
            db_files = glob.glob(os.path.join(units_dir, '*.db'))
            
            for db_path in db_files:
                unit_name = os.path.basename(db_path)[:-3]  # 移除 .db 后缀
                
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        SELECT id, model_number, name, price, specification, brand, unit
                        FROM products ORDER BY name
                    """)
                    unit_products = cursor.fetchall()
                    
                    for product in unit_products:
                        products.append({
                            "id": product[0],
                            "name": product[2] or "",
                            "model_number": product[1] or "",
                            "specification": product[4] or "",
                            "price": float(product[3]) if product[3] else 0.0,
                            "brand": product[5] or "",
                            "unit": product[6] or "",
                            "purchase_unit_name": unit_name,
                            "description": ""
                        })
                    
                    conn.close()
                except Exception as e:
                    logger.warning(f"读取单位数据库 {unit_name} 失败: {e}")
                    continue
        
        # 按产品名称排序
        products.sort(key=lambda x: x["name"])
        
        return jsonify({
            "success": True,
            "data": products,
            "count": len(products)
        })
        
    except Exception as e:
        logger.error(f"获取产品名称列表失败: {e}")
        return jsonify({"success": False, "message": f"获取产品列表失败: {str(e)}"}), 500

def get_unit_id_by_name(unit_name):
    """根据单位名称获取单位ID"""
    try:
        unit = query_db("SELECT id FROM purchase_units WHERE unit_name = ? AND is_active = 1", [unit_name], fetch_one=True)
        return unit["id"] if unit else None
    except:
        return None

@app.route("/api/product_names/by_unit/<int:unit_id>", methods=["GET"])
def get_product_names_by_unit(unit_id):
    """根据购买单位获取产品名称"""
    try:
        # 先获取单位名称
        unit = query_db("SELECT unit_name FROM purchase_units WHERE id = ? AND is_active = 1", [unit_id], fetch_one=True)
        if not unit:
            return jsonify({"success": False, "message": "单位不存在"}), 404
        
        unit_name = unit["unit_name"]
        
        # 从该单位的数据库获取产品
        units_dir = os.path.join(BASE_DIR, 'unit_databases')
        db_path = os.path.join(units_dir, f'{unit_name}.db')
        
        if not os.path.exists(db_path):
            return jsonify({"success": True, "data": [], "count": 0, "message": "未找到单位数据库"})
        
        # 连接单位数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, model_number, name, price, specification, brand, unit
            FROM products ORDER BY name
        """)
        unit_products = cursor.fetchall()
        
        conn.close()
        
        # 转换为前端需要的格式
        products = []
        for product in unit_products:
            products.append({
                "id": product[0],
                "name": product[2] or "",
                "model": product[1] or "",
                "price": float(product[3]) if product[3] else 0.0,
                "specification": product[4] or "",
                "brand": product[5] or "",
                "unit": product[6] or "",
                "purchase_unit": unit_name,
                "unit_id": unit_id
            })
        
        return jsonify({
            "success": True,
            "data": products,
            "count": len(products)
        })
        
    except Exception as e:
        logger.error(f"根据单位获取产品列表失败: {e}")
        return jsonify({"success": False, "message": f"获取产品列表失败: {str(e)}"}), 500

@app.route("/api/product_names/search", methods=["GET"])
def search_product_names():
    """搜索产品名称"""
    try:
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify({"success": True, "data": [], "count": 0})
        
        # 搜索产品名称或型号
        search_term = f"%{query}%"
        products = query_db("""
            SELECT * FROM products 
            WHERE name LIKE ? OR model_number LIKE ? 
            ORDER BY name
            LIMIT 20
        """, [search_term, search_term])
        
        if products:
            result = []
            for product in products:
                # 获取购买单位名称
                if product["purchase_unit_id"]:
                    unit = query_db(
                        "SELECT unit_name FROM purchase_units WHERE id = ?",
                        [product["purchase_unit_id"]],
                        fetch_one=True
                    )
                    purchase_unit_name = unit["unit_name"] if unit else ""
                else:
                    purchase_unit_name = ""
                
                result.append({
                    "id": product["id"],
                    "name": product["name"],
                    "model_number": product["model_number"] if product["model_number"] else "",
                    "specification": product["specification"] if product["specification"] else "",
                    "price": float(product["price"]) if product["price"] else 0.0,
                    "purchase_unit_name": purchase_unit_name,
                    "description": product["description"] if product["description"] else ""
                })
            return jsonify({
                "success": True,
                "data": result,
                "count": len(result)
            })
        else:
            return jsonify({
                "success": True,
                "data": [],
                "count": 0
            })
    
    except Exception as e:
        logger.error(f"搜索产品名称失败: {e}")
        return jsonify({"success": False, "message": f"搜索产品名称失败：{str(e)}"}), 500

@app.route("/api/product_names/by_unit_and_name", methods=["GET"])
def get_product_by_unit_and_name():
    """根据购买单位和产品名称获取产品"""
    try:
        unit_id = request.args.get('unit_id')
        product_name = request.args.get('name', '').strip()
        
        if not unit_id or not product_name:
            return jsonify({"success": False, "message": "缺少必要参数"})
        
        # 查询指定购买单位和产品名称的产品
        product = query_db("""
            SELECT * FROM products 
            WHERE purchase_unit_id = ? AND name = ?
            LIMIT 1
        """, [unit_id, product_name], fetch_one=True)
        
        if product:
            result = {
                "id": product["id"],
                "name": product["name"],
                "model_number": product["model_number"] if product["model_number"] else "",
                "specification": product["specification"] if product["specification"] else "",
                "price": float(product["price"]) if product["price"] else 0.0,
                "description": product["description"] if product["description"] else ""
            }
            return jsonify({
                "success": True,
                "data": result
            })
        else:
            return jsonify({"success": False, "message": "产品不存在"})
    
    except Exception as e:
        logger.error(f"根据购买单位和产品名称获取产品失败: {e}")
        return jsonify({"success": False, "message": f"获取产品失败：{str(e)}"}), 500

# ==================== 订单编号管理API ====================

@app.route("/orders/next_number", methods=["GET"])
def get_next_order_number():
    """获取下一个订单编号"""
    try:
        suffix = request.args.get('suffix', 'A')
        
        # 生成订单编号：26-01-00023A格式
        today = datetime.now()
        year = today.strftime("%y")
        month = today.strftime("%m")
        
        # 获取当前日期的最大序号
        sequence_pattern = f"{year}-{month}-%"
        max_sequence = query_db("""
            SELECT MAX(CAST(SUBSTR(order_number, 8, 5) AS INTEGER)) as max_seq
            FROM orders 
            WHERE order_number LIKE ?
        """, [sequence_pattern], fetch_one=True)
        
        # 处理查询失败的情况
        if max_sequence is None:
            next_sequence = 1
        else:
            next_sequence = (max_sequence["max_seq"] or 0) + 1
        order_number = f"{year}-{month}-{next_sequence:05d}{suffix}"
        
        return jsonify({
            "success": True,
            "data": {
                "order_number": order_number,
                "sequence": next_sequence,
                "year_month": f"{year}-{month}"
            }
        })
    
    except Exception as e:
        logger.error(f"获取订单编号失败: {e}")
        return jsonify({"success": False, "message": f"获取订单编号失败：{str(e)}"}), 500


# ==================== 订单管理API ====================

@app.route('/api/orders/purchase-units', methods=['GET'])
def get_order_purchase_units():
    """获取所有购买单位"""
    try:
        import sqlite3
        
        # 从products.db的purchase_units表获取购买单位
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        
        cursor.execute('SELECT unit_name FROM purchase_units WHERE is_active = 1 ORDER BY unit_name')
        units = [row[0] for row in cursor.fetchall() if row[0]]
        
        conn.close()
        
        return jsonify({
            "success": True,
            "data": units,
            "count": len(units)
        })
    except Exception as e:
        logger.error(f"获取购买单位失败: {e}")
        return jsonify({
            "success": False,
            "message": f"获取购买单位失败: {str(e)}"
        }), 500

@app.route('/api/orders/clear-shipment', methods=['POST'])
def clear_shipment_record():
    """清理指定购买单位的出货记录"""
    try:
        data = request.get_json()
        if not data or 'purchase_unit' not in data:
            return jsonify({
                "success": False,
                "message": "缺少购买单位参数"
            }), 400
        
        purchase_unit = data['purchase_unit']
        if not purchase_unit:
            return jsonify({
                "success": False,
                "message": "购买单位不能为空"
            }), 400
        
        # 从数据库中删除订单
        import sqlite3
        conn = sqlite3.connect(get_db_path())  # 使用products.db作为主要数据源
        cursor = conn.cursor()
        
        # 删除指定购买单位的订单
        cursor.execute('DELETE FROM orders WHERE purchase_unit = ?', (purchase_unit,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        # 清理对应的出货记录文件
        cleanup_success = cleanup_shipment_file(purchase_unit)
        
        return jsonify({
            "success": True,
            "message": f"成功清理 {purchase_unit} 的出货记录",
            "deleted_orders": deleted_count,
            "cleanup_file": cleanup_success
        })
        
    except Exception as e:
        logger.error(f"清理出货记录失败: {e}")
        return jsonify({
            "success": False,
            "message": f"清理出货记录失败: {str(e)}"
        }), 500

def cleanup_shipment_file(purchase_unit):
    """清理对应的出货记录文件"""
    try:
        import os
        import shutil
        
        # 构建出货记录文件路径
        base_dir = os.path.dirname(os.path.abspath(__file__))
        shipment_dir = os.path.join(base_dir, '..', '出货记录')
        template_file = os.path.join(shipment_dir, '出货记录模板.xlsx')
        
        # 查找对应的客户文件夹
        client_dir = None
        for item in os.listdir(shipment_dir):
            item_path = os.path.join(shipment_dir, item)
            if os.path.isdir(item_path) and item != '__pycache__':
                # 清理文件夹名称
                clean_folder_name = re.sub(r'[^\w\s]', '', item)
                clean_folder_name = clean_folder_name.strip()
                
                # 使用改进的精确匹配逻辑
                safe_purchase_unit = re.sub(r'[^\w\s]', '', purchase_unit)
                safe_purchase_unit = safe_purchase_unit.strip()
                
                # 收集所有候选匹配
                exact_matches = []
                partial_matches = []
                
                # 精确匹配（优先）
                if safe_purchase_unit == clean_folder_name:
                    exact_matches.append(item_path)
                    logger.info(f"找到精确匹配文件夹: {item}")
                
                # 部分匹配 - 只匹配包含完整单位名称的文件夹，避免混淆
                elif safe_purchase_unit in clean_folder_name:
                    # 避免子串混淆：比如"蕊芯家私1"应该匹配"蕊芯家私1"或"蕊芯家私12"，但不应该匹配"蕊芯家私"
                    # 只有当文件夹名称长度 >= 选择单位名称长度时才认为是匹配
                    if len(clean_folder_name) >= len(safe_purchase_unit):
                        partial_matches.append(item_path)
                        logger.info(f"找到部分匹配文件夹: {item}")
                
                # 选择最佳匹配：优先精确匹配，否则选择最相似的部分匹配
                if exact_matches:
                    client_dir = exact_matches[0]
                    logger.info(f"使用精确匹配: {exact_matches[0]}")
                    break
                elif partial_matches:
                    # 优先选择包含完整单位名称的匹配
                    for path in partial_matches:
                        folder_name = re.sub(r'[^\w\s]', '', os.path.basename(path))
                        if safe_purchase_unit in folder_name:
                            client_dir = path
                            logger.info(f"使用优先部分匹配: {path}")
                            break
                    
                    if not client_dir:
                        client_dir = partial_matches[0]
                        logger.info(f"使用默认部分匹配: {client_dir}")
                    break
        
        if not client_dir:
            logger.warning(f"未找到购买单位 {purchase_unit} 对应的文件夹")
            return False
        
        # 查找Excel文件
        excel_files = []
        for file in os.listdir(client_dir):
            if file.endswith('.xlsx') and file != '出货记录模板.xlsx' and not file.startswith('~$'):
                excel_files.append(os.path.join(client_dir, file))
        
        if not excel_files:
            logger.warning(f"未找到购买单位 {purchase_unit} 的Excel文件")
            return False
        
        # 清理每个Excel文件
        success_count = 0
        for excel_file in excel_files:
            try:
                # 首先删除旧的备份文件（只保留最新一个）
                cleanup_old_backups(client_dir, excel_file)
                
                # 检查文件是否被占用，添加重试机制
                file_operation_success = False
                max_retries = 3
                
                for retry in range(max_retries):
                    try:
                        # 记录操作前的文件信息
                        file_size_before = os.path.getsize(excel_file) if os.path.exists(excel_file) else 0
                        logger.info(f"开始清理文件: {excel_file} (当前大小: {file_size_before} bytes)")
                        
                        # 先验证模板文件可用
                        if not os.path.exists(template_file):
                            raise FileNotFoundError(f"模板文件不存在: {template_file}")
                        
                        # 创建临时文件避免直接替换失败
                        import tempfile
                        temp_file = excel_file + '.tmp'
                        
                        # 复制模板到临时文件
                        shutil.copy2(template_file, temp_file)
                        logger.info(f"已创建临时文件: {temp_file}")
                        
                        # 备份原文件（带时间戳）
                        import time
                        timestamp = int(time.time())
                        backup_file = excel_file + f'.backup_{timestamp}'
                        if os.path.exists(excel_file):
                            shutil.copy2(excel_file, backup_file)
                            logger.info(f"已备份原文件: {backup_file}")
                        
                        # 原子性替换：先移动原文件，然后移动临时文件
                        if os.path.exists(excel_file):
                            os.remove(excel_file)
                        
                        shutil.move(temp_file, excel_file)
                        
                        # 验证替换结果
                        file_size_after = os.path.getsize(excel_file)
                        template_size = os.path.getsize(template_file)
                        
                        logger.info(f"文件清理完成: {excel_file}")
                        logger.info(f"  - 模板大小: {template_size} bytes")
                        logger.info(f"  - 替换后大小: {file_size_after} bytes")
                        logger.info(f"  - 大小匹配: {file_size_after == template_size}")
                        
                        file_operation_success = True
                        break
                        
                    except PermissionError as e:
                        if retry < max_retries - 1:
                            logger.warning(f"文件 {excel_file} 被占用，第 {retry + 1} 次重试...")
                            import time
                            time.sleep(1)  # 等待1秒后重试
                        else:
                            logger.error(f"文件 {excel_file} 仍被占用，清理失败: {e}")
                            break
                    
                    except FileNotFoundError as e:
                        logger.error(f"模板文件不存在: {e}")
                        break
                    
                    except Exception as e:
                        logger.error(f"文件操作失败 {excel_file}: {e}")
                        break
                
                if file_operation_success:
                    success_count += 1
                    logger.info(f"✅ 成功清理文件: {excel_file}")
                else:
                    logger.error(f"❌ 清理文件失败: {excel_file}")
                
            except Exception as e:
                logger.error(f"清理文件失败 {excel_file}: {e}")
        
        logger.info(f"文件清理结果: 成功 {success_count} 个文件，共 {len(excel_files)} 个文件")
        return success_count > 0
        
    except Exception as e:
        logger.error(f"清理出货记录文件失败: {e}")
        return False

def cleanup_old_backups(client_dir, excel_file):
    """清理旧的备份文件，只保留最新一个"""
    try:
        import glob
        
        # 获取文件名（不含路径和扩展名）
        base_name = os.path.basename(excel_file)
        name_without_ext = os.path.splitext(base_name)[0]
        
        # 查找所有相关的备份文件
        pattern = os.path.join(client_dir, f"{name_without_ext}.backup_*")
        backup_files = glob.glob(pattern)
        
        if len(backup_files) > 0:
            # 按时间排序，保留最新的一个
            backup_files.sort(key=os.path.getmtime)
            
            # 删除除最新外的所有备份文件
            for old_backup in backup_files[:-1]:
                try:
                    os.remove(old_backup)
                    logger.info(f"已删除旧备份文件: {old_backup}")
                except Exception as e:
                    logger.warning(f"删除旧备份文件失败 {old_backup}: {e}")
    
    except Exception as e:
        logger.warning(f"清理旧备份文件时出错: {e}")

@app.route('/api/orders', methods=['GET'])
def get_orders():
    """获取订单列表"""
    try:
        from order_manager import get_all_orders
        limit = request.args.get('limit', 100, type=int)
        
        orders = get_all_orders(limit)
        
        return jsonify({
            "success": True,
            "data": orders,
            "count": len(orders)
        })
        
    except Exception as e:
        logger.error(f"获取订单列表失败: {e}")
        return jsonify({"success": False, "message": f"获取订单列表失败：{str(e)}"}), 500

@app.route('/api/orders/search', methods=['GET'])
def search_orders():
    """搜索订单"""
    try:
        query = request.args.get('q', '').strip()
        
        if not query:
            return jsonify({"success": True, "data": [], "count": 0})
        
        from order_manager import search_orders
        orders = search_orders(query)
        
        return jsonify({
            "success": True,
            "data": orders,
            "count": len(orders)
        })
        
    except Exception as e:
        logger.error(f"搜索订单失败: {e}")
        return jsonify({"success": False, "message": f"搜索订单失败：{str(e)}"}), 500

@app.route('/api/orders/<order_number>', methods=['GET'])
def get_order_by_number(order_number):
    """根据订单编号获取订单详情"""
    try:
        from order_manager import get_order_by_number
        order = get_order_by_number(order_number)
        
        if order:
            return jsonify({
                "success": True,
                "data": order
            })
        else:
            return jsonify({"success": False, "message": "订单不存在"}), 404
        
    except Exception as e:
        logger.error(f"获取订单详情失败: {e}")
        return jsonify({"success": False, "message": f"获取订单详情失败：{str(e)}"}), 500


@app.route('/api/orders/<int:order_id>/update-number', methods=['POST'])
def update_order_number(order_id):
    """更新订单编号"""
    try:
        from order_manager import update_order_number
        
        data = request.get_json()
        new_order_number = data.get('new_order_number', '').strip()
        
        if not new_order_number:
            return jsonify({"success": False, "message": "请提供新的订单编号"}), 400
        
        success = update_order_number(order_id, new_order_number)
        
        if success:
            return jsonify({
                "success": True,
                "message": "订单编号更新成功",
                "data": {
                    "order_id": order_id,
                    "new_order_number": new_order_number
                }
            })
        else:
            return jsonify({"success": False, "message": "订单编号更新失败，可能是订单编号已存在"}), 400
        
    except Exception as e:
        logger.error(f"更新订单编号失败: {e}")
        return jsonify({"success": False, "message": f"更新订单编号失败：{str(e)}"}), 500


@app.route('/api/orders/latest', methods=['GET'])
@login_required
def get_latest_order_info():
    """获取最新的订单编号信息"""
    try:
        import sqlite3
        from datetime import datetime
        
        # 连接到数据库
        conn = sqlite3.connect(get_db_path())  # 使用products.db作为主要数据源
        cursor = conn.cursor()
        
        # 获取最新的订单
        cursor.execute("""
            SELECT order_number, created_at FROM orders 
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        latest_order = cursor.fetchone()
        conn.close()
        
        # 生成当前年月和序列
        today = datetime.now()
        year = today.strftime("%y")
        month = today.strftime("%m")
        year_month = f"{year}-{month}"
        
        if latest_order:
            latest_order_number = latest_order[0]
            parts = latest_order_number.split('-')
            if len(parts) >= 3:
                sequence_match = parts[2].split('A')[0]
                sequence = int(sequence_match) if sequence_match.isdigit() else 1
            else:
                sequence = 1
        else:
            latest_order_number = f"{year}-{month}-00001A"
            sequence = 1
        
        # 计算下一个序列
        next_sequence = sequence + 1
        next_order_number = f"{year}-{month}-{next_sequence:05d}A"
        
        return jsonify({
            "success": True,
            "data": {
                "order_number": latest_order_number,
                "next_order_number": next_order_number,
                "sequence": sequence,
                "next_sequence": next_sequence,
                "year_month": year_month
            }
        })
    
    except Exception as e:
        import traceback
        logger.error(f"获取最新订单信息失败: {e}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        return jsonify({"success": False, "message": f"获取最新订单信息失败：{str(e)}"}), 500


@app.route('/api/orders/set-sequence', methods=['POST'])
@login_required
def set_order_sequence():
    """设置订单编号序列"""
    try:
        import sqlite3
        from datetime import datetime
        import re
        
        data = request.get_json()
        new_number = data.get('order_number', '').strip()
        
        if not new_number:
            return jsonify({"success": False, "message": "请输入订单编号"}), 400
        
        pattern = r'^\d{2}-\d{2}-\d{5}[A-Za-z]$'
        if not re.match(pattern, new_number):
            return jsonify({"success": False, "message": "订单编号格式不正确，应为：年份-月份-五位序列号+字母（如26-02-00001A）"}), 400
        
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM orders WHERE order_number = ?", (new_number,))
        if cursor.fetchone():
            conn.close()
            return jsonify({"success": False, "message": f"订单编号 {new_number} 已存在，请使用其他编号"}), 400
        
        cursor.execute("""
            SELECT order_number FROM orders 
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        latest_order = cursor.fetchone()
        
        if latest_order:
            cursor.execute("""
                INSERT INTO orders (order_number, purchase_unit, total_amount, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
            """, (new_number, '编号调整记录', 0, 'adjustment'))
            conn.commit()
        
        conn.close()
        
        parts = new_number.split('-')
        if len(parts) >= 3:
            sequence_match = parts[2].split('A')[0].split('a')[0]
            sequence = int(sequence_match) if sequence_match.isdigit() else 1
        else:
            sequence = 1
        
        today = datetime.now()
        year = today.strftime("%y")
        month = today.strftime("%m")
        next_sequence = sequence + 1
        next_order_number = f"{year}-{month}-{next_sequence:05d}A"
        
        return jsonify({
            "success": True,
            "message": f"订单编号已设置为 {new_number}",
            "data": {
                "order_number": new_number,
                "next_order_number": next_order_number,
                "sequence": sequence,
                "next_sequence": next_sequence,
                "year_month": f"{year}-{month}"
            }
        })
    
    except Exception as e:
        logger.error(f"设置订单编号失败: {e}")
        return jsonify({"success": False, "message": f"设置订单编号失败：{str(e)}"}), 500


@app.route('/api/orders/reset-sequence', methods=['POST'])
@login_required
def reset_order_sequence():
    """重置订单编号序列"""
    try:
        import sqlite3
        from datetime import datetime
        
        today = datetime.now()
        year = today.strftime("%y")
        month = today.strftime("%m")
        
        new_number = f"{year}-{month}-00000A"
        
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        
        # 检查是否已存在该订单号
        cursor.execute("SELECT id FROM orders WHERE order_number = ?", (new_number,))
        existing = cursor.fetchone()
        
        if not existing:
            # 不存在则插入重置记录
            cursor.execute("""
                INSERT INTO orders (order_number, purchase_unit, total_amount, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
            """, (new_number, '编号重置记录', 0, 'reset'))
            conn.commit()
        
        conn.close()
        
        next_order_number = f"{year}-{month}-00001A"
        
        return jsonify({
            "success": True,
            "message": "订单编号已重置",
            "data": {
                "order_number": new_number,
                "next_order_number": next_order_number,
                "sequence": 0,
                "next_sequence": 1,
                "year_month": f"{year}-{month}"
            }
        })
    
    except Exception as e:
        logger.error(f"重置订单编号失败: {e}")
        return jsonify({"success": False, "message": f"重置订单编号失败：{str(e)}"}), 500


@app.route('/')
def index():
    """首页"""
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/integrated')
def integrated():
    """集成发货单页面"""
    return send_from_directory(os.path.join(BASE_DIR, 'templates'), 'integrated.html')


@app.route('/order-query')
def order_query():
    """订单查询管理页面"""
    return send_from_directory(BASE_DIR, 'order_query.html')

@app.route('/show-app-demo')
def show_app_demo():
    """PDF打印显示应用窗口演示页面"""
    return send_from_directory(os.path.join(BASE_DIR, 'templates'), 'show_app_demo.html')

@app.route('/templates')
def templates_page():
    """模板管理页面或模板列表API"""
    # 检查URL参数 - 如果有action=api参数，说明是API请求
    if request.args.get('action') == 'api' or \
        request.headers.get('Accept', '').find('application/json') != -1 or \
        request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # 返回模板列表JSON
        logger.info(f"检测到API请求，Accept头: {request.headers.get('Accept')}")
        return get_templates_list()
    else:
        # 返回HTML页面
        logger.info(f"检测到页面请求，URL: {request.url}")
        return send_from_directory(os.path.join(BASE_DIR, 'templates'), 'edit_template.html')

def get_templates_list():
    """获取模板列表的辅助函数"""
    try:
        # 获取当前目录下的xlsx文件
        templates = []
        for file in os.listdir(BASE_DIR):
            if file.endswith('.xlsx') and not file.startswith('~'):
                templates.append({"name": file, "filename": file})
        
        logger.info(f"加载模板列表: {templates}")
        return jsonify({"success": True, "templates": templates})
        
    except Exception as e:
        logger.error(f"获取模板列表错误: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"获取模板列表失败: {str(e)}"}), 500


# 动态打印机获取工具函数
def get_document_printer():
    """
    获取发货单打印机
    
    Returns:
        str: 发货单打印机名称，如果未找到则返回None
    """
    try:
        printers = get_printers()
        logger.info(f"检查 {len(printers)} 个可用打印机...")
        
        # 识别发货单打印机（通常是点阵打印机）
        for printer in printers:
            printer_name = printer.get('name', '').lower()
            
            # 识别发货单打印机关键词
            if any(keyword in printer_name for keyword in ['joli', '24-pin', 'dot matrix', 'impact', 'lq', '针式']):
                logger.info(f"✅ 找到发货单打印机: {printer.get('name')}")
                return printer.get('name')
        
        # 如果没有自动识别，排除TSC TTP-244等条码打印机，寻找其他打印机
        suitable_printers = []
        for printer in printers:
            printer_name = printer.get('name', '').lower()
            
            # 排除条码/标签打印机
            if not any(exclude_keyword in printer_name for exclude_keyword in ['tsc', 'ttp', 'label', '标签', 'thermal', 'barcode', '条码', 'zebra']):
                suitable_printers.append(printer)
        
        if suitable_printers:
            # 选择第一个非条码打印机作为发货单打印机
            selected_printer = suitable_printers[0].get('name')
            logger.warning(f"⚠️ 未找到专用发货单打印机，选择非条码打印机: {selected_printer}")
            logger.info("建议配置专用发货单打印机以避免混淆")
            return selected_printer
        
        # 如果仍然没有找到合适的打印机
        logger.error("❌ 未找到合适的发货单打印机")
        logger.error("   请确保系统中安装了点阵打印机，或在设置中手动指定发货单打印机")
        
        # 尝试提供一个诊断信息
        logger.info("可用的打印机列表:")
        for i, printer in enumerate(printers, 1):
            printer_name = printer.get('name', '')
            printer_type = "条码/标签打印机" if any(keyword in printer_name.lower() for keyword in ['tsc', 'ttp', 'label', '条码']) else "可能适合发货单"
            logger.info(f"   {i}. {printer_name} ({printer_type})")
        
        return None
        
    except Exception as e:
        logger.error(f"获取发货单打印机失败: {e}")
        return None


def get_label_printer():
    """
    获取标签打印机
    
    Returns:
        str: 标签打印机名称，如果未找到则返回None
    """
    try:
        printers = get_printers()
        
        # 首先尝试获取标签打印机
        label_printer = None
        for printer in printers:
            printer_name = printer.get('name', '').lower()
            
            # 识别标签打印机关键词
            if any(keyword in printer_name for keyword in ['tsc', 'ttp', 'label', '标签', 'thermal', 'barcode']):
                label_printer = printer.get('name')
                logger.info(f"✅ 找到标签打印机: {label_printer}")
                break
        
        # 如果找到了标签打印机，检查是否与发货单打印机冲突
        if label_printer:
            doc_printer = get_document_printer()
            if doc_printer and label_printer == doc_printer:
                logger.error("❌ 标签打印机与发货单打印机相同！")
                logger.error(f"   发货单打印机: {doc_printer}")
                logger.error(f"   标签打印机: {label_printer}")
                logger.error("请检查打印机配置，确保两种类型的打印机不同")
                return None
            return label_printer
        
        # 如果没有TSC，使用第二个可用打印机
        if len(printers) >= 2:
            # 排除第一个作为发货单打印机，尝试使用第二个
            available_printers = [p for p in printers if p.get('name') != get_document_printer()]
            if len(available_printers) >= 2:
                selected = available_printers[1].get('name')
                logger.warning(f"未找到TSC标签打印机，使用第二个可用打印机: {selected}")
                return selected
        
        logger.error("❌ 未找到合适的标签打印机")
        return None
        
    except Exception as e:
        logger.error(f"获取标签打印机失败: {e}")
        return None


def get_printer_queue(printer_name):
    """
    获取指定打印机的队列
    
    Args:
        printer_name: 打印机名称
        
    Returns:
        list: 打印作业列表
    """
    try:
        import win32print
        hPrinter = win32print.OpenPrinter(printer_name)
        jobs = win32print.EnumJobs(hPrinter, 0, -1, 1)
        win32print.ClosePrinter(hPrinter)
        return jobs
    except Exception as e:
        logger.error(f"获取打印机 {printer_name} 队列失败: {e}")
        return []


def validate_printer_separation():
    """
    验证发货单和标签打印机分离性
    
    Returns:
        dict: 验证结果 {'valid': bool, 'doc_printer': str, 'label_printer': str, 'error': str}
    """
    try:
        doc_printer = get_document_printer()
        label_printer = get_label_printer()
        
        if not doc_printer:
            return {
                'valid': False,
                'doc_printer': None,
                'label_printer': label_printer,
                'error': '发货单打印机未配置'
            }
        
        if not label_printer:
            return {
                'valid': False,
                'doc_printer': doc_printer,
                'label_printer': None,
                'error': '标签打印机未配置'
            }
        
        if doc_printer == label_printer:
            return {
                'valid': False,
                'doc_printer': doc_printer,
                'label_printer': label_printer,
                'error': f'发货单打印机和标签打印机相同: {doc_printer}'
            }
        
        return {
            'valid': True,
            'doc_printer': doc_printer,
            'label_printer': label_printer,
            'error': None
        }
        
    except Exception as e:
        return {
            'valid': False,
            'doc_printer': None,
            'label_printer': None,
            'error': f'打印机验证失败: {str(e)}'
        }


@app.route('/api/print/diagnose', methods=['GET'])
def diagnose_printers():
    """
    打印机诊断API
    GET /api/print/diagnose
    """
    try:
        logger.info("🔍 开始打印机诊断...")
        
        # 获取所有打印机
        printers = get_printers()
        diagnostic_info = {
            'total_printers': len(printers),
            'printers': [],
            'validation': validate_printer_separation(),
            'recommendations': []
        }
        
        # 分析每个打印机
        for i, printer in enumerate(printers, 1):
            printer_name = printer.get('name', '')
            printer_info = {
                'name': printer_name,
                'index': i,
                'type': '未知',
                'suitable_for': [],
                'conflicts': []
            }
            
            # 识别打印机类型
            printer_name_lower = printer_name.lower()
            if any(keyword in printer_name_lower for keyword in ['tsc', 'ttp', 'label', '标签', 'thermal', 'barcode']):
                printer_info['type'] = '条码/标签打印机'
                printer_info['suitable_for'].append('标签打印')
            elif any(keyword in printer_name_lower for keyword in ['joli', '24-pin', 'dot matrix', 'impact', 'lq', '针式']):
                printer_info['type'] = '点阵/发货单打印机'
                printer_info['suitable_for'].append('发货单打印')
            else:
                printer_info['type'] = '通用打印机'
                printer_info['suitable_for'].append('发货单打印')
                printer_info['suitable_for'].append('标签打印（需要确认）')
            
            diagnostic_info['printers'].append(printer_info)
        
        # 生成建议
        validation = diagnostic_info['validation']
        if not validation['valid']:
            diagnostic_info['recommendations'].append({
                'type': 'error',
                'message': validation['error'],
                'solution': '请检查打印机配置，确保发货单打印机和标签打印机不同'
            })
        
        # 检查打印机数量
        if len(printers) == 1:
            diagnostic_info['recommendations'].append({
                'type': 'warning',
                'message': '系统中只有1台打印机',
                'solution': '建议安装独立的标签打印机或设置手动打印模式'
            })
        elif len(printers) == 0:
            diagnostic_info['recommendations'].append({
                'type': 'error',
                'message': '未检测到任何打印机',
                'solution': '请确保打印机已正确连接并安装驱动程序'
            })
        
        # 检查专用打印机配置
        has_doc_printer = any(p['type'] == '点阵/发货单打印机' for p in diagnostic_info['printers'])
        has_label_printer = any(p['type'] == '条码/标签打印机' for p in diagnostic_info['printers'])
        
        if not has_doc_printer:
            diagnostic_info['recommendations'].append({
                'type': 'warning',
                'message': '未检测到专用发货单打印机',
                'solution': '建议使用点阵打印机打印发货单，激光/喷墨打印机打印标签'
            })
        
        if not has_label_printer:
            diagnostic_info['recommendations'].append({
                'type': 'warning',
                'message': '未检测到专用标签打印机',
                'solution': '建议使用TSC TTP-244 Plus等条码打印机打印标签'
            })
        
        logger.info("✅ 打印机诊断完成")
        return jsonify({
            'success': True,
            'diagnostic': diagnostic_info
        })
        
    except Exception as e:
        logger.error(f"打印机诊断失败: {e}")
        return jsonify({
            'success': False,
            'message': f'打印机诊断失败: {str(e)}'
        }), 500


@app.route('/api/generate', methods=['POST'])
@login_required
def generate_document():
    """
    生成发货单API
    POST /api/generate
    {"order_text": "订单文本", "template_name": "模板名称", "custom_mode": false, "number_mode": false, "excel_sync": false, "excel_file_path": "可选的自定义Excel文件路径"}
    """
    try:
        app.logger.info("DEBUG: generate_document 函数开始执行")
        # 获取请求数据
        data = request.get_json()
        order_text = data.get('order_text', '').strip()
        template_name = data.get('template_name', '尹玉华1.xlsx')
        custom_mode = data.get('custom_mode', False)
        number_mode = data.get('number_mode', False)
        excel_sync = data.get('excel_sync', False)
        excel_file_path = data.get('excel_file_path', None)
        auto_print = data.get('auto_print', False)  # 获取自动打印设置
        
        if not order_text:
            return jsonify({"success": False, "message": "请输入订单信息"}), 400
        
        logger.info(f"开始生成发货单，订单文本: {order_text[:50]}..., 自定义模式: {custom_mode}, 编号模式: {number_mode}, Excel同步: {excel_sync}, 自动打印: {auto_print}")
        
        # Excel同步将在解析完成后根据购买单位自动执行
        
        # ========== 学习样板预处理 ==========
        logger.info("🚀 开始学习样板预处理")
        original_text = order_text
        applied_corrections = []
        if voice_db:
            logger.info(f"✅ voice_db 存在，开始处理")
            try:
                # 获取所有学习样板
                all_samples = voice_db.get_all_samples()
                logger.info(f"获取到 {len(all_samples)} 个学习样板")
                corrections_applied = 0
                
                for sample in all_samples:
                    wrong_input = sample['wrong_input']
                    correct_output = sample['correct_output']
                    
                    # 检查错误文本是否在订单文本中
                    if wrong_input in order_text:
                        logger.info(f"发现匹配: '{wrong_input}' → '{correct_output}'")
                        # 计算相似度（改进的相似度计算）
                        wrong_len = len(wrong_input)
                        total_len = len(order_text)
                        # 简单相似度：错误文本长度 / 总文本长度
                        similarity = wrong_len / total_len if total_len > 0 else 0.0
                        
                        logger.info(f"相似度计算: {wrong_len}/{total_len} = {similarity:.3f}")
                        
                        # 修复：降低阈值或者直接应用匹配（因为已经有了匹配）
                        if similarity >= 0.05 or len(wrong_input) >= 2:  # 降低阈值，增加灵活性
                            logger.info(f"✅ 应用纠正: '{wrong_input}' → '{correct_output}' (相似度: {similarity:.3f})")
                            order_text = order_text.replace(wrong_input, correct_output)
                            applied_corrections.append({
                                "original": wrong_input,
                                "corrected": correct_output,
                                "confidence": min(similarity, 0.95)  # 最大置信度0.95
                            })
                            corrections_applied += 1
                            
                            # 记录应用
                            voice_db.apply_sample(sample['id'], wrong_input, correct_output, True, 
                                                f"主流程预处理应用 - 原始文本: {original_text}")
                        else:
                            logger.info(f"❌ 相似度太低，跳过: {similarity:.3f}")
                    else:
                        logger.info(f"❌ 未匹配: '{wrong_input}' 不在 '{order_text}' 中")
                
                if applied_corrections:
                    logger.info(f"学习样板预处理应用了 {len(applied_corrections)} 个纠正")
                else:
                    logger.info("学习样板预处理未应用任何纠正")
                    
            except Exception as e:
                logger.warning(f"学习样板预处理失败: {e}")
        else:
            logger.warning("voice_db 未初始化，跳过学习样板预处理")
        # ========== 学习样板预处理结束 ==========
        
        # 调用文档生成器（先不启用同步，因为需要先根据购买单位加载文件）
        result = document_generator.parse_and_generate(
            order_text, 
            custom_mode=custom_mode, 
            number_mode=number_mode,
            enable_excel_sync=False  # 先不执行同步
        )
        
        if result['success']:
            app.logger.info("DEBUG: 发货单生成成功，开始执行标签生成逻辑")
            logger.info(f"发货单生成成功，文件名: {result['document']['filename']}")
            
            # 获取 order_id
            order_id = result.get('order_id')
            app.logger.info(f"DEBUG: 获取到 order_id = {order_id}")
            
            if order_id:
                pass  # 删除重复的标签生成逻辑
            
            # 如果启用了Excel同步，根据购买单位加载对应的出货记录文件
            if excel_sync and document_generator.excel_sync_manager:
                # 从解析结果中获取购买单位
                parsed_data = result.get('parsed_data', {})
                purchase_unit = parsed_data.get('purchase_unit', '')
                
                logger.info(f"购买单位: {purchase_unit}")
                
                # 使用改进的精确匹配逻辑查找对应的出货记录文件
                excel_sync_success = False
                if purchase_unit:
                    try:
                        # 使用改进的精确匹配逻辑
                        from shipment_excel_sync import find_shipment_record
                        shipment_file = find_shipment_record(purchase_unit)
                        
                        if shipment_file:
                            document_generator.excel_sync_manager.load_excel(shipment_file)
                            excel_sync_success = True
                            logger.info(f"使用改进匹配找到的出货记录文件: {shipment_file}")
                        else:
                            logger.warning(f"改进匹配未找到购买单位 {purchase_unit} 对应的文件")
                            # 回退到原来的方法
                            excel_sync_success = document_generator.excel_sync_manager.load_excel_by_unit(purchase_unit)
                            logger.info(f"回退使用原有匹配方法: {purchase_unit}")
                    except Exception as e:
                        logger.error(f"改进匹配失败，使用原有方法: {e}")
                        excel_sync_success = document_generator.excel_sync_manager.load_excel_by_unit(purchase_unit)
                
                # 如果没有找到购买单位或加载失败，尝试使用默认文件
                if not excel_sync_success and document_generator.excel_sync_enabled:
                    # 使用正确的默认路径
                    default_excel = os.path.join(os.path.dirname(__file__), '..', '出货记录', '七彩乐园', '七彩乐园.xlsx')
                    if os.path.exists(default_excel):
                        document_generator.excel_sync_manager.load_excel(default_excel)
                        excel_sync_success = True
                        logger.info(f"使用默认出货记录文件: {default_excel}")
                
                # 手动执行同步
                if excel_sync_success:
                    logger.info("🚀 开始同步到Excel出货记录...")
                    doc = result['document']
                    excel_sync_success = document_generator.sync_to_excel(doc, parsed_data)
                    logger.info(f"Excel同步结果: {excel_sync_success}")
                else:
                    logger.info("未找到对应的出货记录文件，跳过同步")
            
            # 自动生成产品标签
            order_id = result.get('order_id')
            logger.info(f"开始自动标签生成，order_id={order_id}")
            logger.info(f"📄 自动为订单 {order_id} 生成产品标签")
            
            # 创建商标导出目录（使用全局os）
            LABELS_EXPORT_DIR = os.path.join(BASE_DIR, '商标导出')
            os.makedirs(LABELS_EXPORT_DIR, exist_ok=True)
            logger.info(f"商标导出目录: {LABELS_EXPORT_DIR}")
            
            # 清除旧的商标文件
            logger.info("清除旧的商标文件...")
            
            # 先清理所有旧文件（包括PNG和PDF）
            for filename in os.listdir(LABELS_EXPORT_DIR):
                file_path = os.path.join(LABELS_EXPORT_DIR, filename)
                if os.path.isfile(file_path):
                    try:
                        os.remove(file_path)
                        logger.info(f"已删除旧文件: {filename}")
                    except Exception as e:
                        logger.warning(f"删除旧文件失败 {filename}: {e}")
            logger.info("旧文件清除完成")
            
            try:
                from order_manager import OrderManager
                from label_generator import ProductLabelGenerator
                from ratio_rules_manager_fixed import RatioRulesManager
                from datetime import datetime
                import uuid
                
                # 获取订单信息
                # 使用与 document_generator 相同的数据库路径
                db_path = document_generator.generator.db_path
                logger.info(f"使用数据库路径: {db_path}")
                order_manager = OrderManager(db_path)
                order = order_manager.get_order_by_id(order_id)
                logger.info(f"获取订单结果: {order is not None}")
                
                if order:
                    logger.info(f"订单信息: {order}")
                    # 获取产品列表
                    products = order.get('products', [])
                    logger.info(f"产品列表: {products}")
                    logger.info(f"产品数量: {len(products)}")
                    if products:
                        # 生成当前日期
                        current_date = datetime.now().strftime('%Y.%m.%d')
                        
                        # 为每个产品生成标签
                        generated_labels = []
                        for i, product in enumerate(products):
                            # 准备产品数据
                            # 处理规格值，去掉.0
                            tin_spec = product.get('tin_spec', 10)
                            try:
                                if hasattr(tin_spec, 'is_integer') and tin_spec.is_integer():
                                    tin_spec = int(tin_spec)
                            except:
                                pass
                            
                            product_data = {
                                'product_number': product.get('model_number', '') or product.get('model', ''),
                                'product_name': product.get('name', '') or product.get('product_name', ''),
                                'ratio': '1:0.5-0.6:0.5-0.8',  # 默认配比
                                'production_date': current_date,
                                'shelf_life': '6个月',
                                'specification': product.get('specification', '') or f"{tin_spec}±0.1KG",
                                'inspector': '合格'
                            }
                            
                            # 验证必需字段
                            if product_data['product_number'] and product_data['product_name']:
                                # 检查产品名称是否包含"剂"或"料"
                                contains_ji_or_liao = any(keyword in product_data['product_name'] for keyword in ['剂', '料'])
                                
                                # 如果不包含"剂"或"料"，则尝试匹配参考配比
                                if not contains_ji_or_liao:
                                    matched_ratio = ratio_manager.match_ratio_by_product_name(product_data['product_name'])
                                    if matched_ratio:
                                        product_data['ratio'] = matched_ratio
                                        logger.info(f"为产品 '{product_data['product_name']}' 匹配到参考配比: {matched_ratio}")
                                
                                # 生成唯一文件名
                                filename = f"label_{order.get('order_number', 'unknown')}_{i+1}_{uuid.uuid4().hex}.png"
                                output_path = os.path.join(LABELS_EXPORT_DIR, filename)
                                
                                # 生成标签
                                generator = ProductLabelGenerator()
                                generator.generate_label(product_data, output_path)
                                
                                # 生成访问URL
                                image_url = f"/商标导出/{filename}"
                                
                                generated_labels.append({
                                    'product_name': product_data['product_name'],
                                    'model_number': product_data['product_number'],
                                    'filename': filename,
                                    'file_path': output_path,
                                    'image_url': f"/商标导出/{filename}"
                                })
                        
                        if generated_labels:
                            logger.info(f"✅ 成功为订单 {order_id} 生成 {len(generated_labels)} 个产品标签")
                            # 将标签信息添加到结果中
                            result['labels'] = generated_labels
                            result['label_export_dir'] = LABELS_EXPORT_DIR
                            
                            # =================== 自动打印发货单和标签 ===================
                            if auto_print:
                                logger.info("🚀 开始自动打印发货单和标签...")
                                
                                # 导入必要的模块
                                import win32api
                                import win32gui
                                import win32con
                                import win32print
                                import subprocess
                                import time
                                
                                try:
                                    # ========== 1. 打印发货单（Excel）- 使用print_utils + WPS监控 ==========
                                    doc = result['document']
                                    # 使用 filepath 而不是 output_path
                                    doc_path = doc.get('filepath', '')
                                    if not doc_path:
                                        # 如果没有 filepath，尝试使用 filename 构建路径
                                        filename = doc.get('filename', '')
                                        if filename:
                                            doc_path = os.path.join(BASE_DIR, 'outputs', filename)
                                    logger.info(f"📄 准备打印发货单: {doc_path}")
                                    
                                    # 获取发货单打印机
                                    document_printer = get_document_printer()
                                    if not document_printer:
                                        logger.error("❌ 未找到发货单打印机")
                                        raise Exception("发货单打印机未配置")
                                    
                                    logger.info(f"📄 发货单打印机: {document_printer}")
                                    
                                    # 获取标签打印机
                                    label_printer = get_label_printer()
                                    if not label_printer:
                                        logger.warning("⚠️ 未找到标签打印机，将跳过标签打印")
                                    else:
                                        logger.info(f"🏷️ 标签打印机: {label_printer}")
                                    
                                    # 在打印前修改默认打印机
                                    logger.info("[发货单打印] 修改默认打印机...")
                                    original_printer = win32print.GetDefaultPrinter()
                                    logger.info(f"[发货单打印] 当前默认打印机: {original_printer}")
                                    if original_printer != document_printer:
                                        win32print.SetDefaultPrinter(document_printer)
                                        time.sleep(0.5)
                                        new_printer = win32print.GetDefaultPrinter()
                                        logger.info(f"[发货单打印] 修改后默认打印机: {new_printer}")
                                    
                                    print_doc_success = False
                                    
                                    if os.path.exists(doc_path):
                                        # 使用print_utils打印
                                        logger.info("📄 使用print_utils打印发货单...")
                                        from print_utils import print_document
                                        print_result = print_document(doc_path, document_printer, use_default_printer=False)
                                        
                                        if print_result.get('success', False):
                                            logger.info("✅ print_utils打印命令已发送")
                                            
                                            # 等待5秒让WPS完成打印
                                            logger.info("⏳ 等待5秒让WPS完成打印...")
                                            time.sleep(5)
                                            
                                            # 强制终止WPS进程
                                            logger.info("🛑 强制终止WPS进程...")
                                            try:
                                                import subprocess
                                                
                                                # WPS相关进程列表
                                                processes = [
                                                    "wps.exe", "et.exe", "wpp.exe",  # 主程序进程
                                                    "wpscloudsvr.exe", "wpsnotify.exe",  # 后台服务
                                                    "wpscenter.exe", "wpsapp.exe", "wpspro.exe",  # 其他可能的WPS进程
                                                    "ksolaunch.exe", "ksodemo.exe", "wpsscan.exe",  # 相关工具进程
                                                    "wpsunins.exe", "wpscrashreport.exe", "wpsupdatetask.exe"  # 更新和崩溃报告
                                                ]
                                                
                                                terminated_processes = []
                                                
                                                for proc in processes:
                                                    try:
                                                        taskkill_result = subprocess.run(
                                                            ["taskkill", "/IM", proc, "/F"],
                                                            capture_output=True,
                                                            text=True,
                                                            timeout=3
                                                        )
                                                        if taskkill_result.returncode == 0:
                                                            logger.info(f"✅ 已终止进程: {proc}")
                                                            terminated_processes.append(proc)
                                                    except:
                                                        pass  # 进程可能不存在，忽略错误
                                                
                                                if terminated_processes:
                                                    logger.info(f"成功终止 {len(terminated_processes)} 个WPS进程")
                                                
                                                # 等待3秒确保进程完全终止
                                                time.sleep(3)
                                                logger.info("✅ WPS进程清理完成")
                                                
                                            except Exception as e:
                                                logger.warning(f"终止WPS进程时出错: {e}")
                                            
                                            print_doc_success = True
                                            
                                            # 恢复发货单打印机为默认打印机
                                            logger.info("[发货单打印] 恢复发货单打印机为默认打印机...")
                                            win32print.SetDefaultPrinter(document_printer)
                                            time.sleep(0.5)
                                            new_printer = win32print.GetDefaultPrinter()
                                            logger.info(f"[发货单打印] 默认打印机已恢复为: {new_printer}")
                                                
                                        else:
                                            logger.warning(f"⚠️ print_utils打印失败: {print_result.get('message', '未知错误')}")
                                    else:
                                        logger.error(f"❌ 发货单文件不存在: {doc_path}")
                                    
                                    # ========== 2. 打印标签（发货单打印完成后） ==========
                                    labels_printed = 0
                                    label_print_result = "标签请手动打印"
                                    
                                    # 即使发货单打印失败，也尝试打印标签
                                    if True:  # 修改为总是执行标签打印
                                        # 发货单打印完成，切换到标签打印机
                                        try:
                                            logger.info("[打印机切换] 发货单打印完成，切换到标签打印机...")
                                            win32print.SetDefaultPrinter(label_printer)
                                            time.sleep(0.5)
                                            new_default = win32print.GetDefaultPrinter()
                                            logger.info(f"[打印机切换] 默认打印机已切换为: {new_default}")
                                        except Exception as e:
                                            logger.warning(f"[打印机切换] 切换到标签打印机失败: {e}")
                                        logger.info("🏷️ 发货单打印完成，开始打印标签...")
                                        
                                        try:
                                            # 获取订单号和产品信息
                                            doc_info = result.get('document', {})
                                            order_number = doc_info.get('order_number', '')
                                            order_id = result.get('order_id', '')
                                            
                                            # 获取产品名称列表
                                            product_names = []
                                            if order_id:
                                                try:
                                                    from order_manager import OrderManager
                                                    db_path = document_generator.generator.db_path
                                                    order_manager = OrderManager(db_path)
                                                    order = order_manager.get_order_by_id(order_id)
                                                    if order:
                                                        products = order.get('products', [])
                                                        for product in products:
                                                            product_name = product.get('name', '')
                                                            if product_name:
                                                                product_names.append(product_name)
                                                except Exception as e:
                                                    logger.error(f"获取订单产品信息失败: {e}")
                                            
                                            logger.info(f"产品名称列表: {product_names}")
                                            
                                            # 为每个产品单独生成PDF文件
                                            logger.info(f"📄 开始为订单 {order_number} 生成单独的PDF标签文件...")
                                            
                                            from convert_order_labels_to_pdf import convert_each_label_to_pdf
                                            labels_dir = os.path.join(BASE_DIR, '商标导出')
                                            label_pdfs = convert_each_label_to_pdf(order_number, product_names, labels_dir)
                                            
                                            # 提取PDF文件路径
                                            label_pdf_paths = [pdf_path for pdf_path, product_name in label_pdfs]
                                            
                                            if label_pdf_paths:
                                                logger.info(f"✅ 成功生成 {len(label_pdf_paths)} 个PDF标签文件")
                                                for pdf_path, product_name in label_pdfs:
                                                    logger.info(f"  - {os.path.basename(pdf_path)} -> {product_name}")
                                            
                                            if label_pdf_paths:
                                                logger.info(f"✅ 成功生成 {len(label_pdf_paths)} 个PDF标签文件")
                                                
                                                # 获取标签打印机
                                                if not label_printer:
                                                    label_printer = get_label_printer()
                                                if not label_printer:
                                                    logger.error("❌ 无法获取标签打印机")
                                                    label_print_result = "标签打印机未配置"
                                                else:
                                                    logger.info(f"标签打印机: {label_printer}")
                                                    
                                                    # 打印所有找到的标签PDF文件（每个产品打印2份）
                                                    total_printed = 0
                                                    print_results = []
                                                    
                                                    # 打印所有标签PDF（每个标签打印2次）
                                                    import special_trademark_print as stp
                                                    
                                                    for label_pdf_path in label_pdf_paths:
                                                        try:
                                                            # 切换到标签打印机
                                                            win32print.SetDefaultPrinter(label_printer)
                                                            time.sleep(0.5)
                                                            logger.info(f"已切换到标签打印机: {label_printer}")
                                                            
                                                            # 打印2次
                                                            logger.info(f"开始打印 {os.path.basename(label_pdf_path)} x2份")
                                                            
                                                            for copy in range(2):
                                                                logger.info(f"========== 开始第{copy+1}次打印 ==========")
                                                                logger.info(f"📄 打印标签第{copy+1}次: {os.path.basename(label_pdf_path)}")
                                                                
                                                                # 加载时间：打印前等待让打印机准备好
                                                                logger.info(f"⏳ 打印前加载等待 3 秒...")
                                                                time.sleep(3)
                                                                
                                                                # 调用打印函数
                                                                logger.info(f"调用 print_trademark_pdf...")
                                                                result = stp.print_trademark_pdf(label_pdf_path, label_printer, show_app=False)
                                                                logger.info(f"print_trademark_pdf 返回: {result}")
                                                                
                                                                if result.get('success'):
                                                                    logger.info(f"✅ 第{copy+1}次打印成功")
                                                                else:
                                                                    logger.error(f"❌ 第{copy+1}次打印失败: {result}")
                                                                
                                                                # 等待3秒再打印下一份（给打印机足够时间加载任务）
                                                                logger.info(f"等待3秒让打印机加载任务...")
                                                                time.sleep(3)
                                                            
                                                            logger.info(f"✅ 标签 {os.path.basename(label_pdf_path)} x2份全部打印完成")
                                                            total_printed += 2
                                                            print_results.append({
                                                                'file': os.path.basename(label_pdf_path),
                                                                'copies': 2,
                                                                'success': True
                                                            })
                                                        except Exception as e:
                                                            logger.error(f"❌ 标签打印失败: {os.path.basename(label_pdf_path)}, 错误: {e}")
                                                            print_results.append({
                                                                'file': os.path.basename(label_pdf_path),
                                                                'copies': 2,
                                                                'success': False,
                                                                'error': str(e)
                                                            })
                                                    
                                                    # 恢复发货单打印机（所有标签打印完成后）
                                                    original_printer = win32print.GetDefaultPrinter()
                                                    if original_printer != document_printer:
                                                        win32print.SetDefaultPrinter(document_printer)
                                                        time.sleep(0.5)
                                                        logger.info(f"[打印机切换] 默认打印机已恢复为: {document_printer}")
                                                    
                                                    # 标签打印完成后清除窗口（等待10秒）
                                                    if total_printed > 0:
                                                        logger.info("⏳ 等待10秒让PDF/WPS打印完成...")
                                                        time.sleep(10)
                                                        
                                                        # 终止WPS和PDF相关进程
                                                        logger.info("🛑 强制终止WPS和PDF相关进程...")
                                                        try:
                                                            import subprocess
                                                            # WPS和PDF相关进程列表
                                                            cleanup_processes = [
                                                                "wps.exe",  # WPS文字
                                                                "et.exe",  # WPS表格
                                                                "wpp.exe",  # WPS演示
                                                                "wpscloudsvr.exe",  # WPS云服务
                                                                "wpsnotify.exe",  # WPS通知
                                                                "wpscenter.exe",  # WPS中心
                                                                "WPSPDF.exe",  # WPS PDF
                                                                "AcroRd32.exe",  # Adobe Reader
                                                                "Acrobat.exe",   # Adobe Acrobat
                                                                "foxitreader.exe",  # Foxit Reader
                                                                "SumatraPDF.exe",  # Sumatra PDF
                                                            ]
                                                            
                                                            terminated = []
                                                            for proc in cleanup_processes:
                                                                try:
                                                                    kill_result = subprocess.run(
                                                                        ["taskkill", "/IM", proc, "/F"],
                                                                        capture_output=True,
                                                                        text=True,
                                                                        timeout=3
                                                                    )
                                                                    if kill_result.returncode == 0:
                                                                        terminated.append(proc)
                                                                        logger.info(f"✅ 已终止进程: {proc}")
                                                                except:
                                                                    pass
                                                            
                                                            if terminated:
                                                                logger.info(f"成功终止 {len(terminated)} 个进程")
                                                            else:
                                                                logger.info("未找到需要终止的进程")
                                                        except Exception as e:
                                                            logger.warning(f"终止进程时出错: {e}")
                                                    
                                                    if total_printed > 0:
                                                        logger.info(f"✅ 成功打印 {total_printed} 个标签文件")
                                                        label_print_result = f"成功打印 {total_printed} 个标签文件"
                                                        result['label_printing'] = {
                                                            'success': True,
                                                            'message': label_print_result,
                                                            'total_printed': total_printed,
                                                            'total_files': len(label_pdf_paths),
                                                            'printer': label_printer,
                                                            'details': print_results
                                                        }
                                                    else:
                                                        logger.error("❌ 所有标签打印失败")
                                                        label_print_result = "所有标签打印失败"
                                                        result['label_printing'] = {
                                                            'success': False,
                                                            'message': label_print_result,
                                                            'details': print_results
                                                        }
                                            else:
                                                logger.warning("⚠️ 未找到标签PDF文件，跳过标签打印")
                                                label_print_result = "未找到标签PDF文件"
                                                result['label_printing'] = {
                                                    'success': False,
                                                    'message': label_print_result
                                                }
                                            
                                        except Exception as e:
                                            logger.error(f"标签打印过程出错: {e}")
                                            label_print_result = f"标签打印出错: {str(e)}"
                                            result['label_printing'] = {
                                                'success': False,
                                                'message': label_print_result
                                            }
                                    else:
                                        logger.warning("⚠️ 发货单打印失败，跳过标签打印")
                                        label_print_result = "发货单打印失败，跳过标签打印"
                                    
                                    # ========== 3. 设置打印结果 ==========
                                    result['printing'] = {
                                        'document_printed': print_doc_success,
                                        'labels_printed': labels_printed,
                                        'total_products': len(products),
                                        'document_result': "发货单打印完成" if print_doc_success else "请手动处理发货单",
                                        'labels_result': label_print_result
                                    }
                                    
                                    logger.info("✅ 自动打印流程完成")
                                    
                                except Exception as e:
                                    logger.error(f"❌ 自动打印失败: {e}")
                                    result['printing'] = {
                                        'document_printed': False,
                                        'labels_printed': 0,
                                        'error': str(e)
                                    }
                            
                            else:
                                logger.info("⏭️ 跳过自动打印（前端未启用自动打印）")
                                total_labels_printed = 0
                                result['printing'] = {
                                    'document_printed': False,
                                    'labels_printed': 0,
                                    'total_products': len(products),
                                    'document_result': "跳过打印",
                                    'labels_result': "跳过打印"
                                }
                            
                            # ======================================================
                            
                        else:
                            logger.warning(f"⚠️ 为订单 {order_id} 生成标签失败：订单中没有有效的产品信息")
                    else:
                        logger.warning(f"⚠️ 为订单 {order_id} 生成标签失败：订单中没有产品")
                else:
                    logger.warning(f"⚠️ 为订单 {order_id} 生成标签失败：订单不存在")
            except Exception as e:
                logger.error(f"❌ 自动生成标签失败: {e}")
                import traceback
                logger.error(traceback.format_exc())
            
            # 标签打印已集成到自动打印流程中，在发货单打印完成后执行
            # 打印结果已在自动打印流程中设置
            
            return jsonify(result)
        else:
            logger.error(f"发货单生成失败: {result['message']}")
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"API错误: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"服务器内部错误: {str(e)}"}), 500

@app.route('/api/excel/sync/enable', methods=['POST'])
def enable_excel_sync():
    """
    启用Excel出货记录同步
    POST /api/excel/sync/enable
    {"excel_path": "Excel文件路径", "worksheet_name": "工作表名称(可选)"}
    """
    try:
        data = request.get_json()
        excel_path = data.get('excel_path', '').strip()
        worksheet_name = data.get('worksheet_name', '25出货')
        
        if not excel_path:
            return jsonify({"success": False, "message": "请提供Excel文件路径"}), 400
        
        # 启用Excel同步
        success = document_generator.enable_excel_sync(excel_path, worksheet_name)
        
        if success:
            return jsonify({
                "success": True, 
                "message": f"已启用Excel同步: {excel_path}",
                "excel_sync_enabled": True
            })
        else:
            return jsonify({"success": False, "message": "启用Excel同步失败"}), 500
            
    except Exception as e:
        logger.error(f"启用Excel同步失败: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"服务器内部错误: {str(e)}"}), 500

@app.route('/api/excel/sync/status', methods=['GET'])
def excel_sync_status():
    """获取Excel同步状态"""
    return jsonify({
        "success": True,
        "excel_sync_enabled": document_generator.excel_sync_enabled
    })

@app.route('/api/excel/sync/disable', methods=['POST'])
def disable_excel_sync():
    """禁用Excel出货记录同步"""
    document_generator.disable_excel_sync()
    return jsonify({
        "success": True,
        "message": "已禁用Excel同步",
        "excel_sync_enabled": False
    })

@app.route('/api/excel/sync/upload', methods=['POST'])
def upload_excel_sync():
    """
    上传Excel文件并启用同步
    POST /api/excel/sync/upload
    multipart/form-data: excel_file, worksheet_name
    """
    try:
        if 'excel_file' not in request.files:
            return jsonify({"success": False, "message": "请上传Excel文件"}), 400
        
        file = request.files['excel_file']
        worksheet_name = request.form.get('worksheet_name', '25出货')
        
        if file.filename == '':
            return jsonify({"success": False, "message": "请选择Excel文件"}), 400
        
        # 保存文件到临时目录
        import os
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp_excel')
        os.makedirs(temp_dir, exist_ok=True)
        
        # 生成文件名
        filename = f"shipment_record_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        file_path = os.path.join(temp_dir, filename)
        file.save(file_path)
        
        # 启用Excel同步
        success = document_generator.enable_excel_sync(file_path, worksheet_name)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"已启用Excel同步: {file.filename}",
                "excel_sync_enabled": True,
                "excel_path": file_path,
                "filename": file.filename
            })
        else:
            # 删除上传的文件
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({"success": False, "message": "启用Excel同步失败"}), 500
            
    except Exception as e:
        logger.error(f"上传Excel同步失败: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"服务器内部错误: {str(e)}"}), 500

@app.route('/api/excel/upload', methods=['POST'])
def upload_excel():
    """
    上传Excel文件进行分析
    POST /api/excel/upload
    multipart/form-data: excel_file
    """
    try:
        if 'excel_file' not in request.files:
            return jsonify({"success": False, "error": "请上传Excel文件"}), 400
        
        file = request.files['excel_file']
        
        if file.filename == '':
            return jsonify({"success": False, "error": "请选择Excel文件"}), 400
        
        # 验证文件类型
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({"success": False, "error": "只支持 .xlsx 和 .xls 格式的Excel文件"}), 400
        
        # 保存文件到临时目录
        import os
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp_excel')
        os.makedirs(temp_dir, exist_ok=True)
        
        # 生成文件名
        filename = f"excel_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        file_path = os.path.join(temp_dir, filename)
        file.save(file_path)
        
        logger.info(f"Excel文件已上传: {file_path}")
        
        return jsonify({
            "success": True,
            "file_path": file_path,
            "workbook_name": file.filename,
            "message": "文件上传成功"
        })
        
    except Exception as e:
        logger.error(f"上传Excel文件失败: {e}", exc_info=True)
        return jsonify({"success": False, "error": f"服务器内部错误: {str(e)}"}), 500

@app.route('/api/optimize_voice', methods=['POST'])
def optimize_voice():
    """
    AI优化语音识别结果API
    POST /api/optimize_voice
    {"voice_text": "语音识别文本"}
    """
    try:
        # 获取请求数据
        data = request.get_json()
        voice_text = data.get('voice_text', '').strip()
        
        if not voice_text:
            return jsonify({"success": False, "message": "请输入语音识别文本"}), 400
        
        logger.info(f"开始AI优化语音识别结果: {voice_text[:50]}...")
        
        # 调用AI分析器进行优化
        from ai_augmented_parser import AIAugmentedShipmentParser
        
        # 创建AI解析器实例
        ai_parser = AIAugmentedShipmentParser()
        
        # 调用AI进行文本优化
        optimized_text = ai_parser.optimize_voice_recognition(voice_text)
        
        if optimized_text:
            logger.info(f"AI优化成功: {optimized_text[:50]}...")
            return jsonify({
                "success": True,
                "optimized_text": optimized_text
            })
        else:
            # 如果AI优化失败，返回原始文本
            logger.warning("AI优化失败，返回原始文本")
            return jsonify({
                "success": True,
                "optimized_text": voice_text
            })
            
    except Exception as e:
        logger.error(f"AI优化错误: {e}", exc_info=True)
        # 出错时返回原始文本
        voice_text = data.get('voice_text', '')
        return jsonify({
            "success": True,
            "optimized_text": voice_text
        })


@app.route('/download/<filename>')
def download_file(filename):
    """
    下载文件API
    GET /download/<filename>
    """
    try:
        # 安全检查：确保文件名不包含路径遍历字符
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({"success": False, "message": "非法文件名"}), 400
        
        # 检查文件是否存在
        file_path = os.path.join(OUTPUTS_DIR, filename)
        
        if not os.path.exists(file_path):
            return jsonify({"success": False, "message": "文件不存在"}), 404
        
        logger.info(f"下载文件: {filename}, 路径: {file_path}")
        
        # 直接使用send_file发送文件
        from flask import send_file
        return send_file(file_path, as_attachment=True, download_name=filename)
        
    except Exception as e:
        logger.error(f"下载文件错误: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"下载失败: {str(e)}"}), 500


@app.route('/api/templates')
@login_required
def get_templates():
    """
    获取可用模板列表API
    GET /api/templates
    """
    try:
        # 获取当前目录下的xlsx文件
        templates = []
        for file in os.listdir(BASE_DIR):
            if file.endswith('.xlsx') and not file.startswith('~'):
                templates.append(file)
        
        logger.info(f"加载模板列表: {templates}")
        return jsonify({"success": True, "templates": templates})
        
    except Exception as e:
        logger.error(f"获取模板列表错误: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"获取模板列表失败: {str(e)}"}), 500


@app.route('/health')
def health_check():
    """
    健康检查API
    GET /health
    """
    return jsonify({"status": "ok", "service": "shipment-document-generator"})

# ==================== 标签生成API ====================

@app.route('/label-generator')
def label_generator_page():
    """
    标签生成器页面
    """
    return '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>产品标签生成器</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .form-group {
            margin: 15px 0;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input[type="text"], input[type="date"] {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #45a049;
        }
        .result {
            margin-top: 20px;
            padding: 15px;
            background-color: #f9f9f9;
            border-radius: 4px;
        }
        .image-preview {
            margin-top: 10px;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            text-align: center;
        }
        .image-preview img {
            max-width: 100%;
            height: auto;
        }
        .error {
            color: red;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>产品标签生成器</h1>
        <form id="labelForm">
            <div class="form-group">
                <label for="productNumber">产品编号</label>
                <input type="text" id="productNumber" name="productNumber" value="7225-70F" required>
            </div>
            <div class="form-group">
                <label for="productName">产品名称</label>
                <input type="text" id="productName" name="productName" value="PU净味三分光清面漆" required>
            </div>
            <div class="form-group">
                <label for="ratio">参考配比</label>
                <input type="text" id="ratio" name="ratio" value="1:0.5-0.6:0.5-0.8">
                <small style="color: #666; font-size: 12px;">
                    <strong>💡 参考配比说明：</strong><br>
                    • 不同产品的参考配比规则存储在 ratio_rules.db 数据库中<br>
                    • 产品名称不包含"剂"或"料"时，会自动匹配参考配比<br>
                    • <strong>硬编码位置：</strong> app_api.py 第59-62行（RatioRulesManager类）<br>
                    • <strong>数据库文件：</strong> ratio_rules.db<br>
                    • <strong>常用配比：</strong><br>
                    &nbsp;&nbsp;- 白底漆类：1:0.5-0.6:0.5-0.8<br>
                    &nbsp;&nbsp;- 面漆类：1:0.4-0.5:0.4-0.7<br>
                    &nbsp;&nbsp;- 稀释剂：按实际需求调整
                </small>
            </div>
            <div class="form-group">
                <label for="productionDate">生产日期</label>
                <input type="text" id="productionDate" name="productionDate" value="2025.12.25">
            </div>
            <div class="form-group">
                <label for="shelfLife">保质期</label>
                <input type="text" id="shelfLife" name="shelfLife" value="6个月">
            </div>
            <div class="form-group">
                <label for="specification">产品规格</label>
                <input type="text" id="specification" name="specification" value="20±0.1KG">
            </div>
            <div class="form-group">
                <label for="inspector">检验员</label>
                <input type="text" id="inspector" name="inspector" value="合格 (01)">
            </div>
            <button type="submit">生成标签</button>
        </form>
        
        <div class="result" id="result" style="display: none;">
            <h3>生成结果</h3>
            <div id="message"></div>
            <div class="image-preview" id="imagePreview"></div>
            <a href="#" id="downloadLink" style="display: none;">下载标签图片</a>
        </div>
    </div>
    
    <script>
        document.getElementById('labelForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData();
            formData.append('product_number', document.getElementById('productNumber').value);
            formData.append('product_name', document.getElementById('productName').value);
            formData.append('ratio', document.getElementById('ratio').value);
            formData.append('production_date', document.getElementById('productionDate').value);
            formData.append('shelf_life', document.getElementById('shelfLife').value);
            formData.append('specification', document.getElementById('specification').value);
            formData.append('inspector', document.getElementById('inspector').value);
            
            fetch('/api/generate-label', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                const resultDiv = document.getElementById('result');
                const messageDiv = document.getElementById('message');
                const imagePreview = document.getElementById('imagePreview');
                const downloadLink = document.getElementById('downloadLink');
                
                if (data.success) {
                    messageDiv.innerHTML = '<p style="color: green;">标签生成成功！</p>';
                    imagePreview.innerHTML = `<img src="${data.image_url}" alt="产品标签" style="max-width: 100%; height: auto;">`;
                    downloadLink.href = data.image_url;
                    downloadLink.download = data.filename;
                    downloadLink.textContent = '下载标签图片';
                    downloadLink.style.display = 'block';
                } else {
                    messageDiv.innerHTML = `<p class="error">生成失败：${data.message}</p>`;
                    imagePreview.innerHTML = '';
                    downloadLink.style.display = 'none';
                }
                resultDiv.style.display = 'block';
            })
            .catch(error => {
                console.error('Error:', error);
                document.getElementById('result').innerHTML = '<p class="error">网络错误，请重试</p>';
                document.getElementById('result').style.display = 'block';
            });
        });
    </script>
</body>
</html>
'''

@app.route('/api/generate-label', methods=['POST'])
def generate_label_api():
    """
    生成产品标签API
    POST /api/generate-label
    """
    try:
        # 获取表单数据
        product_data = {
            'product_number': request.form.get('product_number', '').strip(),
            'product_name': request.form.get('product_name', '').strip(),
            'ratio': request.form.get('ratio', '1:0.5-0.6:0.5-0.8'),
            'production_date': request.form.get('production_date', '').strip(),
            'shelf_life': request.form.get('shelf_life', '6个月'),
            'specification': request.form.get('specification', '').strip(),
            'inspector': request.form.get('inspector', '合格')
        }
        
        # 验证必需字段
        if not product_data['product_number'] or not product_data['product_name']:
            return jsonify({"success": False, "message": "产品编号和名称为必填项"}), 400
        
        # 检查产品名称是否包含"剂"或"料"
        contains_ji_or_liao = any(keyword in product_data['product_name'] for keyword in ['剂', '料'])
        
        # 如果不包含"剂"或"料"，则尝试匹配参考配比
        if not contains_ji_or_liao:
            matched_ratio = ratio_manager.match_ratio_by_product_name(product_data['product_name'])
            if matched_ratio:
                product_data['ratio'] = matched_ratio
                logger.info(f"为产品 '{product_data['product_name']}' 匹配到参考配比: {matched_ratio}")
        
        # 生成唯一文件名
        import uuid
        filename = f"label_{uuid.uuid4().hex}.png"
        output_path = os.path.join(OUTPUTS_DIR, filename)
        
        # 生成标签
        generator = ProductLabelGenerator()
        generator.generate_label(product_data, output_path)
        
        # 生成访问URL
        image_url = f"/outputs/{filename}"
        
        return jsonify({
            "success": True,
            "image_url": image_url,
            "filename": filename,
            "message": "标签生成成功"
        })
        
    except Exception as e:
        logger.error(f"生成标签失败: {e}")
        return jsonify({"success": False, "message": f"生成失败: {str(e)}"}), 500


@app.route('/api/orders/<int:order_id>/shipment-records', methods=['GET'])
def get_shipment_records_for_order(order_id):
    """获取指定订单对应购买单位的出货记录"""
    try:
        # 获取订单信息
        cursor = db.cursor()
        cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
        order = cursor.fetchone()
        
        if not order:
            return jsonify({"success": False, "message": "订单不存在"}), 404
        
        # 获取购买单位
        purchase_unit = order[3]  # purchase_unit字段
        
        # 调用shipment_excel_sync中的函数来查找出货记录
        import shipment_excel_sync
        
        # 查找出货记录文件
        shipment_file = shipment_excel_sync.find_shipment_record(purchase_unit)
        
        if not shipment_file:
            return jsonify({
                "success": False, 
                "message": f"未找到购买单位 {purchase_unit} 的出货记录文件",
                "purchase_unit": purchase_unit,
                "shipment_records": []
            }), 200
        
        # 读取出货记录
        try:
            data = pd.read_excel(shipment_file, sheet_name=None)
            
            # 提取出货记录数据
            shipment_records = {}
            for sheet_name, df in data.items():
                if not df.empty:
                    # 转换为字典列表
                    records = []
                    for _, row in df.iterrows():
                        record = {}
                        for col in df.columns:
                            record[col] = str(row[col]) if pd.notna(row[col]) else ''
                        records.append(record)
                    shipment_records[sheet_name] = records
            
            return jsonify({
                "success": True,
                "message": "出货记录获取成功",
                "purchase_unit": purchase_unit,
                "shipment_file": shipment_file,
                "shipment_records": shipment_records,
                "sheets": list(data.keys())
            })
            
        except Exception as e:
            logger.error(f"读取出货记录失败: {e}")
            return jsonify({
                "success": False,
                "message": f"读取出货记录失败: {str(e)}",
                "purchase_unit": purchase_unit,
                "shipment_file": shipment_file
            }), 500
            
    except Exception as e:
        logger.error(f"获取出货记录失败: {e}")
        return jsonify({
            "success": False,
            "message": f"获取出货记录失败: {str(e)}"
        }), 500

@app.route('/api/orders/<int:order_id>/generate-labels', methods=['POST'])
@login_required
def generate_labels_from_order(order_id):
    """
    从订单生成产品标签API
    POST /api/order/<int:order_id>/generate-labels
    
    Request Body:
        {
            "auto_print": true/false  // 是否自动打印标签
        }
    """
    try:
        from order_manager import OrderManager
        from label_generator import ProductLabelGenerator
        from datetime import datetime
        import uuid
        
        # 获取请求数据
        data = request.get_json() or {}
        auto_print = data.get('auto_print', False)
        
        # 创建商标导出目录
        LABELS_EXPORT_DIR = os.path.join(BASE_DIR, '商标导出')
        os.makedirs(LABELS_EXPORT_DIR, exist_ok=True)
        
        logger.info(f"标签生成请求 - 订单ID: {order_id}, 自动打印: {auto_print}")
        
        # 获取订单信息
        db_path = os.path.join(BASE_DIR, 'products.db')
        order_manager = OrderManager(db_path)
        order = order_manager.get_order_by_id(order_id)
        
        if not order:
            return jsonify({"success": False, "message": "订单不存在"}), 404
        
        # 获取产品列表
        products = order.get('products', [])
        if not products:
            return jsonify({"success": False, "message": "订单中没有产品"}), 400
        
        # 生成当前日期
        current_date = datetime.now().strftime('%Y.%m.%d')
        
        # 为每个产品生成标签
        generated_labels = []
        for i, product in enumerate(products):
            # 准备产品数据
            # 处理规格值，去掉.0
            tin_spec = product.get('tin_spec', 10)
            try:
                if tin_spec.is_integer():
                    tin_spec = int(tin_spec)
            except:
                pass
            
            product_data = {
                'product_number': product.get('model_number', '') or product.get('model', ''),
                'product_name': product.get('name', '') or product.get('product_name', ''),
                'ratio': '1:0.5-0.6:0.5-0.8',  # 默认配比
                'production_date': current_date,
                'shelf_life': '6个月',
                'specification': product.get('specification', '') or f"{tin_spec}±0.1KG",
                'inspector': '合格'
            }
            
            # 验证必需字段
            if not product_data['product_number'] or not product_data['product_name']:
                continue
            
            # 检查产品名称是否包含"剂"或"料"
            contains_ji_or_liao = any(keyword in product_data['product_name'] for keyword in ['剂', '料'])
            
            # 如果不包含"剂"或"料"，则尝试匹配参考配比
            if not contains_ji_or_liao:
                matched_ratio = ratio_manager.match_ratio_by_product_name(product_data['product_name'])
                if matched_ratio:
                    product_data['ratio'] = matched_ratio
                    logger.info(f"为产品 '{product_data['product_name']}' 匹配到参考配比: {matched_ratio}")
            
            # 生成唯一文件名
            filename = f"label_{order.get('order_number', 'unknown')}_{i+1}_{uuid.uuid4().hex}.png"
            output_path = os.path.join(LABELS_EXPORT_DIR, filename)
            
            # 生成标签
            generator = ProductLabelGenerator()
            generator.generate_label(product_data, output_path)
            
            # 生成访问URL
            image_url = f"/商标导出/{filename}"
            
            generated_labels.append({
                'product_name': product_data['product_name'],
                'model_number': product_data['product_number'],
                'filename': filename,
                'file_path': output_path,
                'image_url': image_url
            })
        
        if not generated_labels:
            return jsonify({"success": False, "message": "没有生成任何标签"}), 400
        
        # 如果启用了自动打印
        if auto_print and generated_labels:
            logger.info(f"开始自动打印标签 - 订单ID: {order_id}")
            print_result = auto_print_labels(generated_labels, order)
            result_data = {
                "order_id": order_id,
                "order_number": order.get('order_number'),
                "labels": generated_labels,
                "export_dir": LABELS_EXPORT_DIR,
                "auto_print_result": print_result
            }
        else:
            result_data = {
                "order_id": order_id,
                "order_number": order.get('order_number'),
                "labels": generated_labels,
                "export_dir": LABELS_EXPORT_DIR
            }
        
        return jsonify({
            "success": True,
            "message": f"成功生成 {len(generated_labels)} 个产品标签" + ("，自动打印完成" if auto_print and generated_labels else ""),
            "data": result_data
        })
        
    except Exception as e:
        logger.error(f"从订单生成标签失败: {e}")
        return jsonify({"success": False, "message": f"生成失败: {str(e)}"}), 500


@app.route('/商标导出/<filename>')
def serve_label_file(filename):
    """
    提供商标导出文件的访问
    """
    try:
        LABELS_EXPORT_DIR = os.path.join(BASE_DIR, '商标导出')
        return send_from_directory(LABELS_EXPORT_DIR, filename)
    except Exception as e:
        logger.error(f"提供标签文件失败: {e}")
        return jsonify({"success": False, "message": "文件不存在"}), 404

@app.route('/outputs/<filename>')
def serve_output_file(filename):
    """
    提供输出文件访问
    """
    try:
        return send_from_directory(OUTPUTS_DIR, filename)
    except Exception as e:
        logger.error(f"提供文件失败: {e}")
        return jsonify({"success": False, "message": "文件不存在"}), 404


# ==================== 打印相关API ====================

@app.route('/api/printers')
def list_printers():
    """
    获取系统中可用的打印机列表
    
    GET /api/printers
    Returns:
        JSON: 打印机列表
    """
    try:
        logger.info("获取打印机列表请求")
        
        # 强制重新获取打印机列表
        import importlib
        importlib.reload(sys.modules['print_utils'])
        
        printers = get_printers()
        
        # 智能分类打印机
        document_printer = None
        label_printer = None
        
        for printer in printers:
            printer_name = printer.get('name', '').lower()
            
            # 识别发货单打印机（通常是点阵打印机）
            if any(keyword in printer_name for keyword in ['joli', '24-pin', 'dot matrix', 'impact', 'lq', '针式']):
                if not document_printer:  # 第一个匹配的作为发货单打印机
                    document_printer = printer
                    printer['type'] = '发货单打印机'
                    printer['is_default'] = True
                else:
                    printer['type'] = '发货单打印机'
                    printer['is_default'] = False
                    
            # 识别标签打印机（TSC系列）
            elif any(keyword in printer_name for keyword in ['tsc', 'ttp', 'label', '标签', 'thermal', 'barcode', 'zebra']):
                if not label_printer:  # 第一个匹配的作为标签打印机
                    label_printer = printer
                    printer['type'] = '标签打印机'
                    printer['is_default'] = True
                else:
                    printer['type'] = '标签打印机'
                    printer['is_default'] = False
        
        # 处理未分类的打印机
        for printer in printers:
            if 'type' not in printer:
                printer_name = printer.get('name', '').lower()
                # 排除条码/标签打印机作为发货单打印机
                if not any(exclude_keyword in printer_name for exclude_keyword in ['tsc', 'ttp', 'label', '标签', 'thermal', 'barcode', 'zebra']):
                    if not document_printer:  # 第一个非条码打印机作为发货单打印机
                        document_printer = printer
                        printer['type'] = '发货单打印机'
                        printer['is_default'] = True
                    else:
                        printer['type'] = '其他打印机'
                        printer['is_default'] = False
                else:
                    printer['type'] = '标签打印机'
                    printer['is_default'] = False
        
        # 如果没有自动识别发货单打印机，尝试选择第一个非条码打印机
        if not document_printer and printers:
            # 创建一个列表推导式，排除条码/标签打印机
            exclude_keywords = ['tsc', 'ttp', 'label', '标签', 'thermal', 'barcode', 'zebra']
            suitable_printers = []
            for p in printers:
                printer_name = p.get('name', '').lower()
                if not any(keyword in printer_name for keyword in exclude_keywords):
                    suitable_printers.append(p)
            if suitable_printers:
                document_printer = suitable_printers[0]
                document_printer['type'] = '发货单打印机'
                document_printer['is_default'] = True
            else:
                # 如果都是条码打印机，不强制指定
                logger.warning("⚠️ 所有打印机都是条码/标签打印机，未指定发货单打印机")
                
        if not label_printer and len(printers) >= 2:
            label_printer = printers[1]
            label_printer['type'] = '标签打印机'
            label_printer['is_default'] = True
        
        # 清理其他打印机的type标记
        for printer in printers:
            if printer not in [document_printer, label_printer]:
                printer['type'] = '其他打印机'
                printer['is_default'] = False
        
        # 构建响应数据
        response_data = {
            "success": True,
            "printers": printers,
            "count": len(printers),
            "classified": {
                "document_printer": {
                    "name": document_printer.get('name', '') if document_printer else None,
                    "status": document_printer.get('status', '未知') if document_printer else '未连接',
                    "is_connected": document_printer is not None
                },
                "label_printer": {
                    "name": label_printer.get('name', '') if label_printer else None,
                    "status": label_printer.get('status', '未知') if label_printer else '未连接',
                    "is_connected": label_printer is not None
                }
            },
            "summary": {
                "total_printers": len(printers),
                "document_printer_ready": document_printer is not None,
                "label_printer_ready": label_printer is not None,
                "all_ready": document_printer is not None and label_printer is not None
            }
        }
        
        logger.info(f"找到 {len(printers)} 个打印机: 发货单={document_printer.get('name', '未找到')}, 标签={label_printer.get('name', '未找到')}")
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"获取打印机列表失败: {e}")
        return jsonify({
            "success": False,
            "message": f"获取打印机列表失败: {str(e)}",
            "classified": {
                "document_printer": {"name": None, "status": "错误", "is_connected": False},
                "label_printer": {"name": None, "status": "错误", "is_connected": False}
            }
        }), 500


@app.route('/api/refresh-printers', methods=['POST'])
def refresh_printers():
    """
    强制刷新打印机列表
    
    POST /api/refresh-printers
    Returns:
        JSON: 刷新结果
    """
    try:
        logger.info("强制刷新打印机列表请求")
        
        # 强制重新导入模块
        import importlib
        importlib.reload(sys.modules.get('print_utils'))
        
        # 重新获取打印机
        printers = get_printers()
        
        logger.info(f"刷新后找到 {len(printers)} 个打印机")
        return jsonify({
            "success": True,
            "message": f"已刷新，找到 {len(printers)} 个打印机",
            "printers": printers,
            "count": len(printers)
        })
        
    except Exception as e:
        logger.error(f"刷新打印机列表失败: {e}")
        return jsonify({
            "success": False,
            "message": f"刷新失败: {str(e)}"
        }), 500


@app.route('/api/print/<filename>', methods=['POST'])
def print_document_route(filename):
    """
    打印指定文件
    
    POST /api/print/<filename>
    Request Body:
        {
            "printer_name": "打印机名称" (可选，默认使用系统默认打印机)
        }
    
    Returns:
        JSON: 打印结果
    """
    try:
        logger.info(f"打印文件请求: {filename}")
        
        # 获取请求数据
        data = request.get_json() or {}
        printer_name = data.get('printer_name', None)
        
        # 自动检测打印机类型
        if not printer_name:
            # 检查文件名，判断是发货单还是标签
            if filename.startswith('发货单'):
                # 发货单文件，使用Jolimark打印机
                printer_name = get_document_printer()
                if not printer_name:
                    logger.error("❌ 无法获取发货单打印机，拒绝使用系统默认打印机")
                    return jsonify({
                        "success": False,
                        "message": "发货单打印机未配置，无法打印"
                    }), 500
                logger.info(f"自动检测为发货单，使用发货单打印机: {printer_name}")
            elif filename.startswith('标签') or '标签' in filename:
                # 标签文件，使用标签打印机
                printer_name = get_label_printer()
                if not printer_name:
                    logger.error("❌ 无法获取标签打印机，拒绝使用系统默认打印机")
                    return jsonify({
                        "success": False,
                        "message": "标签打印机未配置，无法打印"
                    }), 500
                logger.info(f"自动检测为标签，使用标签打印机: {printer_name}")
            else:
                # 未知类型文件，也需要指定打印机
                logger.warning(f"未知文件类型: {filename}，拒绝打印")
                return jsonify({
                    "success": False,
                    "message": f"未知文件类型，无法自动分配打印机: {filename}"
                }), 400
        
        # 构建文件完整路径
        file_path = os.path.join(OUTPUTS_DIR, filename)
        
        if not os.path.exists(file_path):
            logger.error(f"文件不存在: {file_path}")
            return jsonify({
                "success": False,
                "message": f"文件不存在: {filename}"
            }), 404
        
        # 执行打印
        logger.info(f"使用打印机: {printer_name}")  # 关键日志：显示实际使用的打印机
        # 对于发货单，使用临时修改默认打印机的方式
        use_default_printer = filename.startswith('发货单')
        result = print_document(file_path, printer_name, use_default_printer=use_default_printer)
        
        logger.info(f"打印结果: {result}")
        
        # 对于发货单Excel文件，添加WPS窗口监控和强制关闭
        if filename.startswith('发货单') and result.get('success', False):
            logger.info("📄 发货单打印完成，开始监控WPS窗口...")
            
            # 导入必要的模块
            import win32api
            import win32gui
            import win32con
            import time
            import subprocess
            
            # 等待3秒让WPS打开并显示打印对话框
            time.sleep(3)
            
            # 监控并自动点击"否"按钮
            logger.info("⏳ 开始监控WPS窗口...")
            
            # 查找WPS窗口（包括主窗口和对话框）
            wps_hwnd = None
            dialog_hwnd = None
            
            # 尝试查找多种类型的WPS窗口
            window_classes = [
                'ksoframe',         # WPS主窗口
                'KingsoftOfficeApp', # WPS应用窗口
                'XLMAIN',           # Excel兼容模式
                '#32770',           # 通用对话框
                'bosa_sdm_Microsoft Office Excel'  # Excel对话框
            ]
            
            # 查找WPS窗口（最多尝试15次）
            for attempt in range(15):
                logger.info(f"尝试 {attempt+1}/15: 查找WPS窗口...")
                
                # 查找主窗口
                for cls in window_classes:
                    hwnd = win32gui.FindWindow(cls, None)
                    if hwnd:
                        window_text = win32gui.GetWindowText(hwnd)
                        logger.info(f"找到窗口: {cls}, 标题: '{window_text}', 句柄: {hwnd}")
                        
                        if '保存' in window_text or '是否' in window_text:
                            dialog_hwnd = hwnd
                            logger.info("✅ 找到WPS保存对话框！")
                        elif not wps_hwnd:
                            wps_hwnd = hwnd
                            logger.info("✅ 找到WPS主窗口！")
                
                if dialog_hwnd or wps_hwnd:
                    break
                
                time.sleep(1)
            
            # 确定要操作的窗口
            target_hwnd = dialog_hwnd if dialog_hwnd else wps_hwnd
            
            if target_hwnd:
                logger.info(f"开始在窗口 {target_hwnd} 中查找按钮...")
                
                # 递归查找所有子窗口中的按钮
                all_buttons = []
                
                def find_all_buttons(hwnd, buttons):
                    """递归查找所有可见窗口中的按钮"""
                    if win32gui.IsWindowVisible(hwnd):
                        text = win32gui.GetWindowText(hwnd)
                        if text:
                            buttons.append((hwnd, text))
                    # 递归查找子窗口
                    child = win32gui.GetWindow(hwnd, win32con.GW_CHILD)
                    while child:
                        find_all_buttons(child, buttons)
                        child = win32gui.GetWindow(child, win32con.GW_HWNDNEXT)
                    return True
                
                # 开始递归查找
                find_all_buttons(target_hwnd, all_buttons)
                
                logger.info(f"共找到 {len(all_buttons)} 个可见窗口")
                for hwnd, text in all_buttons:
                    if text:
                        logger.info(f"  - 窗口: {hwnd}, 文本: '{text}'")
                
                # 查找"否"、"不保存"、"取消"等按钮
                close_buttons = []
                for hwnd, text in all_buttons:
                    if any(keyword in text for keyword in ['否', '不保存', '取消', 'No', 'Cancel']):
                        close_buttons.append((hwnd, text))
                
                if close_buttons:
                    logger.info(f"找到 {len(close_buttons)} 个关闭相关按钮")
                    
                    # 点击第一个找到的关闭按钮
                    btn_hwnd, btn_text = close_buttons[0]
                    logger.info(f"准备点击按钮: '{btn_text}' (句柄: {btn_hwnd})")
                    
                    # 等待1秒让对话框完全加载
                    time.sleep(1)
                    
                    # 发送点击消息
                    try:
                        # 先发送鼠标移动和按下消息
                        win32api.PostMessage(btn_hwnd, win32con.WM_LBUTTONDOWN, 0, 0)
                        time.sleep(0.1)
                        win32api.PostMessage(btn_hwnd, win32con.WM_LBUTTONUP, 0, 0)
                        time.sleep(0.1)
                        # 再发送BM_CLICK消息
                        win32api.PostMessage(btn_hwnd, win32con.BM_CLICK, 0, 0)
                        logger.info(f"✅ 已点击'{btn_text}'按钮")
                        
                        # 等待窗口关闭（最多5秒）
                        logger.info("⏳ 等待WPS窗口关闭...")
                        for _ in range(5):
                            time.sleep(1)
                            # 检查所有WPS窗口是否都已关闭
                            all_closed = True
                            for cls in window_classes:
                                if win32gui.FindWindow(cls, None):
                                    all_closed = False
                                    break
                            if all_closed:
                                logger.info("✅ WPS窗口已完全关闭")
                                break
                        else:
                            logger.warning("⚠️ WPS窗口可能仍未关闭")
                            
                            # 尝试强制关闭WPS进程
                            logger.info("💥 尝试强制关闭WPS进程...")
                            
                            # 扩展WPS相关进程列表
                            processes = [
                                "wps.exe", "et.exe", "wpp.exe",  # 主程序进程
                                "wpscloudsvr.exe", "wpsnotify.exe",  # 后台服务
                                "wpscenter.exe", "wpsapp.exe", "wpspro.exe",  # 其他可能的WPS进程
                                "ksolaunch.exe", "ksodemo.exe", "wpsscan.exe",  # 相关工具进程
                                "wpsunins.exe", "wpscrashreport.exe", "wpsupdatetask.exe"  # 更新和崩溃报告
                            ]
                            
                            terminated_processes = []
                            failed_processes = []
                            
                            for proc in processes:
                                try:
                                    logger.info(f"尝试终止进程: {proc}")
                                    taskkill_result = subprocess.run(
                                        ["taskkill", "/IM", proc, "/F"],
                                        capture_output=True,
                                        text=True,
                                        timeout=3
                                    )
                                    if taskkill_result.returncode == 0:
                                        logger.info(f"✅ 已强制终止进程: {proc}")
                                        logger.debug(f"终止输出: {taskkill_result.stdout.strip()}")
                                        terminated_processes.append(proc)
                                    else:
                                        logger.debug(f"❌ 进程 {proc} 未运行或终止失败: {taskkill_result.stderr.strip()}")
                                        failed_processes.append(proc)
                                except subprocess.TimeoutExpired:
                                    logger.warning(f"⚠️ 终止进程 {proc} 超时")
                                    failed_processes.append(proc)
                                except Exception as e:
                                    logger.error(f"❌ 终止进程 {proc} 失败: {e}")
                                    failed_processes.append(proc)
                            
                            logger.info(f"进程终止结果: 成功 {len(terminated_processes)} 个, 失败 {len(failed_processes)} 个")
                            if terminated_processes:
                                logger.info(f"成功终止的进程: {', '.join(terminated_processes)}")
                            
                            # 增加等待时间，确保进程完全终止
                            logger.info("⏳ 等待5秒让进程完全终止...")
                            time.sleep(5)
                            
                    except Exception as e:
                        logger.error(f"点击按钮失败: {e}")
                else:
                    logger.warning("⚠️ 未找到关闭相关按钮")
                    # 如果没有找到按钮，尝试直接关闭窗口
                    try:
                        logger.info("尝试直接关闭WPS窗口...")
                        
                        # 方法1: 使用SendMessage发送WM_CLOSE（更可靠）
                        logger.info("方法1: 使用SendMessage发送WM_CLOSE")
                        win32api.SendMessage(target_hwnd, win32con.WM_CLOSE, 0, 0)
                        time.sleep(2)
                        
                        # 检查窗口是否关闭
                        still_open = False
                        for cls in window_classes:
                            if win32gui.FindWindow(cls, None):
                                still_open = True
                                break
                        
                        if still_open:
                            logger.warning("⚠️ SendMessage WM_CLOSE未生效，尝试方法2")
                            
                            # 方法2: 发送WM_DESTROY消息（强制关闭）
                            logger.info("方法2: 发送WM_DESTROY消息")
                            win32api.SendMessage(target_hwnd, win32con.WM_DESTROY, 0, 0)
                            time.sleep(2)
                            
                            # 再次检查
                            still_open = False
                            for cls in window_classes:
                                if win32gui.FindWindow(cls, None):
                                    still_open = True
                                    break
                            
                            if still_open:
                                logger.warning("⚠️ WM_DESTROY消息未生效，尝试方法3")
                                
                                # 方法3: 强制终止WPS进程（最终方案）
                                logger.info("方法3: 强制终止WPS进程")
                                try:
                                    # 扩展WPS相关进程列表
                                    processes = [
                                        "wps.exe", "et.exe", "wpp.exe",  # 主程序进程
                                        "wpscloudsvr.exe", "wpsnotify.exe",  # 后台服务
                                        "wpscenter.exe", "wpsapp.exe", "wpspro.exe",  # 其他可能的WPS进程
                                        "ksolaunch.exe", "ksodemo.exe", "wpsscan.exe",  # 相关工具进程
                                        "wpsunins.exe", "wpscrashreport.exe", "wpsupdatetask.exe"  # 更新和崩溃报告
                                    ]
                                    
                                    terminated_processes = []
                                    failed_processes = []
                                    
                                    for proc in processes:
                                        try:
                                            logger.info(f"尝试终止进程: {proc}")
                                            taskkill_result = subprocess.run(
                                                ["taskkill", "/IM", proc, "/F"],
                                                capture_output=True,
                                                text=True,
                                                timeout=3
                                            )
                                            if taskkill_result.returncode == 0:
                                                logger.info(f"✅ 已强制终止进程: {proc}")
                                                logger.debug(f"终止输出: {taskkill_result.stdout.strip()}")
                                                terminated_processes.append(proc)
                                            else:
                                                logger.debug(f"❌ 进程 {proc} 未运行或终止失败: {taskkill_result.stderr.strip()}")
                                                failed_processes.append(proc)
                                        except subprocess.TimeoutExpired:
                                            logger.warning(f"⚠️ 终止进程 {proc} 超时")
                                            failed_processes.append(proc)
                                        except Exception as e:
                                            logger.error(f"❌ 终止进程 {proc} 失败: {e}")
                                            failed_processes.append(proc)
                                    
                                    logger.info(f"进程终止结果: 成功 {len(terminated_processes)} 个, 失败 {len(failed_processes)} 个")
                                    if terminated_processes:
                                        logger.info(f"成功终止的进程: {', '.join(terminated_processes)}")
                                    
                                    # 增加等待时间，确保进程完全终止
                                    logger.info("⏳ 等待5秒让进程完全终止...")
                                    time.sleep(5)
                                    
                                except Exception as e:
                                    logger.error(f"强制终止进程失败: {e}")
                        
                    except Exception as e:
                        logger.error(f"关闭窗口失败: {e}")
            else:
                logger.warning("⚠️ 未找到WPS窗口")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"打印文件失败: {e}")
        return jsonify({
            "success": False,
            "message": f"打印失败: {str(e)}"
        }), 500


@app.route('/api/print-last', methods=['POST'])
def print_last_document():
    """
    打印最后一个生成的发货单
    
    POST /api/print-last
    Request Body:
        {
            "printer_name": "打印机名称" (可选)
        }
    
    Returns:
        JSON: 打印结果
    """
    try:
        logger.info("打印最后一个文档请求")
        
        # 获取请求数据
        data = request.get_json() or {}
        printer_name = data.get('printer_name', None)
        
        # 获取outputs目录中最新修改的xlsx文件
        latest_file = None
        latest_time = 0
        
        for file in os.listdir(OUTPUTS_DIR):
            if file.endswith('.xlsx'):
                file_path = os.path.join(OUTPUTS_DIR, file)
                file_time = os.path.getmtime(file_path)
                if file_time > latest_time:
                    latest_time = file_time
                    latest_file = file_path
        
        if not latest_file:
            return jsonify({
                "success": False,
                "message": "没有找到可打印的文件"
            }), 404
        
        logger.info(f"找到最新文件: {latest_file}")
        
        # 如果没有指定打印机，自动获取发货单打印机
        if not printer_name:
            printer_name = get_document_printer()
            if not printer_name:
                logger.error("❌ 无法获取发货单打印机，拒绝使用系统默认打印机")
                return jsonify({
                    "success": False,
                    "message": "发货单打印机未配置，无法打印"
                }), 500
            logger.info(f"使用发货单打印机: {printer_name}")
        
        # 执行打印，使用临时修改默认打印机的方式
        result = print_document(latest_file, printer_name, use_default_printer=True)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"打印最后一个文档失败: {e}")
        return jsonify({
            "success": False,
            "message": f"打印失败: {str(e)}"
        }), 500


# ==================== 数据库管理API ====================

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
                   discount_rate, is_active, created_at
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
                'discount_rate': customer['discount_rate'],
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
                discount_rate = ?, is_active = ?, updated_at = datetime('now')
            WHERE id = ?
        """, (
            data.get('contact_person'),
            data.get('contact_phone'),
            data.get('address'),
            data.get('discount_rate'),
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
                'customer_product_active': 1,
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
        required_fields = ['model_number', 'name', 'price']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({
                    "success": False, 
                    "message": f"缺少必需字段: {field}"
                }), 400
        
        # 检查是否要操作单位数据库
        purchase_unit = data.get('purchase_unit', '').strip()
        purchase_unit_id = data.get('purchase_unit_id')
        
        # 如果有purchase_unit_id，获取单位名称
        if purchase_unit_id and not purchase_unit:
            conn = sqlite3.connect(get_db_path())
            cursor = conn.cursor()
            cursor.execute("SELECT unit_name FROM purchase_units WHERE id = ?", [purchase_unit_id])
            result = cursor.fetchone()
            conn.close()
            if result:
                purchase_unit = result[0]
        
        if purchase_unit:
            # 构建单位数据库路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            units_dir = os.path.join(current_dir, 'unit_databases')
            os.makedirs(units_dir, exist_ok=True)
            db_path = os.path.join(units_dir, f'{purchase_unit}.db')
            
            # 连接或创建单位数据库
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 创建products表（如果不存在）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_number TEXT,
                    name TEXT NOT NULL,
                    specification TEXT,
                    price REAL,
                    quantity INTEGER DEFAULT 1,
                    description TEXT,
                    category TEXT,
                    brand TEXT,
                    unit TEXT DEFAULT '个',
                    is_active INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 检查产品是否已存在
            cursor.execute("SELECT id FROM products WHERE model_number = ?", [data['model_number']])
            existing = cursor.fetchone()
            if existing:
                conn.close()
                return jsonify({"success": False, "message": "产品型号已存在"}), 409
            
            # 插入新产品到单位数据库
            cursor.execute("""
                INSERT INTO products (model_number, name, specification, price, quantity, 
                                    description, category, brand, unit, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data['model_number'],
                data['name'],
                data.get('specification', ''),
                float(data['price']),
                data.get('quantity', 1),
                data.get('description', ''),
                data.get('category', ''),
                data.get('brand', ''),
                data.get('unit', '个'),
                1
            ))
            
            product_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            return jsonify({
                "success": True,
                "message": f"产品{data['name']}添加成功",
                "product_id": product_id,
                "database": "unit"
            })
        else:
            # 操作主数据库
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
                data.get('unit', '个')
            ))
            
            product_id = cursor.lastrowid
            
            # 检查是否需要关联购买单位
            purchase_unit_id = data.get('purchase_unit_id')
            if purchase_unit_id:
                # 验证购买单位是否存在
                cursor.execute('SELECT id FROM purchase_units WHERE id = ?', (purchase_unit_id,))
                if cursor.fetchone():
                    # 检查是否已存在关联
                    cursor.execute('SELECT id FROM customer_products WHERE unit_id = ? AND product_id = ?', 
                                 (purchase_unit_id, product_id))
                    if not cursor.fetchone():
                        # 创建购买单位与产品的关联
                        cursor.execute('''
                            INSERT INTO customer_products (unit_id, product_id, custom_price, is_active, created_at, updated_at)
                            VALUES (?, ?, ?, 1, datetime('now'), datetime('now'))
                        ''', (purchase_unit_id, product_id, float(data['price'])))
                        logger.info(f"产品 {product_id} 已关联到购买单位 {purchase_unit_id}")
            
            conn.commit()
            conn.close()
            
            return jsonify({
                "success": True,
                "message": "产品添加成功",
                "product_id": product_id,
                "database": "main"
            })
        
    except Exception as e:
        logger.error(f"添加产品失败: {e}")
        return jsonify({"success": False, "message": f"添加产品失败: {str(e)}"}), 500


@app.route('/api/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    """更新产品信息 - 支持单位数据库中的产品"""
    try:
        data = request.get_json()
        
        # 验证必需字段
        if not data:
            return jsonify({"success": False, "message": "缺少请求数据"}), 400
        
        # 获取单位名称（从URL参数或数据中）
        unit_name = data.get('unit_name')
        customer_id = data.get('customer_id')
        
        if not unit_name and not customer_id:
            return jsonify({"success": False, "message": "缺少单位信息，无法确定更新目标"}), 400
        
        # 如果提供了customer_id，先获取单位名称
        if customer_id and not unit_name:
            conn = sqlite3.connect(get_db_path())
            cursor = conn.cursor()
            cursor.execute("SELECT unit_name FROM purchase_units WHERE id = ?", [customer_id])
            result = cursor.fetchone()
            conn.close()
            if result:
                unit_name = result[0]
            else:
                return jsonify({"success": False, "message": "客户单位不存在"}), 404
        
        # 构建单位数据库路径
        current_dir = os.path.dirname(os.path.abspath(__file__))
        units_dir = os.path.join(current_dir, 'unit_databases')
        os.makedirs(units_dir, exist_ok=True)
        db_path = os.path.join(units_dir, f'{unit_name}.db')
        
        # 连接或创建单位数据库
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 创建products表（如果不存在）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_number TEXT,
                name TEXT NOT NULL,
                specification TEXT,
                price REAL,
                quantity INTEGER DEFAULT 1,
                description TEXT,
                category TEXT,
                brand TEXT,
                unit TEXT DEFAULT '个',
                is_active INTEGER DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
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
            return jsonify({"success": False, "message": f"产品ID {product_id} 不存在"}), 404
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": f"单位 {unit_name} 的产品更新成功"
        })
        
    except Exception as e:
        logger.error(f"更新产品失败: {e}")
        return jsonify({"success": False, "message": f"更新产品失败: {str(e)}"}), 500


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


@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    """删除产品（彻底删除）"""
    try:
        # 获取请求中的单位信息
        data = request.get_json() if request.data else {}
        purchase_unit = data.get('purchase_unit', '').strip()
        
        # 确定要操作的数据库
        if purchase_unit:
            # 构建单位数据库路径
            current_dir = os.path.dirname(os.path.abspath(__file__))
            units_dir = os.path.join(current_dir, 'unit_databases')
            os.makedirs(units_dir, exist_ok=True)
            db_path = os.path.join(units_dir, f'{purchase_unit}.db')
            
            # 连接单位数据库
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 创建products表（如果不存在）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_number TEXT,
                    name TEXT NOT NULL,
                    specification TEXT,
                    price REAL,
                    quantity INTEGER DEFAULT 1,
                    description TEXT,
                    category TEXT,
                    brand TEXT,
                    unit TEXT DEFAULT '个',
                    is_active INTEGER DEFAULT 1,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 检查产品是否存在
            cursor.execute("SELECT id, name FROM products WHERE id = ?", [product_id])
            product = cursor.fetchone()
            if not product:
                conn.close()
                return jsonify({"success": False, "message": "产品不存在"}), 404
            
            # 直接删除产品（单位数据库只有products表）
            cursor.execute("DELETE FROM products WHERE id = ?", [product_id])
            
            conn.commit()
            conn.close()
            
            return jsonify({
                "success": True, 
                "message": f"产品{product[1]}彻底删除成功"
            })
        else:
            # 操作主数据库
            conn = sqlite3.connect(get_db_path())
            cursor = conn.cursor()
            
            # 先检查产品是否存在
            cursor.execute("SELECT id, name FROM products WHERE id = ?", [product_id])
            product = cursor.fetchone()
            if not product:
                conn.close()
                return jsonify({"success": False, "message": "产品不存在"}), 404
            
            product_name = product[1]
            
            # 删除相关的客户专属价格记录
            cursor.execute("""
                DELETE FROM customer_products 
                WHERE product_id = ?
            """, [product_id])
            
            # 删除产品本身（彻底删除）
            cursor.execute("""
                DELETE FROM products 
                WHERE id = ?
            """, [product_id])
            
            conn.commit()
            conn.close()
            
            return jsonify({
            "success": True, 
            "message": f"产品{product_name}彻底删除成功"
        })
        
    except Exception as e:
        logger.error(f"删除产品失败: {e}")
        return jsonify({"success": False, "message": f"删除产品失败: {str(e)}"}), 500


@app.route('/api/products/batch', methods=['POST'])
def batch_add_products():
    """批量添加产品 - 支持单位数据库"""
    try:
        data = request.get_json()
        products = data.get('products', [])
        
        if not products:
            return jsonify({"success": False, "message": "缺少产品数据"}), 400
        
        # 获取单位信息（从第一个产品或数据中）
        unit_name = None
        unit_id = None
        
        # 优先使用unit_id
        for product in products:
            if product.get('unit_id'):
                unit_id = product.get('unit_id')
                break
        
        # 如果没有unit_id，再尝试获取purchase_unit
        if not unit_id:
            for product in products:
                if product.get('purchase_unit'):
                    unit_name = product.get('purchase_unit')
                    break
        
        # 如果只有unit_id，获取单位名称
        if unit_id and not unit_name:
            conn = sqlite3.connect(get_db_path())
            cursor = conn.cursor()
            cursor.execute("SELECT unit_name FROM purchase_units WHERE id = ?", [unit_id])
            result = cursor.fetchone()
            conn.close()
            if result:
                unit_name = result[0]
            else:
                return jsonify({"success": False, "message": "客户单位不存在"}), 404
        
        if not unit_name:
            return jsonify({"success": False, "message": "缺少单位信息，无法确定添加目标"}), 400
        
        # 使用统一的数据库访问函数
        result = get_unit_db_connection(unit_name)
        if not result:
            return jsonify({"success": False, "message": f"无法连接到单位数据库: {unit_name}"}), 404
        conn, cursor = result
        
        success_count = 0
        failed_count = 0
        failed_items = []
        
        for product in products:
            try:
                # 验证必需字段
                if not product.get('name'):
                    failed_count += 1
                    failed_items.append("缺少产品名称")
                    continue
                
                # 生成型号（如果没有）
                model_number = product.get('model_number') or product.get('型号', '')
                if not model_number:
                    # 基于名称生成简单型号
                    import re
                    # 提取名称中的数字和字母
                    model_parts = re.findall(r'[A-Za-z0-9]+', product['name'])
                    if model_parts:
                        model_number = ''.join(model_parts)[:20]
                    else:
                        # 使用时间戳生成唯一型号
                        import time
                        model_number = f'BATCH_{int(time.time())}_{success_count}'
                
                # 检查型号是否已存在
                cursor.execute("SELECT id FROM products WHERE model_number = ?", [model_number])
                if cursor.fetchone():
                    failed_count += 1
                    failed_items.append(f"型号 {model_number} 已存在")
                    continue
                
                # 插入产品
                cursor.execute("""
                    INSERT INTO products (model_number, name, specification, price, quantity, 
                                        description, category, brand, unit, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    model_number,
                    product.get('name', ''),
                    product.get('specification', '') or product.get('规格', ''),
                    float(product.get('price', 0)) if product.get('price') else 0.0,
                    int(product.get('quantity', 0)) if product.get('quantity') else 0,
                    product.get('description', '') or product.get('描述', '') or product.get('备注', ''),
                    product.get('category', ''),
                    product.get('brand', ''),
                    product.get('unit', '个'),
                    1  # is_active
                ])
                
                success_count += 1
                
            except Exception as e:
                failed_count += 1
                failed_items.append(f"添加失败: {str(e)}")
        
        conn.commit()
        conn.close()
        
        if success_count > 0:
            return jsonify({
                "success": True, 
                "message": f"成功添加 {success_count} 个产品，失败 {failed_count} 个",
                "success_count": success_count,
                "failed_count": failed_count,
                "failed_items": failed_items
            })
        else:
            return jsonify({
                "success": False, 
                "message": f"所有产品添加失败",
                "failed_count": failed_count,
                "failed_items": failed_items
            }), 400
            
    except Exception as e:
        logger.error(f"批量添加产品失败: {e}")
        return jsonify({"success": False, "message": f"批量添加产品失败: {str(e)}"}), 500


@app.route('/api/product_names/batch_delete', methods=['POST'])
def batch_delete_products():
    """批量删除产品（彻底删除）"""
    try:
        data = request.get_json()
        name_ids = data.get('name_ids', [])
        
        if not name_ids or not isinstance(name_ids, list):
            return jsonify({"success": False, "message": "需要提供产品ID列表"}), 400
        
        conn = sqlite3.connect(get_db_path())
        cursor = conn.cursor()
        
        success_count = 0
        failed_count = 0
        failed_items = []
        
        for product_id in name_ids:
            try:
                # 先检查产品是否存在
                cursor.execute("SELECT id, name FROM products WHERE id = ?", [product_id])
                product = cursor.fetchone()
                
                if not product:
                    failed_count += 1
                    failed_items.append(f"ID {product_id}: 产品不存在")
                    continue
                
                # 彻底删除产品（先删除相关记录，再删除产品）
                product_name = product[1]
                
                # 删除相关的客户专属价格记录
                cursor.execute("""
                    DELETE FROM customer_products 
                    WHERE product_id = ?
                """, [product_id])
                
                # 删除产品本身（彻底删除）
                cursor.execute("""
                    DELETE FROM products 
                    WHERE id = ?
                """, [product_id])
                
                success_count += 1
                logger.info(f"彻底删除产品: {product_name} (ID: {product_id})")
                
            except Exception as e:
                failed_count += 1
                failed_items.append(f"ID {product_id}: {str(e)}")
                logger.error(f"删除产品失败: {product_id}, 错误: {str(e)}")
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "success_count": success_count,
            "failed_count": failed_count,
            "message": f"彻底删除完成：成功 {success_count} 个，失败 {failed_count} 个",
            "failed_items": failed_items if failed_items else None
        })
        
    except Exception as e:
        logger.error(f"批量删除产品失败: {e}")
        return jsonify({"success": False, "message": f"批量删除失败: {str(e)}"}), 500

# ========== 语音学习样板API ==========

# 导入语音学习数据库
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from voice_learning_db import VoiceLearningDatabase
    voice_db = VoiceLearningDatabase()
except Exception as e:
    logger.warning(f"语音学习数据库导入失败: {e}")
    voice_db = None

@app.route('/voice_learning')
def voice_learning():
    """语音学习简化版页面"""
    return send_from_directory(os.path.join(BASE_DIR, 'templates'), 'voice_learning_simple.html')

@app.route('/api/voice_learning/add_sample', methods=['POST'])
def add_voice_sample():
    """添加语音学习样板"""
    try:
        if not voice_db:
            return jsonify({"success": False, "message": "语音学习数据库未初始化"}), 500
        
        data = request.get_json()
        wrong_input = data.get('wrong_input', '').strip()
        correct_output = data.get('correct_output', '').strip()
        category = data.get('category', '').strip()
        context = data.get('context', '').strip()
        
        if not wrong_input or not correct_output or not category:
            return jsonify({"success": False, "message": "缺少必要参数"}), 400
        
        sample_id = voice_db.add_sample(wrong_input, correct_output, category, context)
        
        if sample_id:
            logger.info(f"添加语音学习样板: {wrong_input} -> {correct_output}")
            return jsonify({
                "success": True,
                "message": "学习样板添加成功",
                "sample_id": sample_id
            })
        else:
            return jsonify({"success": False, "message": "添加失败"}), 500
            
    except Exception as e:
        logger.error(f"添加语音学习样板失败: {e}")
        return jsonify({"success": False, "message": f"服务器错误: {str(e)}"}), 500

@app.route('/api/voice_learning/update_sample/<int:sample_id>', methods=['PUT'])
def update_voice_sample(sample_id):
    """更新语音学习样板"""
    try:
        data = request.get_json()
        wrong_input = data.get('wrong_input', '').strip()
        correct_output = data.get('correct_output', '').strip()
        category = data.get('category', '用户学习').strip()
        
        if not wrong_input or not correct_output:
            return jsonify({"success": False, "message": "错误文本和正确文本都不能为空"}), 400
        
        # 更新样板
        result = voice_db.update_sample(sample_id, wrong_input, correct_output, category)
        
        if result:
            return jsonify({"success": True, "message": "样板更新成功"})
        else:
            return jsonify({"success": False, "message": "样板更新失败"}), 500
            
    except Exception as e:
        logger.error(f"更新语音学习样板失败: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"更新失败: {str(e)}"}), 500

@app.route('/api/voice_learning/delete_sample/<int:sample_id>', methods=['DELETE'])
def delete_voice_sample(sample_id):
    """删除语音学习样板"""
    try:
        # 删除样板
        result = voice_db.delete_sample(sample_id)
        
        if result:
            return jsonify({"success": True, "message": "样板删除成功"})
        else:
            return jsonify({"success": False, "message": "样板删除失败"}), 500
            
    except Exception as e:
        logger.error(f"删除语音学习样板失败: {e}", exc_info=True)
        return jsonify({"success": False, "message": f"删除失败: {str(e)}"}), 500

@app.route('/api/voice_learning/samples', methods=['GET'])
def get_voice_samples():
    """获取所有语音学习样板"""
    try:
        if not voice_db:
            return jsonify({"success": False, "message": "语音学习数据库未初始化"}), 500
        
        category = request.args.get('category')
        active_only = request.args.get('active_only', 'true').lower() == 'true'
        
        samples = voice_db.get_all_samples(category, active_only)
        
        return jsonify({
            "success": True,
            "samples": samples,
            "count": len(samples)
        })
        
    except Exception as e:
        logger.error(f"获取语音学习样板失败: {e}")
        return jsonify({"success": False, "message": f"服务器错误: {str(e)}"}), 500

@app.route('/api/voice_learning/samples/<int:sample_id>', methods=['PUT', 'DELETE'])
def manage_voice_sample(sample_id):
    """管理语音学习样板"""
    try:
        if not voice_db:
            return jsonify({"success": False, "message": "语音学习数据库未初始化"}), 500
        
        if request.method == 'DELETE':
            # 删除样板
            success = voice_db.delete_sample(sample_id)
            if success:
                return jsonify({"success": True, "message": "删除成功"})
            else:
                return jsonify({"success": False, "message": "删除失败"}), 500
        
        elif request.method == 'PUT':
            # 更新样板
            data = request.get_json()
            
            wrong_input = data.get('wrong_input')
            correct_output = data.get('correct_output')
            category = data.get('category')
            context = data.get('context')
            is_active = data.get('is_active')
            
            success = voice_db.update_sample(sample_id, wrong_input, correct_output, 
                                          category, context, is_active)
            
            if success:
                return jsonify({"success": True, "message": "更新成功"})
            else:
                return jsonify({"success": False, "message": "更新失败"}), 500
                
    except Exception as e:
        logger.error(f"管理语音学习样板失败: {e}")
        return jsonify({"success": False, "message": f"服务器错误: {str(e)}"}), 500

@app.route('/api/voice_learning/statistics', methods=['GET'])
def get_voice_statistics():
    """获取语音学习统计信息"""
    try:
        if not voice_db:
            return jsonify({"success": False, "message": "语音学习数据库未初始化"}), 500
        
        samples = voice_db.get_all_samples()
        
        # 统计数据
        total_samples = len(samples)
        categories = {}
        total_applications = 0
        total_success = 0
        valid_samples = 0
        
        for sample in samples:
            # 分类统计
            category = sample['category']
            if category not in categories:
                categories[category] = 0
            categories[category] += 1
            
            # 成功率统计
            if sample['usage_count'] > 0:
                total_applications += sample['usage_count']
                total_success += sample['success_rate'] * sample['usage_count']
                valid_samples += 1
        
        average_success_rate = total_success / total_applications if total_applications > 0 else 0.0
        
        return jsonify({
            "success": True,
            "statistics": {
                "total_samples": total_samples,
                "total_categories": len(categories),
                "total_applications": total_applications,
                "average_success_rate": average_success_rate,
                "categories": categories
            }
        })
        
    except Exception as e:
        logger.error(f"获取语音学习统计失败: {e}")
        return jsonify({"success": False, "message": f"服务器错误: {str(e)}"}), 500

@app.route('/api/voice_learning/ai_assist', methods=['POST'])
def ai_assist_voice():
    """AI辅助语音纠正"""
    try:
        if not voice_db:
            return jsonify({"success": False, "message": "语音学习数据库未初始化"}), 500
        
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({"success": False, "message": "请输入文本"}), 400
        
        # 搜索相似样板
        suggestions = voice_db.search_samples(text, similarity_threshold=0.6)
        
        # 应用样板进行纠正
        corrected_text = text
        applied_corrections = []
        
        for suggestion in suggestions:
            wrong_input = suggestion['wrong_input']
            correct_output = suggestion['correct_output']
            
            if wrong_input in corrected_text:
                corrected_text = corrected_text.replace(wrong_input, correct_output)
                applied_corrections.append({
                    "original": wrong_input,
                    "corrected": correct_output,
                    "confidence": suggestion['similarity']
                })
                
                # 记录应用
                voice_db.apply_sample(suggestion['id'], wrong_input, correct_output, True, 
                                    f"AI辅助应用 - 文本: {text}")
        
        return jsonify({
            "success": True,
            "text": text,
            "corrected_text": corrected_text,
            "suggestions": applied_corrections,
            "corrections_count": len(applied_corrections)
        })
        
    except Exception as e:
        logger.error(f"AI辅助语音纠正失败: {e}")
        return jsonify({"success": False, "message": f"服务器错误: {str(e)}"}), 500


def auto_print_labels(generated_labels, order):
    """
    自动打印产品标签
    
    Args:
        generated_labels: 生成的标签列表
        order: 订单信息
    
    Returns:
        dict: 打印结果
    """
    try:
        logger.info(f"开始自动打印标签 - 订单号: {order.get('order_number')}")
        
        # 获取打印机列表
        printers = get_printers()
        if not printers:
            return {"success": False, "message": "未找到可用打印机"}
        
        # 获取标签打印机（优先使用TSC TTP-244）
        label_printer = None
        
        # 查找TSC TTP-244打印机
        for printer in printers:
            if 'TSC TTP-244' in printer.get('name', '') or 'TTP-244' in printer.get('name', ''):
                label_printer = printer
                logger.info(f"找到标签打印机: {printer.get('name')}")
                break
        
        # 如果没找到TSC TTP-244，使用第二个打印机
        if not label_printer:
            if len(printers) >= 2:
                label_printer = printers[1]  # 使用第二个打印机
                logger.info(f"未找到TSC TTP-244，使用第二个打印机: {label_printer.get('name')}")
            else:
                label_printer = printers[0]   # 如果只有一个打印机，就使用第一个
                logger.info(f"未找到第二个打印机，使用第一个: {label_printer.get('name')}")
        
        if not label_printer:
            return {"success": False, "message": "未找到合适的标签打印机"}
        
        logger.info(f"使用标签打印机: {label_printer.get('name', 'Unknown')}")
        
        # 统计需要打印的标签数量
        products = order.get('products', [])
        if not products:
            return {"success": False, "message": "订单中没有产品信息"}
        
        # 计算总打印份数：每个产品的数量 × 2份
        # 例如：产品数量是1，打印2张；产品数量是2，打印4张
        total_labels = 0
        product_quantities = {}
        for product in products:
            # 使用 quantity_tins（桶数）作为产品数量
            quantity = product.get('quantity_tins', 1) or product.get('quantity', 1) or 1
            product_name = product.get('name', '') or product.get('product_name', '')
            product_quantities[product_name] = quantity
            total_labels += quantity * 2
        
        logger.info(f"需要打印 {len(products)} 个产品的标签，产品数量: {product_quantities}，共 {total_labels} 份")
        
        # 执行打印
        print_results = []
        for label in generated_labels:
            file_path = label.get('file_path')
            product_name = label.get('product_name', 'Unknown Product')
            
            if not os.path.exists(file_path):
                logger.error(f"标签文件不存在: {file_path}")
                print_results.append({
                    "product_name": product_name,
                    "success": False,
                    "message": "文件不存在"
                })
                continue
            
            # 获取该产品的数量，计算需要打印的标签份数
            product_quantity = product_quantities.get(product_name, 1)
            label_copies = product_quantity * 2  # 产品数量 × 2
            logger.info(f"产品 '{product_name}' 数量: {product_quantity}，需要打印 {label_copies} 张标签")
            
            # 打印该产品的标签（根据产品数量计算份数）
            for copy in range(label_copies):
                try:
                    result = print_document(file_path, label_printer.get('name'))
                    print_results.append({
                        "product_name": product_name,
                        "copy": copy + 1,
                        "success": result.get('success', False),
                        "message": result.get('message', 'Unknown error')
                    })
                    logger.info(f"打印标签 {product_name} 第{copy + 1}份: {result}")
                except Exception as e:
                    logger.error(f"打印标签失败 {product_name} 第{copy + 1}份: {e}")
                    print_results.append({
                        "product_name": product_name,
                        "copy": copy + 1,
                        "success": False,
                        "message": str(e)
                    })
        
        # 统计打印结果
        success_count = sum(1 for r in print_results if r.get('success', False))
        total_count = len(print_results)
        
        logger.info(f"标签打印完成: {success_count}/{total_count} 成功")
        
        return {
            "success": True,
            "message": f"自动打印完成: {success_count}/{total_count} 成功",
            "printer_used": label_printer.get('name'),
            "total_labels": total_count,
            "successful_labels": success_count,
            "details": print_results
        }
        
    except Exception as e:
        logger.error(f"自动打印标签失败: {e}")
        return {"success": False, "message": f"自动打印失败: {str(e)}"}

# =============================================================================
# PDF标签打印API端点
# =============================================================================

@app.route('/api/print/pdf_labels', methods=['POST'])
def print_pdf_labels():
    """打印PDF标签"""
    try:
        data = request.get_json()
        pdf_path = data.get('pdf_path', 'PDF文件/订单26-0200099A_标签.pdf')  # 修改：使用订单PDF作为默认
        copies = data.get('copies', 1)
        show_app = data.get('show_app', True)  # 修改：默认显示PDF应用窗口
        
        # 检查PDF文件是否存在
        if not os.path.exists(pdf_path):
            return {"success": False, "message": f"PDF文件不存在: {pdf_path}"}
        
        logger.info(f"开始PDF标签打印: {pdf_path}, 份数: {copies}, 显示应用: {show_app}")
        
        # 导入PDF标签打印机
        from pdf_label_printer import print_pdf_labels
        
        # 执行打印（传递show_app参数）
        result = print_pdf_labels(pdf_path, copies, show_app=show_app)
        
        logger.info(f"PDF标签打印结果: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"PDF标签打印失败: {e}")
        return {"success": False, "message": f"PDF标签打印失败: {str(e)}"}

@app.route('/api/pdf/convert_and_print', methods=['POST'])
def convert_and_print_pdf_labels():
    """将PNG标签转换为PDF并打印"""
    try:
        # 导入PNG到PDF的转换器
        from convert_labels_to_pdf import convert_png_to_pdf
        
        logger.info("开始将PNG标签转换为PDF并打印...")
        
        # 执行转换
        conversion_success = convert_png_to_pdf()
        
        if not conversion_success:
            return {"success": False, "message": "PNG转PDF失败"}
        
        # 导入PDF标签打印机
        from pdf_label_printer import print_pdf_labels
        
        # 执行打印
        pdf_path = "商标标签完整版.pdf"
        copies = request.json.get('copies', 1) if request.json else 1
        
        result = print_pdf_labels(pdf_path, copies)
        
        logger.info(f"PDF转换并打印结果: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"PDF转换并打印失败: {e}")
        return {"success": False, "message": f"PDF转换并打印失败: {str(e)}"}

@app.route('/api/print/single_label', methods=['POST'])
def print_single_label_api():
    """打印单个标签"""
    try:
        data = request.get_json() or {}
        label_index = data.get('label_index', 0)  # 默认打印第一个标签
        copies = data.get('copies', 1)
        
        logger.info(f"开始单标签打印: 标签序号={label_index + 1}, 份数={copies}")
        
        # 导入单标签打印机
        from print_single_label import print_single_label
        
        # 执行打印
        result = print_single_label(label_index, copies)
        
        logger.info(f"单标签打印结果: {result}")
        
        return result
        
    except Exception as e:
        logger.error(f"单标签打印失败: {e}")
        return {"success": False, "message": f"单标签打印失败: {str(e)}"}

@app.route('/api/print/list_labels', methods=['GET'])
def list_available_labels():
    """获取可用的标签列表"""
    try:
        labels_dir = "商标导出"
        
        if not os.path.exists(labels_dir):
            return {"success": False, "message": f"标签目录不存在: {labels_dir}"}
        
        png_files = glob.glob(os.path.join(labels_dir, "*.png"))
        png_files.sort()
        
        labels = []
        for i, file_path in enumerate(png_files):
            file_name = os.path.basename(file_path)
            # 从文件名提取信息
            if 'label_' in file_name:
                parts = file_name.split('_')
                if len(parts) >= 3:
                    order_info = parts[1]  # 如: 26-0200053A
                    label_number = parts[2]  # 如: 1
                    
                    labels.append({
                        "index": i,
                        "filename": file_name,
                        "order_number": order_info,
                        "label_number": label_number,
                        "file_path": file_path,
                        "size": os.path.getsize(file_path)
                    })
        
        return {
            "success": True,
            "message": f"找到 {len(labels)} 个标签",
            "labels": labels
        }
        
    except Exception as e:
        logger.error(f"获取标签列表失败: {e}")
        return {"success": False, "message": f"获取标签列表失败: {str(e)}"}


def add_to_startup():
    """添加程序到Windows开机自启动"""
    try:
        import winreg
        import sys
        
        # 获取当前脚本路径
        script_path = os.path.abspath(__file__)
        python_exe = sys.executable
        
        # 构建启动命令（使用pythonw.exe隐藏窗口）
        pythonw_exe = python_exe.replace('python.exe', 'pythonw.exe')
        if not os.path.exists(pythonw_exe):
            pythonw_exe = python_exe
        
        startup_command = f'"{pythonw_exe}" "{script_path}" --autostart'
        
        # 打开注册表启动项
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE)
        
        # 设置启动项
        app_name = "AI助手发货单系统"
        winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, startup_command)
        winreg.CloseKey(key)
        
        logger.info(f"✅ 已添加到开机自启动: {app_name}")
        return True
    except Exception as e:
        logger.error(f"❌ 添加开机自启动失败: {e}")
        return False


def remove_from_startup():
    """从Windows开机自启动中移除程序"""
    try:
        import winreg
        
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_WRITE)
        
        app_name = "AI助手发货单系统"
        try:
            winreg.DeleteValue(key, app_name)
            logger.info(f"✅ 已从开机自启动移除: {app_name}")
        except FileNotFoundError:
            logger.info(f"ℹ️ 启动项不存在: {app_name}")
        
        winreg.CloseKey(key)
        return True
    except Exception as e:
        logger.error(f"❌ 移除开机自启动失败: {e}")
        return False


def check_startup_status():
    """检查是否已设置为开机自启动"""
    try:
        import winreg
        
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        
        app_name = "AI助手发货单系统"
        try:
            value, _ = winreg.QueryValueEx(key, app_name)
            winreg.CloseKey(key)
            return True, value
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False, None
    except Exception as e:
        logger.error(f"检查开机自启动状态失败: {e}")
        return False, None


if __name__ == '__main__':
    import webbrowser
    import threading
    import time
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='AI助手发货单系统')
    parser.add_argument('--autostart', action='store_true', help='开机自启动模式（不打开浏览器）')
    parser.add_argument('--add-startup', action='store_true', help='添加到开机自启动')
    parser.add_argument('--remove-startup', action='store_true', help='从开机自启动移除')
    args = parser.parse_args()
    
    # 处理开机自启动管理命令
    if args.add_startup:
        if add_to_startup():
            print("✅ 已成功添加到开机自启动")
        else:
            print("❌ 添加到开机自启动失败")
        sys.exit(0)
    
    if args.remove_startup:
        if remove_from_startup():
            print("✅ 已成功从开机自启动移除")
        else:
            print("❌ 从开机自启动移除失败")
        sys.exit(0)
    
    # 检测是否是首次运行（通过环境变量标记）
    is_first_run = not os.environ.get('AI_ASSISTANT_RUNNING')
    
    if is_first_run:
        os.environ['AI_ASSISTANT_RUNNING'] = '1'
        
        # 只有在非自启动模式下才打开浏览器
        if not args.autostart:
            def open_browser():
                time.sleep(3)
                webbrowser.open('http://127.0.0.1:5000')
                webbrowser.open('http://127.0.0.1:5000/database')
            
            browser_thread = threading.Thread(target=open_browser)
            browser_thread.daemon = True
            browser_thread.start()
    
    # 检查开机自启动状态并记录日志
    is_startup, startup_cmd = check_startup_status()
    if is_startup:
        logger.info(f"✅ 当前已设置为开机自启动")
    else:
        logger.info(f"ℹ️ 当前未设置为开机自启动，运行 'python app_api.py --add-startup' 可添加")
    
    # 运行Flask应用（debug=False 避免终端保持打开）
    app.run(host='0.0.0.0', port=5000, debug=False)
