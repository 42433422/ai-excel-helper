#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import pandas as pd

def analyze_customer_data():
    """分析客户数据分布"""
    conn = sqlite3.connect('customer_products_final_corrected.db')
    customers = pd.read_sql_query('SELECT * FROM customers', conn)
    products = pd.read_sql_query('SELECT * FROM products', conn)
    conn.close()

    print('=' * 80)
    print('=== 客户数据分布分析 ===')
    print('=' * 80)
    
    print(f'\n总客户数: {len(customers)}')
    print(f'总产品数: {len(products)}')

    # 按客户统计
    customer_stats = products.groupby('客户ID').agg({
        '产品型号': 'count',
        '数量_件': 'sum',
        '规格_KG': 'sum',
        '金额': 'sum'
    }).rename(columns={'产品型号': '产品种类数'})

    customer_names = customers.set_index('customer_id')['客户名称']
    customer_stats['客户名称'] = customer_names[customer_stats.index]
    
    print('\n' + '=' * 80)
    print('客户统计表:')
    print('-' * 80)
    print(f"{'客户名称':<20} {'产品种类':<10} {'总数量(件)':<15} {'总规格(KG)':<15} {'总金额':<20}")
    print('-' * 80)
    
    for customer_id, stats in customer_stats.iterrows():
        print(f"{stats['客户名称']:<20} {stats['产品种类数']:<10} {stats['数量_件']:<15.0f} {stats['规格_KG']:<15.0f} {stats['金额']:<20.2f}")
    
    print('-' * 80)
    print(f"{'合计':<20} {customer_stats['产品种类数'].sum():<10} {customer_stats['数量_件'].sum():<15.0f} {customer_stats['规格_KG'].sum():<15.0f} {customer_stats['金额'].sum():<20.2f}")
    
    # 分类建议
    print('\n' + '=' * 80)
    print('模板分类建议:')
    print('-' * 80)
    
    for customer_id, stats in customer_stats.iterrows():
        customer = stats['客户名称']
        product_count = stats['产品种类数']
        
        if product_count >= 50:
            print(f'  ✓ {customer}: {product_count}种产品 -> 出货记录模板 + 发货单模板')
        elif product_count >= 20:
            print(f'  ○ {customer}: {product_count}种产品 -> 出货记录模板 或 发货单模板')
        else:
            print(f'  △ {customer}: {product_count}种产品 -> 发货单模板')
    
    # 文件来源分析
    print('\n' + '=' * 80)
    print('文件来源分析:')
    print('-' * 80)
    
    file_sources = products.groupby('来源').size().reset_index()
    file_sources.columns = ['来源', '产品数量']
    
    for _, row in file_sources.iterrows():
        print(f'  {row["来源"]}: {row["产品数量"]}种产品')

if __name__ == "__main__":
    analyze_customer_data()