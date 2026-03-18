#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import sqlite3
from datetime import datetime
import re
import os

def safe_float(value):
    """安全转换为浮点数"""
    try:
        if pd.isna(value):
            return 0.0
        if isinstance(value, str):
            # 移除非数字字符
            cleaned = re.sub(r'[^\d.-]', '', value)
            if cleaned:
                return float(cleaned)
            else:
                return 0.0
        return float(value)
    except (ValueError, TypeError):
        return 0.0

def create_database_schema():
    """创建数据库结构"""
    print('=== 第三步：创建数据库结构 ===')
    
    # 连接到SQLite数据库
    conn = sqlite3.connect('customer_products.db')
    cursor = conn.cursor()
    
    # 创建客户表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
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
        CREATE TABLE IF NOT EXISTS orders (
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
    
    # 创建产品表（核心表）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
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
    
    # 创建产品历史表（保留所有历史记录）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products_history (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            客户ID INTEGER,
            产品型号 TEXT,
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
            FOREIGN KEY (客户ID) REFERENCES customers (customer_id)
        )
    ''')
    
    # 创建索引以提高查询性能
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_customer ON products (客户ID)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_model ON products (产品型号)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_order ON products (订单ID)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_products_history_customer ON products_history (客户ID)')
    
    conn.commit()
    conn.close()
    
    print("数据库结构创建完成！")
    return True

def insert_customer_data(customer_info):
    """插入客户数据"""
    print('\n=== 插入客户数据 ===')
    
    conn = sqlite3.connect('customer_products.db')
    cursor = conn.cursor()
    
    # 先检查客户是否已存在
    cursor.execute('SELECT customer_id FROM customers WHERE 客户名称 = ?', 
                  (customer_info.get('客户名称', ''),))
    existing_customer = cursor.fetchone()
    
    if existing_customer:
        # 更新现有客户
        customer_id = existing_customer[0]
        cursor.execute('''
            UPDATE customers 
            SET 联系人 = ?, 供应商名称 = ?, 供应商电话 = ?, 更新时间 = CURRENT_TIMESTAMP
            WHERE customer_id = ?
        ''', (
            customer_info.get('联系人', ''),
            customer_info.get('供应商名称', ''),
            customer_info.get('电话', ''),
            customer_id
        ))
    else:
        # 插入新客户
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
    
    # 插入订单信息
    cursor.execute('''
        INSERT INTO orders (客户ID, 订单编号, 订单日期)
        VALUES (?, ?, ?)
    ''', (
        customer_id,
        customer_info.get('订单编号', ''),
        customer_info.get('日期', '')
    ))
    
    # 获取订单ID
    order_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    print(f"客户信息已插入，客户ID: {customer_id}, 订单ID: {order_id}")
    return customer_id, order_id

def insert_products_with_latest_priority(products, customer_id, order_id):
    """插入产品数据，实现最新记录优先"""
    print('\n=== 第五步：实现最新记录优先的数据插入逻辑 ===')
    
    conn = sqlite3.connect('customer_products.db')
    cursor = conn.cursor()
    
    # 首先将所有记录插入历史表
    for product in products:
        cursor.execute('''
            INSERT INTO products_history (
                客户ID, 产品型号, 产品名称, 规格_KG, 数量_KG, 数量_件,
                单价, 金额, 单号, 记录顺序, 来源
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            customer_id,
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
    
    # 删除现有产品记录（如果存在）
    cursor.execute('DELETE FROM products WHERE 客户ID = ?', (customer_id,))
    
    # 按记录顺序分组，选择每个产品型号的最新记录
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
    
    print(f"产品数据插入完成，共 {len(products)} 条记录（包含历史记录）")

def extract_customer_info():
    """提取客户信息"""
    print('=== 提取客户信息 ===')
    
    df = pd.read_excel('e:\\女娲1号\\发货单\\尹玉华1.xlsx', sheet_name='尹')
    
    customer_info = {}
    
    if len(df) > 0:
        customer_row = df.iloc[0]
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
    
    for i in range(len(df)):
        for j in range(len(df.columns)):
            cell_value = df.iloc[i, j]
            if not pd.isna(cell_value) and isinstance(cell_value, str):
                if '成都国圣工业有限公司' in cell_value:
                    customer_info['供应商名称'] = '成都国圣工业有限公司'
                    customer_info['电话'] = '028-85852618'
                    break
    
    return customer_info

def extract_product_info():
    """提取产品信息"""
    print('\n=== 提取产品信息 ===')
    
    df_出货 = pd.read_excel('e:\\女娲1号\\发货单\\尹玉华1.xlsx', sheet_name='出货')
    df_尹 = pd.read_excel('e:\\女娲1号\\发货单\\尹玉华1.xlsx', sheet_name='尹')
    
    products = []
    
    # 从出货工作表提取产品
    for index, row in df_出货.iterrows():
        if index == 0 or index == 1:
            continue
            
        product = {}
        
        if not pd.isna(row.iloc[3]):
            product['产品型号'] = str(row.iloc[3]).strip()
        else:
            continue
            
        if not pd.isna(row.iloc[6]):
            product['产品名称'] = str(row.iloc[6]).strip()
            
        if not pd.isna(row.iloc[8]):
            product['规格_KG'] = safe_float(row.iloc[8])
            
        if not pd.isna(row.iloc[10]):
            product['数量_KG'] = safe_float(row.iloc[10])
            
        if not pd.isna(row.iloc[11]):
            product['单价'] = safe_float(row.iloc[11])
            
        if not pd.isna(row.iloc[12]):
            product['金额'] = safe_float(row.iloc[12])
            
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
        尹_product['产品型号'] = str(df_尹.iloc[3, 0]).strip() if not pd.isna(df_尹.iloc[3, 0]) else ""
        尹_product['产品名称'] = str(df_尹.iloc[3, 3]).strip() if not pd.isna(df_尹.iloc[3, 3]) else ""
        尹_product['数量_件'] = safe_float(df_尹.iloc[3, 4])
        尹_product['规格_KG'] = safe_float(df_尹.iloc[3, 5])
        尹_product['数量_KG'] = safe_float(df_尹.iloc[3, 6])
        尹_product['单价'] = safe_float(df_尹.iloc[3, 7])
        尹_product['金额'] = safe_float(df_尹.iloc[3, 8])
        尹_product['来源'] = '发货单'
        尹_product['记录顺序'] = 9999
        
        products.append(尹_product)
    
    return products

def deduplicate_products(products):
    """去重处理，保留最新记录"""
    print('\n=== 去重处理 ===')
    
    latest_products = {}
    
    for product in products:
        model = product.get('产品型号', '')
        if model:
            record_order = product.get('记录顺序', 0)
            
            if model not in latest_products or record_order > latest_products[model]['记录顺序']:
                latest_products[model] = product
    
    deduplicated = list(latest_products.values())
    print(f"去重前：{len(products)} 条记录")
    print(f"去重后：{len(deduplicated)} 条记录")
    
    return deduplicated

if __name__ == "__main__":
    print("=== 以客户为核心的产品数据库创建系统 ===")
    
    # 执行完整流程
    customer_info = extract_customer_info()
    products = extract_product_info()
    latest_products = deduplicate_products(products)
    
    # 创建数据库
    create_database_schema()
    
    # 插入客户数据
    customer_id, order_id = insert_customer_data(customer_info)
    
    # 插入产品数据
    insert_products_with_latest_priority(latest_products, customer_id, order_id)
    
    print(f"\n=== 任务完成 ===")
    print(f"客户：{customer_info.get('客户名称', 'N/A')} (ID: {customer_id})")
    print(f"订单：{customer_info.get('订单编号', 'N/A')} (ID: {order_id})")
    print(f"产品种类：{len(latest_products)} 种")
    print("数据库文件：customer_products.db")