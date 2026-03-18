#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
彻底修复发货单解析器的数据库兼容性
"""

def complete_fix_parser():
    """彻底修复所有数据库查询"""
    
    # 读取原文件
    with open('shipment_parser.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 定义所有需要替换的查询模式
    replacements = [
        # 客户表查询
        {
            'old': "SELECT customer_id FROM customers WHERE 客户名称 = ?",
            'new': "SELECT id FROM purchase_units WHERE unit_name = ?"
        },
        {
            'old': "SELECT id FROM purchase_units WHERE unit_name = ?",
            'new': "SELECT id FROM purchase_units WHERE unit_name = ?"
        },
        {
            'old': "SELECT id, unit_name, contact_person, contact_phone, address FROM purchase_units WHERE is_active = 1",
            'new': "SELECT id, unit_name, contact_person, contact_phone, address FROM purchase_units WHERE is_active = 1"
        },
        
        # 产品表查询
        {
            'old': "SELECT 产品型号, 产品名称, 规格_KG, 单价",
            'new': "SELECT p.model_number, p.name, p.specification, cp.custom_price"
        },
        {
            'old': "FROM products WHERE 客户ID = ? AND UPPER(产品型号) = UPPER(?)",
            'new': "FROM products p JOIN customer_products cp ON p.id = cp.product_id WHERE cp.unit_id = ? AND UPPER(p.model_number) = UPPER(?) AND cp.is_active = 1"
        },
        {
            'old': "FROM products WHERE 客户ID = ? AND UPPER(产品型号) LIKE UPPER(?)",
            'new': "FROM products p JOIN customer_products cp ON p.id = cp.product_id WHERE cp.unit_id = ? AND UPPER(p.model_number) LIKE UPPER(?) AND cp.is_active = 1"
        },
        {
            'old': "FROM products WHERE 客户ID = ? AND 产品名称 LIKE ?",
            'new': "FROM products p JOIN customer_products cp ON p.id = cp.product_id WHERE cp.unit_id = ? AND p.name LIKE ? AND cp.is_active = 1"
        },
        {
            'old': "FROM products WHERE UPPER(产品型号) = UPPER(?)",
            'new': "FROM products p WHERE UPPER(p.model_number) = UPPER(?)"
        },
        {
            'old': "FROM products WHERE UPPER(产品型号) LIKE UPPER(?)",
            'new': "FROM products p WHERE UPPER(p.model_number) LIKE UPPER(?)"
        },
        {
            'old': "FROM products WHERE 产品名称 LIKE ?",
            'new': "FROM products p WHERE p.name LIKE ?"
        },
        {
            'old': "FROM products",
            'new': "FROM products p"
        },
        {
            'old': "SELECT p.model_number, p.name, p.specification, cp.custom_price FROM products p WHERE UPPER(p.model_number) = UPPER(?)",
            'new': "SELECT p.model_number, p.name, p.specification, p.price FROM products p WHERE UPPER(p.model_number) = UPPER(?)"
        },
        {
            'old': "SELECT p.model_number, p.name, p.specification, cp.custom_price FROM products p WHERE UPPER(p.model_number) LIKE UPPER(?)",
            'new': "SELECT p.model_number, p.name, p.specification, p.price FROM products p WHERE UPPER(p.model_number) LIKE UPPER(?)"
        },
        {
            'old': "SELECT p.model_number, p.name, p.specification, cp.custom_price FROM products p WHERE p.name LIKE ?",
            'new': "SELECT p.model_number, p.name, p.specification, p.price FROM products p WHERE p.name LIKE ?"
        },
    ]
    
    # 执行所有替换
    for replacement in replacements:
        old_text = replacement['old']
        new_text = replacement['new']
        if old_text in content:
            content = content.replace(old_text, new_text)
            print(f"✅ 替换: {old_text[:50]}...")
        else:
            print(f"⚠️ 未找到: {old_text[:50]}...")
    
    # 保存修复后的文件
    with open('shipment_parser.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n🎉 发货单解析器数据库兼容性彻底修复完成!")

if __name__ == "__main__":
    complete_fix_parser()