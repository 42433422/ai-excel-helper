"""
Excel 模板数据库迁移脚本
添加 templates 表用于存储 Excel 模板分析结果和配置
"""

import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent / 'products.db'

def create_templates_table():
    """创建 templates 表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 创建 templates 表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_key TEXT UNIQUE NOT NULL,
        template_name TEXT NOT NULL,
        template_type TEXT,
        original_file_path TEXT,
        analyzed_data TEXT,
        editable_config TEXT,
        zone_config TEXT,
        merged_cells_config TEXT,
        style_config TEXT,
        business_rules TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 创建 template_usage_log 表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS template_usage_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_id INTEGER,
        action TEXT,
        result TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (template_id) REFERENCES templates(id)
    )
    ''')
    
    conn.commit()
    conn.close()
    
    print("✓ templates 表创建成功")
    print("✓ template_usage_log 表创建成功")

if __name__ == '__main__':
    create_templates_table()
