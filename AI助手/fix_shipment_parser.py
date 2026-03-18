#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复发货单解析器的数据库兼容性
"""

import re
import sqlite3
from typing import Dict, List, Optional, Tuple, Any

def fix_shipment_parser():
    """修复shipment_parser.py中的数据库兼容性"""
    
    # 读取原文件
    with open('shipment_parser.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 定义需要替换的SQL查询
    old_queries = [
        {
            'old': "SELECT 产品型号, 产品名称, 规格_KG, 单价\n                                        FROM products\n                                        WHERE 客户ID = ? AND UPPER(产品型号) LIKE UPPER(?)",
            'new': "SELECT p.model_number, p.name, p.specification, cp.custom_price\n                                         FROM products p\n                                         JOIN customer_products cp ON p.id = cp.product_id\n                                         WHERE cp.unit_id = ? AND UPPER(p.model_number) LIKE UPPER(?) AND cp.is_active = 1"
        },
        {
            'old': "SELECT 产品型号, 产品名称, 规格_KG, 单价\n                                    FROM products\n                                    WHERE 客户ID = ? AND 产品名称 LIKE ?",
            'new': "SELECT p.model_number, p.name, p.specification, cp.custom_price\n                                     FROM products p\n                                     JOIN customer_products cp ON p.id = cp.product_id\n                                     WHERE cp.unit_id = ? AND p.name LIKE ? AND cp.is_active = 1"
        },
        {
            'old': "SELECT 产品型号, 产品名称, 规格_KG, 单价\n                            FROM products\n                            WHERE UPPER(产品型号) = UPPER(?)",
            'new': "SELECT p.model_number, p.name, p.specification, p.price\n                            FROM products p\n                            WHERE UPPER(p.model_number) = UPPER(?)"
        },
        {
            'old': "SELECT 产品型号, 产品名称, 规格_KG, 单价\n                            FROM products\n                            WHERE UPPER(产品型号) LIKE UPPER(?)",
            'new': "SELECT p.model_number, p.name, p.specification, p.price\n                            FROM products p\n                            WHERE UPPER(p.model_number) LIKE UPPER(?)"
        },
        {
            'old': "SELECT 产品型号, 产品名称, 规格_KG, 单价\n                            FROM products\n                            WHERE 产品名称 LIKE ?",
            'new': "SELECT p.model_number, p.name, p.specification, p.price\n                            FROM products p\n                            WHERE p.name LIKE ?"
        }
    ]
    
    # 替换SQL查询
    for query in old_queries:
        content = content.replace(query['old'], query['new'])
    
    # 保存修复后的文件
    with open('shipment_parser.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ 发货单解析器数据库兼容性修复完成")

if __name__ == "__main__":
    fix_shipment_parser()