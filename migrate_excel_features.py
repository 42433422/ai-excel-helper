#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XCAGI 数据库迁移脚本 - 添加 Excel 提取和模板管理功能

添加的表：
- extract_logs: Excel 提取操作日志
- templates: Excel 模板配置
- template_usage_log: 模板使用日志
"""

import sqlite3
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)


def get_db_path():
    """获取数据库路径"""
    base_dir = Path(__file__).parent
    return base_dir / 'products.db'


def create_extraction_tables():
    """创建 Excel 提取相关表"""
    db_path = get_db_path()
    logger.info(f"数据库路径：{db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 创建 extract_logs 表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS extract_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT NOT NULL,
            file_path TEXT,
            data_type TEXT NOT NULL,
            total_rows INTEGER DEFAULT 0,
            valid_rows INTEGER DEFAULT 0,
            imported_rows INTEGER DEFAULT 0,
            skipped_rows INTEGER DEFAULT 0,
            failed_rows INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            error_message TEXT,
            field_mapping TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        logger.info("✓ extract_logs 表创建成功")
        
        # 创建 field_mappings 表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS field_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_id INTEGER,
            excel_header TEXT,
            db_field TEXT,
            field_type TEXT,
            is_required INTEGER DEFAULT 0,
            validation_rule TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (log_id) REFERENCES extract_logs(id)
        )
        ''')
        logger.info("✓ field_mappings 表创建成功")
        
        conn.commit()
        logger.info("Excel 提取表创建完成")
        
    except Exception as e:
        logger.error(f"创建提取表失败：{e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def create_templates_tables():
    """创建模板管理相关表"""
    db_path = get_db_path()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 创建 templates 表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_key TEXT UNIQUE NOT NULL,
            template_name TEXT NOT NULL,
            template_type TEXT DEFAULT '通用',
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
        logger.info("✓ templates 表创建成功")
        
        # 创建 template_usage_log 表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS template_usage_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER,
            action TEXT NOT NULL,
            result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (template_id) REFERENCES templates(id)
        )
        ''')
        logger.info("✓ template_usage_log 表创建成功")
        
        conn.commit()
        logger.info("模板管理表创建完成")
        
    except Exception as e:
        logger.error(f"创建模板表失败：{e}")
        conn.rollback()
        raise
    finally:
        conn.close()


def verify_tables():
    """验证表是否创建成功"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('extract_logs', 'templates', 'template_usage_log', 'field_mappings')")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['extract_logs', 'templates', 'template_usage_log', 'field_mappings']
        
        logger.info(f"已创建的表：{tables}")
        
        for table in expected_tables:
            if table in tables:
                logger.info(f"✓ {table} 表已创建")
            else:
                logger.error(f"✗ {table} 表未创建")
                return False
        
        logger.info("所有表验证通过")
        return True
        
    except Exception as e:
        logger.error(f"验证表失败：{e}")
        return False
    finally:
        conn.close()


def migrate_all():
    """执行所有迁移"""
    logger.info("=" * 50)
    logger.info("开始数据库迁移 - Excel 提取和模板管理功能")
    logger.info("=" * 50)
    
    try:
        create_extraction_tables()
        create_templates_tables()
        
        if verify_tables():
            logger.info("=" * 50)
            logger.info("✓ 数据库迁移完成")
            logger.info("=" * 50)
            return True
        else:
            logger.error("✗ 数据库迁移失败 - 表验证未通过")
            return False
            
    except Exception as e:
        logger.error(f"✗ 数据库迁移失败：{e}")
        return False


if __name__ == '__main__':
    success = migrate_all()
    exit(0 if success else 1)
