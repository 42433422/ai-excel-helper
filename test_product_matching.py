#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细测试产品匹配逻辑
"""

import sqlite3
import re

def test_product_matching():
    """测试产品匹配逻辑"""
    db_path = '产品文件夹/customer_products_final_corrected.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 测试文本
        test_texts = [
            "蕊芯10桶9806规格28",
            "1桶9806a规格280"
        ]
        
        for text in test_texts:
            print(f"\n测试文本: {text}")
            print("=" * 60)
            
            # 清理输入文本，移除数量信息
            search_text = re.sub(r'\d+\s*(?:桶|kg|千克|公斤)', '', text)
            search_text = re.sub(r'规格\d+', '', search_text)
            search_text = search_text.replace("蕊芯", '').strip()
            
            print(f"清理后的文本: {search_text}")
            
            # 提取型号
            model_match = re.search(r'\b[A-Z0-9]+\b', search_text, re.IGNORECASE)
            if model_match:
                model_number = model_match.group(0)
                print(f"提取的型号: {model_number}")
                
                # 测试数据库查询
                print("\n数据库查询结果:")
                
                # 不区分大小写的查询
                cursor.execute('''
                    SELECT 产品型号, 产品名称, 规格_KG, 单价
                    FROM products
                    WHERE UPPER(产品型号) = UPPER(?)
                    LIMIT 5
                ''', [model_number])
                
                results = cursor.fetchall()
                if results:
                    for row in results:
                        print(f"  - 型号: {row[0]}, 名称: {row[1]}, 规格: {row[2]}, 单价: {row[3]}")
                else:
                    print("  无匹配结果")
                    
                    # 尝试模糊匹配
                    cursor.execute('''
                        SELECT 产品型号, 产品名称, 规格_KG, 单价
                        FROM products
                        WHERE UPPER(产品型号) LIKE UPPER(?)
                        LIMIT 5
                    ''', [f'%{model_number}%'])
                    
                    fuzzy_results = cursor.fetchall()
                    if fuzzy_results:
                        print("  模糊匹配结果:")
                        for row in fuzzy_results:
                            print(f"  - 型号: {row[0]}, 名称: {row[1]}, 规格: {row[2]}, 单价: {row[3]}")
                    else:
                        print("  无模糊匹配结果")
            else:
                print("  未提取到型号")
        
        # 测试直接查询9806和9806A
        print("\n" + "=" * 80)
        print("直接测试数据库查询:")
        print("=" * 80)
        
        # 测试9806
        print("\n测试9806:")
        cursor.execute('''
            SELECT 产品型号, 产品名称, 规格_KG, 单价
            FROM products
            WHERE 产品型号 = "9806"
            LIMIT 3
        ''')
        results = cursor.fetchall()
        for row in results:
            print(f"  - 型号: {row[0]}, 名称: {row[1]}, 规格: {row[2]}, 单价: {row[3]}")
        
        # 测试9806A
        print("\n测试9806A:")
        cursor.execute('''
            SELECT 产品型号, 产品名称, 规格_KG, 单价
            FROM products
            WHERE 产品型号 = "9806A"
            LIMIT 3
        ''')
        results = cursor.fetchall()
        for row in results:
            print(f"  - 型号: {row[0]}, 名称: {row[1]}, 规格: {row[2]}, 单价: {row[3]}")
        
        # 测试不区分大小写查询
        print("\n测试不区分大小写查询9806a:")
        cursor.execute('''
            SELECT 产品型号, 产品名称, 规格_KG, 单价
            FROM products
            WHERE UPPER(产品型号) = UPPER("9806a")
            LIMIT 3
        ''')
        results = cursor.fetchall()
        for row in results:
            print(f"  - 型号: {row[0]}, 名称: {row[1]}, 规格: {row[2]}, 单价: {row[3]}")
        
        conn.close()
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_product_matching()
