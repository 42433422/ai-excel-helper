#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XCAGI 共享数据库与路径配置

说明：
- 本文件从原 AI 助手/db.py 迁移而来
- 逐步清理对 sys.path.insert 的依赖
- 技术债跟踪：#001
"""

import os
import sys
import sqlite3
import logging
import urllib.parse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', encoding='utf-8')
logger = logging.getLogger(__name__)


def get_base_dir():
    """获取应用基础目录（兼容 PyInstaller 打包）"""
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def get_app_data_dir():
    """获取应用程序数据目录"""
    base = get_base_dir()
    if hasattr(sys, '_MEIPASS'):
        app_data = os.environ.get('APPDATA') or os.environ.get('LOCALAPPDATA')
        app_data_dir = os.path.join(app_data, 'XCAGI')
    else:
        app_data_dir = base
    os.makedirs(app_data_dir, exist_ok=True)
    return app_data_dir


BASE_DIR = get_base_dir()
APP_DATA_DIR = get_app_data_dir()
logger.info(f"XCAGI 应用运行目录：{BASE_DIR}")
logger.info(f"XCAGI 应用程序数据目录：{APP_DATA_DIR}")


def initialize_databases():
    """初始化数据库（PyInstaller 打包环境需要）"""
    import shutil
    is_frozen = hasattr(sys, '_MEIPASS')
    source_dir = sys._MEIPASS if is_frozen else BASE_DIR
    work_dir = APP_DATA_DIR
    logger.info(f"PyInstaller 打包环境：{is_frozen}")
    logger.info(f"源目录：{source_dir}")
    logger.info(f"工作目录：{work_dir}")
    
    # XCAGI 项目需要的数据库文件
    db_files = ['products.db', 'customers.db', 'inventory.db', 'voice_learning.db', 'error_collection.db']
    
    for db_file in db_files:
        source_path = os.path.join(source_dir, db_file)
        work_path = os.path.join(work_dir, db_file)
        logger.info(f"检查数据库：{db_file}")
        
        if not os.path.exists(source_path):
            logger.warning(f"  源数据库文件不存在：{source_path}")
            continue
        
        if os.path.exists(work_path):
            logger.info(f"  工作数据库已存在，跳过复制")
            continue
        
        try:
            shutil.copy2(source_path, work_path)
            logger.info(f"  已复制数据库文件：{db_file}")
            
            if os.path.exists(work_path):
                cur = sqlite3.connect(work_path).cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [t[0] for t in cur.fetchall()]
                logger.info(f"  数据库表：{tables}")
        except Exception as e:
            logger.error(f"  处理数据库文件失败 {db_file}: {e}")


def get_db_path():
    """获取数据库路径（兼容 PyInstaller 打包）"""
    if hasattr(sys, '_MEIPASS'):
        db_path = os.path.join(APP_DATA_DIR, 'products.db')
    else:
        db_path = os.path.join(BASE_DIR, 'products.db')
    logger.info(f"数据库路径：{db_path}")
    return db_path


def get_customers_db_path():
    """获取客户库路径"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(APP_DATA_DIR, 'customers.db')
    return os.path.join(BASE_DIR, 'customers.db')


def get_distillation_db_path():
    """蒸馏数据存储路径"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(APP_DATA_DIR, 'distillation.db')
    return os.path.join(BASE_DIR, 'distillation.db')


def _query_purchase_units_from_db(db_path):
    """从指定数据库查询 purchase_units 表，返回 list[dict]；表不存在或出错返回 []。"""
    if not db_path or not os.path.exists(db_path):
        return []
    
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='purchase_units'")
        if not cur.fetchone():
            conn.close()
            return []
        
        cur.execute(
            "SELECT id, unit_name, contact_person, contact_phone, address FROM purchase_units WHERE is_active = 1"
        )
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        logger.warning(f"查询 purchase_units 失败 {db_path}: {e}")
        return []


def get_all_purchase_units():
    """
    从 products.db 与 customers.db 合并加载购货单位
    同一 unit_name 以先出现的为准（products 优先）
    返回 dict: unit_name -> { id, name, contact_person, contact_phone, address }
    """
    merged = {}
    for path in (get_db_path(), get_customers_db_path()):
        for row in _query_purchase_units_from_db(path):
            name = (row.get("unit_name") or "").strip()
            if not name or name in merged:
                continue
            merged[name] = {
                "id": row.get("id"),
                "name": name,
                "contact_person": row.get("contact_person") or "",
                "contact_phone": row.get("contact_phone") or "",
                "address": row.get("address") or "",
            }
    return merged


def init_user_db():
    """初始化用户数据库"""
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


def get_unit_db_connection(unit):
    """
    获取单位数据库连接
    :param unit: 单位名称
    :return: (conn, cursor) 或 None
    """
    try:
        unit = urllib.parse.unquote(unit)
        db_path = os.path.join(BASE_DIR, 'unit_databases', f'{unit}.db')
        
        if not os.path.exists(db_path):
            logger.error(f"单位数据库不存在：{unit}, 路径：{db_path}")
            return None
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="products"')
        if not cursor.fetchone():
            logger.error(f"单位数据库中不存在 products 表：{unit}")
            conn.close()
            return None
        
        return conn, cursor
    except Exception as e:
        logger.error(f"获取单位数据库连接失败：{e}")
        return None


def query_db(sql, params=(), fetch_one=False):
    """查询数据库"""
    try:
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql, params)
        result = cursor.fetchone() if fetch_one else cursor.fetchall()
        conn.close()
        return result
    except Exception as e:
        logger.error(f"数据库查询失败：{e}")
        return None


def row_to_dict(row):
    """将 sqlite3.Row 对象转换为字典"""
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
        logger.error(f"数据库操作失败：{e}")
        return None


def get_unit_id_by_name(unit_name):
    """根据单位名称获取单位 ID"""
    try:
        unit = query_db("SELECT id FROM purchase_units WHERE unit_name = ? AND is_active = 1", [unit_name], fetch_one=True)
        return unit["id"] if unit else None
    except Exception:
        return None


def init_wechat_tasks_table():
    """初始化 wechat_tasks 表（存放从微信解析出来的任务）"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS wechat_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contact_id INTEGER,
            username TEXT,
            display_name TEXT,
            message_id TEXT,
            msg_timestamp INTEGER,
            raw_text TEXT NOT NULL,
            task_type TEXT NOT NULL DEFAULT 'unknown',
            status TEXT NOT NULL DEFAULT 'pending',
            last_status_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_wechat_tasks_contact_status
        ON wechat_tasks (contact_id, status)
        """
    )
    
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_wechat_tasks_msg_unique
        ON wechat_tasks (message_id, username)
        """
    )
    
    conn.commit()
    conn.close()


def insert_or_ignore_wechat_task(
    *,
    contact_id: int | None,
    username: str | None,
    display_name: str | None,
    message_id: str | None,
    msg_timestamp: int | None,
    raw_text: str,
    task_type: str = "unknown",
):
    """插入一条 wechat_tasks 记录，若已存在则忽略。返回插入行 id 或已存在行 id。"""
    if not raw_text:
        return None
    
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    if message_id and username:
        cur.execute(
            "SELECT id FROM wechat_tasks WHERE message_id = ? AND username = ? LIMIT 1",
            (message_id, username),
        )
        row = cur.fetchone()
        if row:
            conn.close()
            return row[0]
    
    cur.execute(
        """
        INSERT INTO wechat_tasks
        (contact_id, username, display_name, message_id, msg_timestamp, raw_text, task_type, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
        """,
        (contact_id, username, display_name, message_id, msg_timestamp, raw_text, task_type),
    )
    
    task_id = cur.lastrowid
    conn.commit()
    conn.close()
    return task_id


def update_wechat_task_status(task_id: int, status: str):
    """更新任务状态：pending / confirmed / done / ignored"""
    if status not in ("pending", "confirmed", "done", "ignored"):
        raise ValueError(f"invalid wechat_task status: {status}")
    
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute(
        "UPDATE wechat_tasks SET status = ?, last_status_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (status, task_id),
    )
    
    conn.commit()
    conn.close()


def get_pending_wechat_tasks_for_contact(contact_id: int | None, limit: int = 20):
    """查询某个联系人的挂起任务（pending）"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    if contact_id is not None:
        cur.execute(
            "SELECT * FROM wechat_tasks WHERE contact_id = ? AND status = 'pending' ORDER BY msg_timestamp DESC, id DESC LIMIT ?",
            (contact_id, limit),
        )
    else:
        cur.execute(
            "SELECT * FROM wechat_tasks WHERE status = 'pending' ORDER BY msg_timestamp DESC, id DESC LIMIT ?",
            (limit,),
        )
    
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows
