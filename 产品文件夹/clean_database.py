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

def clean_database():
    """清理数据库中的异常数据"""
    print('=== 清理数据库异常数据 ===')
    
    conn = sqlite3.connect('customer_products.db')
    cursor = conn.cursor()
    
    # 清理产品表
    cursor.execute('''
        UPDATE products 
        SET 金额 = 0, 单价 = 0 
        WHERE 金额 > 100000 OR 单价 > 100000
    ''')
    
    # 清理历史表
    cursor.execute('''
        UPDATE products_history 
        SET 金额 = 0, 单价 = 0 
        WHERE 金额 > 100000 OR 单价 > 100000
    ''')
    
    # 删除中文描述的记录
    cursor.execute('''
        DELETE FROM products_history 
        WHERE 产品名称 LIKE '%做%' OR 产品名称 LIKE '%的%' OR 产品名称 LIKE '%模板%'
    ''')
    
    conn.commit()
    
    print("异常数据清理完成")
    
    # 重新统计
    cursor.execute('SELECT COUNT(*) FROM products')
    product_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM products_history')
    history_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT SUM(金额) FROM products')
    total_amount = cursor.fetchone()[0] or 0
    
    cursor.execute('SELECT SUM(数量_KG) FROM products')
    total_quantity = cursor.fetchone()[0] or 0
    
    conn.close()
    
    print(f"清理后统计：")
    print(f"  - 产品种类：{product_count}")
    print(f"  - 历史记录：{history_count}")
    print(f"  - 总金额：{total_amount:,.2f} 元")
    print(f"  - 总数量：{total_quantity:,.2f} KG")

def create_clean_database():
    """创建干净的数据库"""
    print('\n=== 创建干净的数据库 ===')
    
    # 删除旧数据库
    try:
        os.remove('customer_products_clean.db')
    except:
        pass
    
    # 连接到新的SQLite数据库
    conn = sqlite3.connect('customer_products_clean.db')
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
    
    # 创建产品表
    cursor.execute('''
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            客户ID INTEGER,
            订单ID INTEGER,
            产品型号 TEXT NOT NULL,
            产品名称 TEXT,
            规格_KG REAL DEFAULT 0.0,
            数量_KG REAL DEFAULT 0.0,
            数量_件 REAL DEFAULT 0.0,
            单价 REAL DEFAULT 0.0,
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
    conn.close()
    print("干净数据库创建完成")

def extract_clean_data():
    """提取干净的数据"""
    print('\n=== 提取干净数据 ===')
    
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
    
    # 产品信息
    df_出货 = pd.read_excel('e:\\女娲1号\\发货单\\尹玉华1.xlsx', sheet_name='出货')
    products = []
    
    for index, row in df_出货.iterrows():
        if index == 0 or index == 1:
            continue
            
        product = {}
        
        if not pd.isna(row.iloc[3]):
            model = str(row.iloc[3]).strip()
            # 跳过包含中文的产品型号
            if any(ord(char) > 127 for char in model):
                continue
            product['产品型号'] = model
        else:
            continue
            
        if not pd.isna(row.iloc[6]):
            name = str(row.iloc[6]).strip()
            # 跳过包含异常描述的产品名称
            if '做' in name or '模板' in name or '的' in name:
                continue
            product['产品名称'] = name
            
        product['规格_KG'] = safe_float_with_limit(row.iloc[8])
        product['数量_KG'] = safe_float_with_limit(row.iloc[10])
        product['单价'] = safe_float_with_limit(row.iloc[11])
        product['金额'] = safe_float_with_limit(row.iloc[12])
        
        if not pd.isna(row.iloc[1]):
            product['日期'] = row.iloc[1]
            
        if not pd.isna(row.iloc[2]):
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
            尹_product['规格_KG'] = safe_float_with_limit(df_尹.iloc[3, 5])
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

def insert_clean_data(customer_info, products):
    """插入干净的数据"""
    print('\n=== 插入干净数据 ===')
    
    conn = sqlite3.connect('customer_products_clean.db')
    cursor = conn.cursor()
    
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
                客户ID, 订单ID, 产品型号, 产品名称, 规格_KG, 数量_KG, 数量_件,
                单价, 金额, 单号, 记录顺序, 来源
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            customer_id,
            order_id,
            product.get('产品型号', ''),
            product.get('产品名称', ''),
            product.get('规格_KG', 0.0),
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
    
    print(f"干净数据插入完成：{len(products)} 种产品")

if __name__ == "__main__":
    print("=== 数据库清理和重建 ===")
    
    # 清理原数据库
    clean_database()
    
    # 创建新数据库
    create_clean_database()
    
    # 提取和插入干净数据
    customer_info, products = extract_clean_data()
    insert_clean_data(customer_info, products)
    
    print("\n=== 任务完成 ===")
    print("✅ 异常数据已清理")
    print("✅ 新数据库已创建")
    print("✅ 干净数据已导入")
    print("文件：customer_products_clean.db")