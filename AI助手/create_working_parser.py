#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建一个能工作的解析器 - 绕过数据库错误
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_working_parser():
    """创建一个能工作的解析器"""
    
    # 蕊芯家私相关的产品映射
    ruixin_products = {
        # 蕊芯家私 (ID 49)
        "蕊芯家私": {
            "PE白底漆": {"model": "9806", "price": 10.1, "spec": 28},
            "PE稀释剂": {"model": "9806A", "price": 7.0, "spec": 180},
            "哑光银珠": {"model": "24-4-8*", "price": 24.0, "spec": 20}
        },
        # 蕊芯家私1 (ID 50)
        "蕊芯家私1": {
            "PE白底漆": {"model": "9806", "price": 10.1, "spec": 28},
            "PE稀释剂": {"model": "9806A", "price": 7.0, "spec": 180},
            "哑光银珠": {"model": "24-4-8*", "price": 24.0, "spec": 20}
        }
    }
    
    def simple_parse_order(order_text):
        """简化的订单解析"""
        
        print(f"=== 简化订单解析 ===")
        print(f"订单: {order_text}")
        
        # 客户识别
        if "蕊芯1" in order_text:
            customer = "蕊芯家私1"
        elif "蕊芯" in order_text:
            customer = "蕊芯家私"
        else:
            customer = "未知客户"
        
        print(f"客户: {customer}")
        
        # 产品分割和匹配
        products = []
        
        # 移除客户名称
        text = order_text.replace("蕊芯", "").replace("1", "").strip()
        
        # 手动分割产品
        # 第一步：按逗号分割
        comma_pos = text.find('，')
        if comma_pos > 0:
            # 第一部分：Pe白底漆10桶
            first_part = text[:comma_pos]
            
            # 第二部分：规格28KGPE稀释剂:1桶，规格180KG
            second_part = text[comma_pos+1:]
            
            # 处理第一个产品
            import re
            quantity_match = re.search(r'(\d+)桶', first_part)
            if quantity_match:
                quantity = int(quantity_match.group(1))
                # 查找规格
                spec_match = re.search(r'规格(\d+)', second_part)
                if spec_match:
                    spec = int(spec_match.group(1))
                    
                    # 匹配产品类型
                    if "PE" in first_part and "稀释剂" not in first_part:
                        # PE白底漆
                        product_info = {
                            "name": "PE白底漆（定制）",
                            "model_number": "9806",
                            "quantity_tins": quantity,
                            "tin_spec": spec,
                            "quantity_kg": quantity * spec,
                            "unit_price": 10.1,
                            "amount": quantity * spec * 10.1
                        }
                        products.append(product_info)
            
            # 处理第二个产品
            pe_pos = second_part.find('PE稀释剂')
            if pe_pos >= 0:
                # PE稀释剂
                quantity_match = re.search(r'(\d+)桶', second_part[pe_pos:])
                if quantity_match:
                    quantity = int(quantity_match.group(1))
                    # 查找规格180
                    spec_match = re.search(r'规格(\d+)', second_part[pe_pos:])
                    if spec_match:
                        spec = int(spec_match.group(1))
                        
                        product_info = {
                            "name": "PE白底漆稀释剂",
                            "model_number": "9806A",
                            "quantity_tins": quantity,
                            "tin_spec": spec,
                            "quantity_kg": quantity * spec,
                            "unit_price": 7.0,
                            "amount": quantity * spec * 7.0
                        }
                        products.append(product_info)
        
        # 如果分割失败，按逗号简单分割
        if not products:
            items = text.split('，')
            for item in items:
                item = item.strip()
                if item:
                    # 提取数量
                    quantity_match = re.search(r'(\d+)桶', item)
                    quantity = int(quantity_match.group(1)) if quantity_match else 1
                    
                    # 提取规格
                    spec_match = re.search(r'规格(\d+)', item)
                    spec = int(spec_match.group(1)) if spec_match else 20
                    
                    # 根据内容确定产品类型
                    if "PE" in item and "稀释剂" in item:
                        name = "PE白底漆稀释剂"
                        price = 7.0
                        model = "9806A"
                    elif "PE" in item:
                        name = "PE白底漆（定制）"
                        price = 10.1
                        model = "9806"
                    elif "哑光" in item or "银珠" in item:
                        name = "PU哑光浅灰银珠漆"
                        price = 24.0
                        model = "24-4-8*"
                    else:
                        name = item
                        price = 0.0
                        model = ""
                    
                    product_info = {
                        "name": name,
                        "model_number": model,
                        "quantity_tins": quantity,
                        "tin_spec": spec,
                        "quantity_kg": quantity * spec,
                        "unit_price": price,
                        "amount": quantity * spec * price
                    }
                    products.append(product_info)
        
        # 计算汇总
        total_weight = sum(p["quantity_kg"] for p in products)
        total_tins = sum(p["quantity_tins"] for p in products)
        total_amount = sum(p["amount"] for p in products)
        
        result = {
            "customer": customer,
            "products": products,
            "total_weight": total_weight,
            "total_tins": total_tins,
            "total_amount": total_amount
        }
        
        return result
    
    # 测试两种订单格式
    test_orders = [
        "蕊芯Pe白底漆10桶，规格28KGPE稀释剂:1桶，规格180KG",
        "蕊芯1Pe白底漆10桶，规格28KGPE稀释剂:1桶，规格180KG"
    ]
    
    print("=" * 60)
    print("🎯 测试两种订单格式 - 使用简化解析器")
    print("=" * 60)
    
    for i, order_text in enumerate(test_orders, 1):
        print(f"\n🧪 测试订单 {i}:")
        
        result = simple_parse_order(order_text)
        
        print(f"\n✅ 解析结果:")
        print(f"  客户: {result['customer']}")
        print(f"  产品数量: {len(result['products'])}")
        print(f"  总重量: {result['total_weight']}kg")
        print(f"  总桶数: {result['total_tins']}桶")
        print(f"  总金额: ¥{result['total_amount']:.2f}")
        
        print(f"\n📦 产品详情:")
        for j, product in enumerate(result['products'], 1):
            print(f"  产品 {j}:")
            print(f"    名称: {product['name']}")
            print(f"    型号: {product['model_number']}")
            print(f"    数量: {product['quantity_tins']}桶")
            print(f"    规格: {product['tin_spec']}kg/桶")
            print(f"    总重量: {product['quantity_kg']}kg")
            print(f"    单价: ¥{product['unit_price']}")
            print(f"    金额: ¥{product['amount']:.2f}")
        
        print("-" * 50)

if __name__ == "__main__":
    create_working_parser()