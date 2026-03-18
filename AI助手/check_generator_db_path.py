#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查DocumentAPIGenerator的数据库路径
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_generator_db_path():
    """检查DocumentAPIGenerator的数据库路径"""
    
    print("=" * 80)
    print("🔍 检查DocumentAPIGenerator的数据库路径")
    print("=" * 80)
    
    from shipment_document import DocumentAPIGenerator
    
    doc_generator = DocumentAPIGenerator()
    
    print(f"DocumentAPIGenerator类型: {type(doc_generator).__name__}")
    print(f"generator类型: {type(doc_generator.generator).__name__}")
    
    # 检查数据库路径
    generator_db_path = doc_generator.generator.db_path
    print(f"\n📂 DocumentAPIGenerator的数据库路径:")
    print(f"  路径: {generator_db_path}")
    print(f"  存在: {'✅' if os.path.exists(generator_db_path) else '❌'}")
    if os.path.exists(generator_db_path):
        print(f"  绝对路径: {os.path.abspath(generator_db_path)}")
    
    # 比较直接AI解析器的数据库路径
    from ai_augmented_parser import AIAugmentedShipmentParser
    ai_parser = AIAugmentedShipmentParser()
    
    ai_db_path = ai_parser.db_path
    print(f"\n🤖 AI解析器的数据库路径:")
    print(f"  路径: {ai_db_path}")
    print(f"  存在: {'✅' if os.path.exists(ai_db_path) else '❌'}")
    if os.path.exists(ai_db_path):
        print(f"  绝对路径: {os.path.abspath(ai_db_path)}")
    
    print(f"\n📊 路径对比:")
    print(f"  相同: {'✅' if generator_db_path == ai_db_path else '❌'}")
    if generator_db_path != ai_db_path:
        print(f"  DocumentAPIGenerator: {generator_db_path}")
        print(f"  AI解析器: {ai_db_path}")
    
    # 检查数据库内容
    print(f"\n🔍 数据库内容对比:")
    
    import sqlite3
    
    try:
        # DocumentAPIGenerator的数据库
        conn1 = sqlite3.connect(generator_db_path)
        cursor1 = conn1.cursor()
        
        cursor1.execute("SELECT COUNT(*) FROM customer_products")
        count1 = cursor1.fetchone()[0]
        print(f"  DocumentAPIGenerator数据库 - customer_products: {count1} 条记录")
        
        # 检查9806产品
        cursor1.execute("""
            SELECT COUNT(*) FROM customer_products cp
            JOIN products p ON cp.product_id = p.id
            WHERE p.model_number = '9806'
        """)
        count_9806_1 = cursor1.fetchone()[0]
        print(f"  DocumentAPIGenerator数据库 - 9806产品: {count_9806_1} 条记录")
        
        conn1.close()
        
    except Exception as e:
        print(f"  DocumentAPIGenerator数据库检查失败: {e}")
    
    try:
        # AI解析器的数据库
        conn2 = sqlite3.connect(ai_db_path)
        cursor2 = conn2.cursor()
        
        cursor2.execute("SELECT COUNT(*) FROM customer_products")
        count2 = cursor2.fetchone()[0]
        print(f"  AI解析器数据库 - customer_products: {count2} 条记录")
        
        # 检查9806产品
        cursor2.execute("""
            SELECT COUNT(*) FROM customer_products cp
            JOIN products p ON cp.product_id = p.id
            WHERE p.model_number = '9806'
        """)
        count_9806_2 = cursor2.fetchone()[0]
        print(f"  AI解析器数据库 - 9806产品: {count_9806_2} 条记录")
        
        conn2.close()
        
    except Exception as e:
        print(f"  AI解析器数据库检查失败: {e}")

if __name__ == "__main__":
    check_generator_db_path()