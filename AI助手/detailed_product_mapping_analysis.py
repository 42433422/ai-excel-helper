#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细的产品映射分析
比较Excel文件中的产品数据和数据库中的产品数据，找出映射错误
"""

import os
import sqlite3
import pandas as pd
import json
from datetime import datetime


def get_database_products():
    """
    从数据库中获取所有产品
    
    Returns:
        list: 产品列表
    """
    db_path = os.path.join(os.getcwd(), 'products.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT id, model_number, name, purchase_unit_id 
    FROM products 
    WHERE is_active = 1
    ''')
    
    products = []
    for row in cursor.fetchall():
        products.append({
            'id': row[0],
            'model_number': row[1],
            'name': row[2],
            'purchase_unit_id': row[3]
        })
    
    conn.close()
    return products


def get_purchase_units():
    """
    从数据库中获取所有购买单位
    
    Returns:
        dict: 购买单位字典，key为id，value为单位名称
    """
    db_path = os.path.join(os.getcwd(), 'products.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, unit_name FROM purchase_units WHERE is_active = 1')
    
    units = {}
    for row in cursor.fetchall():
        units[row[0]] = row[1]
    
    conn.close()
    return units


def analyze_product_mapping():
    """
    分析产品映射情况
    
    Returns:
        dict: 分析结果
    """
    print("=== 详细产品映射分析 ===")
    
    # 1. 读取Excel数据
    excel_file = "templates/新建 XLSX 工作表 (2).xlsx"
    df = pd.read_excel(excel_file, sheet_name='Sheet1')
    
    print(f"Excel数据总行数: {len(df)}")
    print(f"Excel唯一购买单位数: {df['购买单位'].nunique()}")
    print(f"Excel唯一产品型号数: {df['产品型号'].nunique()}")
    print(f"Excel唯一产品名称数: {df['产品名称'].nunique()}")
    print()
    
    # 2. 获取数据库数据
    db_products = get_database_products()
    purchase_units = get_purchase_units()
    
    print(f"数据库产品总数: {len(db_products)}")
    print(f"数据库购买单位数: {len(purchase_units)}")
    print()
    
    # 3. 分析购买单位映射
    excel_units = set(df['购买单位'].dropna().unique())
    db_unit_names = set(purchase_units.values())
    
    print("购买单位映射分析:")
    print(f"Excel中有但数据库中没有的单位: {excel_units - db_unit_names}")
    print(f"数据库中有但Excel中没有的单位: {db_unit_names - excel_units}")
    print(f"两边都有的单位: {excel_units & db_unit_names}")
    print()
    
    # 4. 分析产品型号映射
    excel_model_numbers = set(df['产品型号'].dropna().unique())
    db_model_numbers = set(product['model_number'] for product in db_products if product['model_number'])
    
    print("产品型号映射分析:")
    print(f"Excel中有但数据库中没有的型号: {len(excel_model_numbers - db_model_numbers)}")
    print(f"数据库中有但Excel中没有的型号: {len(db_model_numbers - excel_model_numbers)}")
    print(f"两边都有的型号: {len(excel_model_numbers & db_model_numbers)}")
    print()
    
    # 5. 分析产品名称映射
    excel_product_names = set(df['产品名称'].dropna().unique())
    db_product_names = set(product['name'] for product in db_products if product['name'])
    
    print("产品名称映射分析:")
    print(f"Excel中有但数据库中没有的产品名称: {len(excel_product_names - db_product_names)}")
    print(f"数据库中有但Excel中没有的产品名称: {len(db_product_names - excel_product_names)}")
    print(f"两边都有的产品名称: {len(excel_product_names & db_product_names)}")
    print()
    
    # 6. 分析具体的映射错误
    print("=== 具体映射错误分析 ===")
    
    # 按购买单位分组分析
    mapping_errors = []
    
    for unit in excel_units:
        print(f"\n分析购买单位: {unit}")
        
        # Excel中该单位的产品
        unit_excel_products = df[df['购买单位'] == unit]
        unit_excel_models = set(unit_excel_products['产品型号'].dropna())
        
        print(f"  Excel中该单位的产品数: {len(unit_excel_products)}")
        print(f"  Excel中该单位的唯一型号数: {len(unit_excel_models)}")
        
        # 数据库中该单位的产品（如果有对应的unit_id）
        unit_id = None
        for uid, name in purchase_units.items():
            if name == unit:
                unit_id = uid
                break
        
        if unit_id:
            unit_db_products = [p for p in db_products if p['purchase_unit_id'] == unit_id]
            unit_db_models = set(p['model_number'] for p in unit_db_products if p['model_number'])
            
            print(f"  数据库中该单位的产品数: {len(unit_db_products)}")
            print(f"  数据库中该单位的唯一型号数: {len(unit_db_models)}")
            
            # 找出不匹配的型号
            excel_only_models = unit_excel_models - unit_db_models
            db_only_models = unit_db_models - unit_excel_models
            
            if excel_only_models:
                print(f"  Excel中有但数据库中没有的型号 ({len(excel_only_models)}个):")
                for model in list(excel_only_models)[:10]:  # 只显示前10个
                    print(f"    - {model}")
                if len(excel_only_models) > 10:
                    print(f"    ... 还有 {len(excel_only_models) - 10} 个型号")
            
            if db_only_models:
                print(f"  数据库中有但Excel中没有的型号 ({len(db_only_models)}个):")
                for model in list(db_only_models)[:10]:  # 只显示前10个
                    print(f"    - {model}")
                if len(db_only_models) > 10:
                    print(f"    ... 还有 {len(db_only_models) - 10} 个型号")
            
            # 记录错误
            if excel_only_models or db_only_models:
                mapping_errors.append({
                    'unit': unit,
                    'excel_product_count': len(unit_excel_products),
                    'db_product_count': len(unit_db_products),
                    'excel_only_models': list(excel_only_models),
                    'db_only_models': list(db_only_models)
                })
        else:
            print(f"  数据库中未找到对应的购买单位: {unit}")
            mapping_errors.append({
                'unit': unit,
                'excel_product_count': len(unit_excel_products),
                'db_product_count': 0,
                'error': '数据库中未找到该单位'
            })
    
    # 7. 分析产品无购买单位关联的情况
    print("\n=== 数据库产品无购买单位关联分析 ===")
    products_without_unit = [p for p in db_products if p['purchase_unit_id'] is None]
    print(f"数据库中无购买单位关联的产品数: {len(products_without_unit)}")
    
    if products_without_unit:
        print("无购买单位关联的产品示例 (前10个):")
        for product in products_without_unit[:10]:
            print(f"  - 型号: {product['model_number']}, 名称: {product['name']}")
        if len(products_without_unit) > 10:
            print(f"  ... 还有 {len(products_without_unit) - 10} 个产品")
    
    # 8. 生成分析结果
    analysis_result = {
        'excel_data': {
            'total_rows': len(df),
            'unique_units': len(excel_units),
            'unique_models': len(excel_model_numbers),
            'unique_names': len(excel_product_names)
        },
        'database_data': {
            'total_products': len(db_products),
            'total_units': len(purchase_units),
            'products_without_unit': len(products_without_unit)
        },
        'mapping_analysis': {
            'unit_mapping': {
                'excel_only': list(excel_units - db_unit_names),
                'db_only': list(db_unit_names - excel_units),
                'both': list(excel_units & db_unit_names)
            },
            'model_mapping': {
                'excel_only_count': len(excel_model_numbers - db_model_numbers),
                'db_only_count': len(db_model_numbers - excel_model_numbers),
                'both_count': len(excel_model_numbers & db_model_numbers)
            }
        },
        'detailed_errors': mapping_errors
    }
    
    return analysis_result


def main():
    """
    主函数
    """
    # 执行分析
    analysis_result = analyze_product_mapping()
    
    # 保存分析结果
    output_file = f"product_mapping_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 详细分析结果已保存到: {output_file}")


if __name__ == "__main__":
    main()
