#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查语音应用解析器的产品数据匹配问题
"""

import sqlite3
import requests

def check_voice_parser_data():
    """检查语音应用解析器使用的产品数据"""
    try:
        conn = sqlite3.connect('products.db')
        cursor = conn.cursor()
        
        print("=== 检查语音应用解析器使用的数据 ===")
        
        # 检查蕊芯家私1的特定产品
        print("\n蕊芯家私1的相关产品:")
        cursor.execute("""
            SELECT pu.unit_name, p.model_number, p.name, cp.custom_price
            FROM customer_products cp
            JOIN products p ON cp.product_id = p.id
            JOIN purchase_units pu ON cp.unit_id = pu.id
            WHERE pu.unit_name LIKE '%蕊芯1%' OR pu.unit_name = '蕊芯家私1'
            AND (p.model_number = '9806' OR p.model_number = '9806A' OR p.model_number = '24-4-8*')
            ORDER BY p.model_number
        """)
        
        ruixin1_products = cursor.fetchall()
        for unit_name, model, name, price in ruixin1_products:
            print(f"  {model}: {name} (价格: {price})")
        
        # 检查解析器硬编码规则中的产品是否存在
        print("\n检查解析器硬编码规则:")
        rules = {
            '9806': 'PE白底漆',
            '9806A': 'PE稀释剂', 
            '24-4-8*': '哑光银珠漆'
        }
        
        for model, expected_name in rules.items():
            cursor.execute("""
                SELECT p.name
                FROM products p
                WHERE p.model_number = ?
            """, (model,))
            
            result = cursor.fetchone()
            if result:
                actual_name = result[0]
                match = expected_name.lower() in actual_name.lower() or actual_name.lower() in expected_name.lower()
                status = "✅" if match else "❌"
                print(f"  {status} {model}: 期望'{expected_name}' vs 实际'{actual_name}'")
            else:
                print(f"  ❌ {model}: 数据库中不存在")
        
        # 检查所有以"9806"开头的产品
        print("\n所有以'9806'开头的产品:")
        cursor.execute("""
            SELECT p.model_number, p.name
            FROM products p
            WHERE p.model_number LIKE '9806%'
            ORDER BY p.model_number
        """)
        
        all_9806 = cursor.fetchall()
        for model, name in all_9806:
            print(f"  {model}: {name}")
        
        conn.close()
        
        return True
    except Exception as e:
        print(f"检查失败: {e}")
        return False

def test_voice_app_api():
    """测试语音应用的API"""
    try:
        print("\n=== 测试语音应用API ===")
        
        # 测试解析接口
        test_data = {
            "order_text": "1桶9806A，规格20Kg",
            "number_mode": True
        }
        
        response = requests.post(
            "http://localhost:5000/api/shipment/parse",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API调用成功")
            print(f"解析结果: {result}")
        else:
            print(f"❌ API调用失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            
    except Exception as e:
        print(f"❌ API测试失败: {e}")

if __name__ == "__main__":
    check_voice_parser_data()
    test_voice_app_api()
