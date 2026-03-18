#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试产品匹配逻辑
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_product_matching():
    """测试产品匹配逻辑"""
    try:
        from shipment_parser import ShipmentParser
        
        # 创建解析器实例
        parser = ShipmentParser(db_path="products.db")
        
        print("=== 测试产品匹配逻辑 ===")
        
        # 测试产品名称匹配
        test_products = [
            "Pe白底漆10桶规格28",
            "24-4-8 哑光银珠:1桶规格20",
            "PE稀释剂:1桶规格180"
        ]
        
        # 测试每个产品的匹配
        for i, product_text in enumerate(test_products, 1):
            print(f"\n=== 测试产品 {i}: {product_text} ===")
            
            # 测试数据库匹配
            result = parser._match_product_from_db(product_text, "蕊芯家私1", number_mode=False)
            
            if result:
                print(f"✅ 匹配成功:")
                print(f"  型号: {result.get('model_number', '')}")
                print(f"  名称: {result.get('name', '')}")
                print(f"  规格: {result.get('specification', '')}")
                print(f"  价格: ¥{result.get('price', 0)}")
            else:
                print(f"❌ 匹配失败")
                
                # 调试：提取产品关键词
                search_text = product_text.replace("蕊芯家私1", "").strip()
                search_text = search_text.replace("10桶", "").replace("1桶", "").replace("规格", "").strip()
                
                print(f"  清理后的文本: {search_text}")
                
                # 提取产品关键词
                keywords = parser._extract_product_keywords(search_text)
                print(f"  提取的关键词: {keywords}")
        
        # 测试编号模式
        print(f"\n=== 测试编号模式 ===")
        for i, product_text in enumerate(test_products, 1):
            print(f"\n产品 {i}: {product_text}")
            
            # 提取产品型号
            search_text = product_text.replace("蕊芯家私1", "").strip()
            search_text = search_text.replace("10桶", "").replace("1桶", "").replace("规格", "").strip()
            
            # 尝试提取型号（数字+字母组合）
            import re
            model_match = re.search(r'\b[A-Z0-9]+\b', search_text, re.IGNORECASE)
            if model_match:
                model_number = model_match.group(0)
                print(f"  提取的型号: {model_number}")
                
                # 测试用这个型号匹配
                result = parser._match_product_from_db(product_text, "蕊芯家私1", number_mode=True)
                if result:
                    print(f"  ✅ 编号模式匹配成功: {result.get('model_number', '')}")
                else:
                    print(f"  ❌ 编号模式匹配失败")
            else:
                print(f"  未找到型号")
    
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_product_matching()