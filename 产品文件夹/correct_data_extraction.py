#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import sqlite3
from datetime import datetime
import re
import os

def safe_float_with_limit(value):
    """安全转换为浮点数，并限制最大值"""
    try:
        if pd.isna(value):
            return 0.0
        if isinstance(value, str):
            # 如果是中文，直接返回0
            if any(ord(char) > 127 for char in value):
                return 0.0
            # 移除非数字字符，但保留小数点和负号
            cleaned = re.sub(r'[^\d.-]', '', value)
            if cleaned and cleaned.replace('-', '').replace('.', '').isdigit():
                num = float(cleaned)
                # 限制最大值为100万
                if num > 1000000:
                    return 0.0
                return num
            else:
                return 0.0
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def extract_corrected_data():
    """提取正确的数据（修正列索引）"""
    print('=== 修正后的数据提取 ===')
    print('规格：I列（第9列，索引8）')
    print('单价：K列（第11列，索引10）')
    print('规格单位：KG/桶')
    
    # 客户信息
    df_尹 = pd.read_excel('e:\\女娲1号\\发货单\\尹玉华1.xlsx', sheet_name='尹')
    customer_info = {}
    
    if len(df_尹) > 0:
        customer_row = df_尹.iloc[0]
        customer_text = str(customer_row.iloc[0]) if not pd.isna(customer_row.iloc[0]) else ""
        
        customer_match = re.search(r'购货单位：([^联系方式]*)', customer_text)
        if customer_match:
            customer_info['客户名称'] = customer_match.group(1).strip()
        
        contact_match = re.search(r'联系人：([^日期]*?)(\s|$)', customer_text)
        if contact_match:
            customer_info['联系人'] = contact_match.group(1).strip()
        
        date_match = re.search(r'(\d{4}年\d{2}月\d{2}日)', customer_text)
        if date_match:
            customer_info['日期'] = date_match.group(1)
        
        order_match = re.search(r'订单编号：([^联系方式]*?)$', customer_text)
        if order_match:
            customer_info['订单编号'] = order_match.group(1).strip()
    
    for i in range(len(df_尹)):
        for j in range(len(df_尹.columns)):
            cell_value = df_尹.iloc[i, j]
            if not pd.isna(cell_value) and isinstance(cell_value, str):
                if '成都国圣工业有限公司' in cell_value:
                    customer_info['供应商名称'] = '成都国圣工业有限公司'
                    customer_info['电话'] = '028-85852618'
                    break
    
    # 产品信息（修正列索引）
    df_出货 = pd.read_excel('e:\\女娲1号\\发货单\\尹玉华1.xlsx', sheet_name='出货')
    products = []
    
    print(f"\n出货工作表形状: {df_出货.shape}")
    print("列索引对应:")
    print("  - 产品型号: 第4列（索引3）")
    print("  - 产品名称: 第7列（索引6）")
    print("  - 规格/KG: 第9列（索引8）I列")
    print("  - 数量/KG: 第11列（索引10）")
    print("  - 单价: 第11列（索引10）K列")
    print("  - 金额: 第13列（索引12）")
    
    for index, row in df_出货.iterrows():
        if index == 0 or index == 1:
            continue
            
        product = {}
        
        if not pd.isna(row.iloc[3]):  # 产品型号（第4列）
            model = str(row.iloc[3]).strip()
            # 跳过包含中文的产品型号
            if any(ord(char) > 127 for char in model):
                continue
            product['产品型号'] = model
        else:
            continue
            
        if not pd.isna(row.iloc[6]):  # 产品名称（第7列）
            name = str(row.iloc[6]).strip()
            # 跳过包含异常描述的产品名称
            if '做' in name or '模板' in name or '的' in name:
                continue
            product['产品名称'] = name
            
        # 修正列索引
        product['规格_KG_桶'] = safe_float_with_limit(row.iloc[8])  # I列（第9列，索引8）
        product['数量_KG'] = safe_float_with_limit(row.iloc[9])  # J列（第10列，索引9）
        product['单价'] = safe_float_with_limit(row.iloc[10])  # K列（第11列，索引10）
        product['金额'] = safe_float_with_limit(row.iloc[11])  # L列（第12列，索引11）
        
        if not pd.isna(row.iloc[1]):  # 日期
            product['日期'] = row.iloc[1]
            
        if not pd.isna(row.iloc[2]):  # 单号
            product['单号'] = str(row.iloc[2])
            
        product['记录顺序'] = index
        product['来源'] = '出货记录'
        
        products.append(product)
    
    # 从尹工作表提取产品
    if len(df_尹) > 3:
        尹_product = {}
        model = str(df_尹.iloc[3, 0]).strip() if not pd.isna(df_尹.iloc[3, 0]) else ""
        if model and not any(ord(char) > 127 for char in model):
            尹_product['产品型号'] = model
            
            name = str(df_尹.iloc[3, 3]).strip() if not pd.isna(df_尹.iloc[3, 3]) else ""
            if name and '做' not in name:
                尹_product['产品名称'] = name
                
            尹_product['数量_件'] = safe_float_with_limit(df_尹.iloc[3, 4])
            尹_product['规格_KG_桶'] = safe_float_with_limit(df_尹.iloc[3, 5])
            尹_product['数量_KG'] = safe_float_with_limit(df_尹.iloc[3, 6])
            尹_product['单价'] = safe_float_with_limit(df_尹.iloc[3, 7])
            尹_product['金额'] = safe_float_with_limit(df_尹.iloc[3, 8])
            尹_product['来源'] = '发货单'
            尹_product['记录顺序'] = 9999
            
            products.append(尹_product)
    
    # 去重
    latest_products = {}
    for product in products:
        model = product.get('产品型号', '')
        if model:
            record_order = product.get('记录顺序', 0)
            
            if model not in latest_products or record_order > latest_products[model]['记录顺序']:
                latest_products[model] = product
    
    return customer_info, list(latest_products.values())

def create_corrected_database(customer_info, products):
    """创建修正后的数据库"""
    print('\n=== 创建修正后的数据库 ===')
    
    # 删除旧数据库
    try:
        os.remove('customer_products_corrected.db')
    except:
        pass
    
    # 连接到新的SQLite数据库
    conn = sqlite3.connect('customer_products_corrected.db')
    cursor = conn.cursor()
    
    # 创建客户表
    cursor.execute('''
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            客户名称 TEXT NOT NULL UNIQUE,
            联系人 TEXT,
            电话 TEXT,
            地址 TEXT,
            供应商名称 TEXT,
            供应商电话 TEXT,
            创建时间 DATETIME DEFAULT CURRENT_TIMESTAMP,
            更新时间 DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建订单表
    cursor.execute('''
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            客户ID INTEGER,
            订单编号 TEXT,
            订单日期 DATE,
            订单状态 TEXT DEFAULT '未完成',
            创建时间 DATETIME DEFAULT CURRENT_TIMESTAMP,
            更新时间 DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (客户ID) REFERENCES customers (customer_id)
        )
    ''')
    
    # 创建产品表（包含修正的规格字段）
    cursor.execute('''
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            客户ID INTEGER,
            订单ID INTEGER,
            产品型号 TEXT NOT NULL,
            产品名称 TEXT,
            规格_KG_桶 REAL DEFAULT 0.0,  -- I列：规格（KG/桶）
            数量_KG REAL DEFAULT 0.0,
            数量_件 REAL DEFAULT 0.0,
            单价 REAL DEFAULT 0.0,  -- K列：单价
            金额 REAL DEFAULT 0.0,
            单号 TEXT,
            记录顺序 INTEGER DEFAULT 0,
            来源 TEXT DEFAULT '出货记录',
            创建时间 DATETIME DEFAULT CURRENT_TIMESTAMP,
            更新时间 DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (客户ID) REFERENCES customers (customer_id),
            FOREIGN KEY (订单ID) REFERENCES orders (order_id)
        )
    ''')
    
    # 创建索引
    cursor.execute('CREATE INDEX idx_products_customer ON products (客户ID)')
    cursor.execute('CREATE INDEX idx_products_model ON products (产品型号)')
    
    conn.commit()
    
    # 插入客户
    cursor.execute('''
        INSERT INTO customers (客户名称, 联系人, 供应商名称, 供应商电话)
        VALUES (?, ?, ?, ?)
    ''', (
        customer_info.get('客户名称', ''),
        customer_info.get('联系人', ''),
        customer_info.get('供应商名称', ''),
        customer_info.get('电话', '')
    ))
    customer_id = cursor.lastrowid
    
    # 插入订单
    cursor.execute('''
        INSERT INTO orders (客户ID, 订单编号, 订单日期)
        VALUES (?, ?, ?)
    ''', (
        customer_id,
        customer_info.get('订单编号', ''),
        customer_info.get('日期', '')
    ))
    order_id = cursor.lastrowid
    
    # 插入产品
    for product in products:
        cursor.execute('''
            INSERT INTO products (
                客户ID, 订单ID, 产品型号, 产品名称, 规格_KG_桶, 数量_KG, 数量_件,
                单价, 金额, 单号, 记录顺序, 来源
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            customer_id,
            order_id,
            product.get('产品型号', ''),
            product.get('产品名称', ''),
            product.get('规格_KG_桶', 0.0),
            product.get('数量_KG', 0.0),
            product.get('数量_件', 0.0),
            product.get('单价', 0.0),
            product.get('金额', 0.0),
            product.get('单号', ''),
            product.get('记录顺序', 0),
            product.get('来源', '出货记录')
        ))
    
    conn.commit()
    conn.close()
    
    print(f"修正后的数据插入完成：{len(products)} 种产品")

def verify_corrected_database():
    """验证修正后的数据库"""
    print('\n=== 验证修正后的数据库 ===')
    
    conn = sqlite3.connect('customer_products_corrected.db')
    
    # 客户信息
    customers = pd.read_sql_query('SELECT * FROM customers', conn)
    print(f'客户数量: {len(customers)}')
    if len(customers) > 0:
        c = customers.iloc[0]
        print(f'客户名称: {c["客户名称"]}')
        print(f'联系人: {c["联系人"]}')
    
    # 产品信息
    products = pd.read_sql_query('SELECT * FROM products', conn)
    print(f'产品种类: {len(products)}')
    
    # 统计信息
    cursor = conn.cursor()
    cursor.execute('SELECT SUM(单价) FROM products')
    total_price = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT SUM(规格_KG_桶) FROM products')
    total_spec = cursor.fetchone()[0] or 0
    
    print(f'规格总计（KG/桶）: {total_spec:,.2f}')
    print(f'单价总计: {total_price:,.2f}')
    
    # 显示前5个产品（展示修正后的规格和单价）
    print('\n前5个产品（修正后）:')
    for i, (_, p) in enumerate(products.head(5).iterrows()):
        print(f'{i+1}. {p["产品型号"]} - {p["产品名称"]}')
        print(f'   规格: {p["规格_KG_桶"]:.1f} KG/桶')
        print(f'   单价: {p["单价"]:.2f} 元')
        print(f'   数量: {p["数量_KG"]:.1f} KG')
    
    conn.close()

if __name__ == "__main__":
    print("=== 修正数据提取（I列=规格，K列=单价） ===")
    
    # 提取修正后的数据
    customer_info, products = extract_corrected_data()
    
    # 创建修正后的数据库
    create_corrected_database(customer_info, products)
    
    # 验证结果
    verify_corrected_database()
    
    print("\n=== 修正完成 ===")
    print("✅ 列索引已修正：I列=规格（KG/桶），K列=单价")
    print("✅ 数据库已更新")
    print("文件：customer_products_corrected.db")