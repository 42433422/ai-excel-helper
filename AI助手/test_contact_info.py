#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试联系人信息获取
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_contact_info():
    """测试联系人信息获取"""
    
    print("=" * 80)
    print("🔍 测试联系人信息获取")
    print("=" * 80)
    
    import sqlite3
    
    # 直接查询数据库中的联系人信息
    conn = sqlite3.connect('products.db')
    cursor = conn.cursor()
    
    print("📊 查询蕊芯家私的联系人信息:")
    
    # 查询蕊芯家私1
    cursor.execute("""
        SELECT id, unit_name, contact_person, contact_phone, address
        FROM purchase_units
        WHERE unit_name LIKE '%蕊芯家私1%'
        LIMIT 5
    """)
    
    ruixin1_records = cursor.fetchall()
    if ruixin1_records:
        for record in ruixin1_records:
            id_, name, contact, phone, address = record
            print(f"  蕊芯家私1:")
            print(f"    ID: {id_}")
            print(f"    客户名: {name}")
            print(f"    联系人: {contact}")
            print(f"    电话: {phone}")
            print(f"    地址: {address}")
    else:
        print("  ❌ 未找到蕊芯家私1的记录")
    
    print()
    
    # 查询蕊芯家私
    cursor.execute("""
        SELECT id, unit_name, contact_person, contact_phone, address
        FROM purchase_units
        WHERE unit_name LIKE '%蕊芯家私%' AND unit_name != '%蕊芯家私1%'
        LIMIT 5
    """)
    
    ruixin_records = cursor.fetchall()
    if ruixin_records:
        for record in ruixin_records:
            id_, name, contact, phone, address = record
            print(f"  蕊芯家私:")
            print(f"    ID: {id_}")
            print(f"    客户名: {name}")
            print(f"    联系人: {contact}")
            print(f"    电话: {phone}")
            print(f"    地址: {address}")
    else:
        print("  ❌ 未找到蕊芯家私的记录")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("🤖 测试发货单生成器的联系人获取")
    print("=" * 60)
    
    from shipment_document import DocumentAPIGenerator
    
    doc_generator = DocumentAPIGenerator()
    
    test_order = "蕊芯1Pe白底漆10桶，规格28KG"
    
    print(f"测试订单: {test_order}")
    
    try:
        # 测试联系人获取
        unit_name = "蕊芯家私1"
        purchase_unit = doc_generator.generator._get_purchase_unit_info(unit_name)
        
        print(f"\n📋 获取的联系人信息:")
        print(f"  客户名: {purchase_unit.name}")
        print(f"  联系人: {purchase_unit.contact_person}")
        print(f"  电话: {purchase_unit.contact_phone}")
        print(f"  地址: {purchase_unit.address}")
        print(f"  ID: {purchase_unit.id}")
        
        if purchase_unit.contact_person:
            print(f"  ✅ 联系人信息获取成功")
        else:
            print(f"  ❌ 联系人信息为空")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("📄 测试完整的发货单生成")
    print("=" * 60)
    
    try:
        result = doc_generator.parse_and_generate(
            order_text=test_order,
            custom_mode=False,
            number_mode=False,
            generate_labels=False
        )
        
        if result.get('success'):
            purchase_unit = result.get('purchase_unit')
            if purchase_unit:
                print(f"  客户信息:")
                print(f"    名称: {purchase_unit.get('name', '无')}")
                print(f"    联系人: {purchase_unit.get('contact_person', '无')}")
                print(f"    电话: {purchase_unit.get('contact_phone', '无')}")
                print(f"    地址: {purchase_unit.get('address', '无')}")
            else:
                print(f"  ❌ 客户信息为空")
        else:
            print(f"  ❌ 生成失败: {result.get('message', '未知错误')}")
            
    except Exception as e:
        print(f"❌ 完整测试失败: {e}")

if __name__ == "__main__":
    test_contact_info()