#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细调试SQL错误来源
"""

import sys
import os
import traceback
import sqlite3

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def debug_sql_error_source():
    """调试SQL错误的详细来源"""
    
    try:
        from shipment_parser import ShipmentParser
        
        # 创建解析器实例
        parser = ShipmentParser(db_path="products.db")
        
        # 测试产品匹配
        test_text = "Pe白底漆10桶，规格28"
        customer = "蕊芯家私1"
        
        print("=== 详细调试SQL错误来源 ===")
        print(f"测试产品: {test_text}")
        print(f"客户: {customer}")
        
        # 直接调用产品匹配方法
        try:
            result = parser._match_product_from_db(test_text, customer, number_mode=False)
            print(f"产品匹配结果: {result}")
        except Exception as e:
            print(f"产品匹配异常: {e}")
            print("详细错误信息:")
            traceback.print_exc()
        
        # 测试关键词提取
        try:
            keywords = parser._extract_product_keywords(test_text)
            print(f"提取的关键词: {keywords}")
        except Exception as e:
            print(f"关键词提取异常: {e}")
            traceback.print_exc()
            
        # 测试模糊匹配
        try:
            conn = sqlite3.connect('products.db')
            cursor = conn.cursor()
            
            # 获取unit_id
            cursor.execute("SELECT id FROM purchase_units WHERE unit_name = ?", (customer,))
            unit_result = cursor.fetchone()
            if unit_result:
                unit_id = unit_result[0]
                print(f"客户 {customer} 的ID: {unit_id}")
                
                # 测试各种可能的查询路径
                print("\n测试所有可能的查询路径:")
                
                # 路径1: 直接匹配型号
                try:
                    cursor.execute("""
                        SELECT p.model_number, p.name, p.specification, p.price 
                        FROM products p 
                        WHERE UPPER(p.model_number) = UPPER(?)
                        LIMIT 1
                    """, ("9806",))
                    result = cursor.fetchone()
                    print(f"✅ 型号直接匹配: {result}")
                except Exception as e:
                    print(f"❌ 型号直接匹配失败: {e}")
                
                # 路径2: 客户专属产品匹配
                try:
                    cursor.execute("""
                        SELECT p.model_number, p.name, p.specification, cp.custom_price 
                        FROM products p 
                        JOIN customer_products cp ON p.id = cp.product_id 
                        WHERE cp.unit_id = ? AND UPPER(p.model_number) = UPPER(?) AND cp.is_active = 1
                        LIMIT 1
                    """, (unit_id, "9806"))
                    result = cursor.fetchone()
                    print(f"✅ 客户专属产品匹配: {result}")
                except Exception as e:
                    print(f"❌ 客户专属产品匹配失败: {e}")
                    
                # 路径3: 模糊匹配
                try:
                    cursor.execute("""
                        SELECT p.model_number, p.name, p.specification, cp.custom_price 
                        FROM products p 
                        JOIN customer_products cp ON p.id = cp.product_id 
                        WHERE cp.unit_id = ? AND UPPER(p.model_number) LIKE UPPER(?) AND cp.is_active = 1
                        LIMIT 1
                    """, (unit_id, "%9806%"))
                    result = cursor.fetchone()
                    print(f"✅ 模糊匹配: {result}")
                except Exception as e:
                    print(f"❌ 模糊匹配失败: {e}")
                    
            conn.close()
            
        except Exception as e:
            print(f"数据库查询异常: {e}")
            traceback.print_exc()
        
    except Exception as e:
        print(f"整体测试异常: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    debug_sql_error_source()