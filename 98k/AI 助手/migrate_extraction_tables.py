"""
Excel 数据提取数据库迁移脚本
添加 extract_logs 和 field_mappings 表
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / 'products.db'

def create_extraction_tables():
    """创建数据提取相关表"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 创建 extract_logs 表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS extract_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_name TEXT,
        data_type TEXT,
        total_rows INTEGER,
        imported_rows INTEGER,
        skipped_rows INTEGER,
        failed_rows INTEGER,
        status TEXT,
        error_message TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # 创建 field_mappings 表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS field_mappings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        template_id INTEGER,
        excel_header TEXT,
        db_field TEXT,
        field_type TEXT,
        is_required INTEGER DEFAULT 0,
        validation_rule TEXT,
        FOREIGN KEY (template_id) REFERENCES templates(id)
    )
    ''')
    
    conn.commit()
    conn.close()
    
    print("✓ extract_logs 表创建成功")
    print("✓ field_mappings 表创建成功")

if __name__ == '__main__':
    create_extraction_tables()
