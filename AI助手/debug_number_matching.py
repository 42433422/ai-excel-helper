#!/usr/bin/env python3
# 调试编号模式下的产品匹配过程

import sqlite3
import re
import os

def debug_number_matching():
    """调试编号模式下的产品匹配过程"""
    print("=== 调试编号模式下的产品匹配过程 ===")
    
    # 测试文本
    test_text = "蕊芯一桶，24-4-8规格25"
    print(f"测试文本: '{test_text}'")
    print()
    
    # 获取数据库路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, 'products.db')
    
    # 1. 提取购买单位
    purchase_units = ["蕊芯家私1", "蕊芯家私", "蕊芯", "蕊芯测试"]
    purchase_unit = None
    for unit in purchase_units:
        if unit in test_text:
            purchase_unit = unit
            break
    
    print(f"1. 提取的购买单位: {purchase_unit}")
    
    # 2. 按逗号分割多个产品
    products = test_text.split('，')
    print(f"2. 分割后的产品: {products}")
    
    # 3. 处理单个产品
    for i, item_text in enumerate(products):
        print(f"\n--- 处理产品 {i+1}: '{item_text}' ---")
        
        # 移除购买单位名称
        if purchase_unit:
            item_text = item_text.replace(purchase_unit, '').strip()
        
        print(f"移除购买单位后: '{item_text}'")
        
        # 模拟编号模式下的搜索文本处理
        # 清理输入文本，移除数量信息
        search_text = re.sub(r'\d+\s*(?:桶|kg|千克|公斤)', '', item_text)
        print(f"移除数量信息后: '{search_text}'")
        
        # 编号模式下保留数字
        # 移除购买单位名称（如果存在）
        if purchase_unit:
            search_text = search_text.replace(purchase_unit, '').strip()
        
        print(f"最终搜索文本: '{search_text}'")
        
        # 4. 数据库查询
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 分离字母数字组合关键词和纯数字关键词
            alpha_numeric_keywords = []
            numeric_keywords = []
            
            # 提取关键词
            words = re.findall(r'[a-zA-Z0-9\-]+', search_text)
            for word in words:
                if re.search(r'[a-zA-Z]', word):
                    alpha_numeric_keywords.append(word)
                else:
                    numeric_keywords.append(word)
            
            print(f"字母数字关键词: {alpha_numeric_keywords}")
            print(f"纯数字关键词: {numeric_keywords}")
            
            # 构建查询
            conditions = []
            params = []
            
            for keyword in alpha_numeric_keywords:
                conditions.append("(p.model_number LIKE ? OR p.name LIKE ?)")
                params.extend([f'%{keyword}%', f'%{keyword}%'])
            
            for keyword in numeric_keywords:
                conditions.append("(p.model_number LIKE ? OR p.name LIKE ?)")
                params.extend([f'%{keyword}%', f'%{keyword}%'])
            
            if conditions:
                where_clause = " AND ".join(conditions)
                query = f"""
                    SELECT DISTINCT p.id, p.model_number, p.name, p.specification, p.price
                    FROM products p
                    WHERE {where_clause}
                    AND p.is_active = 1
                    LIMIT 5
                """
                
                print(f"执行查询: {query}")
                print(f"查询参数: {params}")
                
                cursor.execute(query, params)
                results = cursor.fetchall()
                
                print(f"查询结果数量: {len(results)}")
                for j, row in enumerate(results):
                    print(f"  结果 {j+1}: ID={row[0]}, 型号='{row[1]}', 名称='{row[2]}', 规格='{row[3]}', 价格={row[4]}")
            
            else:
                print("没有提取到有效的关键词")
            
            conn.close()
            
        except Exception as e:
            print(f"数据库查询错误: {e}")
    
    print("\n=== 调试完成 ===")

if __name__ == "__main__":
    debug_number_matching()