#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import sqlite3
import os
import re
from datetime import datetime
import glob

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

def extract_customer_info_from_file(file_path, file_name):
    """从Excel文件中提取客户信息"""
    try:
        df = pd.read_excel(file_path, sheet_name='尹')
        
        customer_info = {
            '客户名称': '',
            '联系人': ' ',  # 联系人用空格代替
            '电话': '',
            '供应商名称': '成都国圣工业有限公司',
            '供应商电话': '028-85852618',
            '文件名': file_name
        }
        
        # 从第1行提取客户信息
        if len(df) > 0:
            customer_row = df.iloc[0]
            customer_text = str(customer_row.iloc[0]) if not pd.isna(customer_row.iloc[0]) else ""
            
            # 提取客户名称
            customer_match = re.search(r'购货单位：([^联系方式]*)', customer_text)
            if customer_match:
                customer_info['客户名称'] = customer_match.group(1).strip()
            else:
                # 如果没有找到，尝试从文件名提取
                customer_info['客户名称'] = file_name.replace('.xlsx', '')
            
            # 提取联系人
            contact_match = re.search(r'联系人：([^日期]*?)(\s|$)', customer_text)
            if contact_match:
                contact = contact_match.group(1).strip()
                if contact:  # 如果有联系人信息
                    customer_info['联系人'] = contact
            
            # 提取日期
            date_match = re.search(r'(\d{4}年\d{2}月\d{2}日)', customer_text)
            if date_match:
                customer_info['日期'] = date_match.group(1)
            else:
                customer_info['日期'] = ''
            
            # 提取订单编号
            order_match = re.search(r'订单编号：([^联系方式]*?)$', customer_text)
            if order_match:
                customer_info['订单编号'] = order_match.group(1).strip()
            else:
                customer_info['订单编号'] = ''
        
        # 从其他行查找公司信息
        for i in range(len(df)):
            for j in range(len(df.columns)):
                cell_value = df.iloc[i, j]
                if not pd.isna(cell_value) and isinstance(cell_value, str):
                    if '成都国圣工业有限公司' in cell_value:
                        customer_info['供应商名称'] = '成都国圣工业有限公司'
                        customer_info['供应商电话'] = '028-85852618'
                        break
        
        return customer_info
        
    except Exception as e:
        print(f"提取客户信息失败 {file_path}: {str(e)}")
        return None

def extract_products_from_file(file_path, file_name):
    """从Excel文件中提取产品信息"""
    try:
        products = []
        
        # 读取出货记录
        df_出货 = pd.read_excel(file_path, sheet_name='出货')
        
        # 读取尹工作表
        df_尹 = pd.read_excel(file_path, sheet_name='尹')
        
        # 从出货工作表提取产品
        for index, row in df_出货.iterrows():
            if index == 0 or index == 1:
                continue
                
            product = {}
            
            # 产品型号（列4，索引3）
            if not pd.isna(row.iloc[3]):
                model = str(row.iloc[3]).strip()
                if any(ord(char) > 127 for char in model):
                    continue
                product['产品型号'] = model
            else:
                continue
                
            # 产品名称（列7，索引6）
            if not pd.isna(row.iloc[6]):
                name = str(row.iloc[6]).strip()
                if '做' in name or '模板' in name or '的' in name:
                    continue
                product['产品名称'] = name
                
            # 数量/件（列8，索引7）
            product['数量_件'] = safe_float_with_limit(row.iloc[7])
            
            # 规格/KG（列9，索引8）I列
            product['规格_KG'] = safe_float_with_limit(row.iloc[8])
            
            # 数量/KG（列10，索引9）
            product['数量_KG'] = safe_float_with_limit(row.iloc[9])
            
            # 单价/元（列11，索引10）K列
            product['单价'] = safe_float_with_limit(row.iloc[10])
            
            # 金额/元（列12，索引11）
            product['金额'] = safe_float_with_limit(row.iloc[11])
            
            if not pd.isna(row.iloc[1]):  # 日期
                product['日期'] = row.iloc[1]
                
            if not pd.isna(row.iloc[2]):  # 单号
                product['单号'] = str(row.iloc[2])
                
            product['记录顺序'] = index
            product['来源'] = f'出货记录-{file_name}'
            
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
                尹_product['来源'] = f'发货单-{file_name}'
                尹_product['记录顺序'] = 9999
                
                products.append(尹_product)
        
        return products
        
    except Exception as e:
        print(f"提取产品信息失败 {file_path}: {str(e)}")
        return []

def create_batch_database():
    """创建批量处理后的数据库"""
    print("=== 创建批量数据库 ===")
    
    # 删除旧数据库
    try:
        os.remove('customer_products_batch.db')
    except:
        pass
    
    # 连接到新的SQLite数据库
    conn = sqlite3.connect('customer_products_batch.db')
    cursor = conn.cursor()
    
    # 创建客户表
    cursor.execute('''
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            客户名称 TEXT NOT NULL,
            联系人 TEXT,
            电话 TEXT,
            地址 TEXT,
            供应商名称 TEXT,
            供应商电话 TEXT,
            文件名 TEXT,
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
            数量_件 REAL DEFAULT 0.0,
            规格_KG REAL DEFAULT 0.0,
            数量_KG REAL DEFAULT 0.0,
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
    cursor.execute('CREATE INDEX idx_customers_name ON customers (客户名称)')
    
    conn.commit()
    conn.close()
    
    print("批量数据库创建完成")

def process_all_excel_files():
    """批量处理所有Excel文件"""
    print("=== 批量处理Excel文件 ===")
    
    # 获取发货单目录下的所有Excel文件
    excel_files = glob.glob('发货单/*.xlsx')
    
    if not excel_files:
        print("未找到Excel文件")
        return
    
    print(f"找到 {len(excel_files)} 个Excel文件")
    
    # 创建数据库
    create_batch_database()
    
    # 连接数据库
    conn = sqlite3.connect('customer_products_batch.db')
    cursor = conn.cursor()
    
    processed_files = 0
    total_products = 0
    
    for file_path in excel_files:
        file_name = os.path.basename(file_path)
        print(f"\n处理文件: {file_name}")
        
        try:
            # 提取客户信息
            customer_info = extract_customer_info_from_file(file_path, file_name)
            if not customer_info or not customer_info['客户名称']:
                print(f"跳过文件 {file_name}: 无法提取客户信息")
                continue
            
            # 检查客户是否已存在
            cursor.execute('SELECT customer_id FROM customers WHERE 客户名称 = ?', 
                         (customer_info['客户名称'],))
            existing_customer = cursor.fetchone()
            
            if existing_customer:
                customer_id = existing_customer[0]
                print(f"客户已存在: {customer_info['客户名称']}")
            else:
                # 插入新客户
                cursor.execute('''
                    INSERT INTO customers (客户名称, 联系人, 电话, 供应商名称, 供应商电话, 文件名)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    customer_info['客户名称'],
                    customer_info['联系人'],
                    customer_info.get('电话', ''),
                    customer_info['供应商名称'],
                    customer_info['供应商电话'],
                    file_name
                ))
                customer_id = cursor.lastrowid
                print(f"新增客户: {customer_info['客户名称']}")
            
            # 插入订单信息
            cursor.execute('''
                INSERT INTO orders (客户ID, 订单编号, 订单日期)
                VALUES (?, ?, ?)
            ''', (
                customer_id,
                customer_info.get('订单编号', ''),
                customer_info.get('日期', '')
            ))
            order_id = cursor.lastrowid
            
            # 提取产品信息
            products = extract_products_from_file(file_path, file_name)
            
            if products:
                # 去重处理
                latest_products = {}
                for product in products:
                    model = product.get('产品型号', '')
                    if model:
                        record_order = product.get('记录顺序', 0)
                        
                        if model not in latest_products or record_order > latest_products[model]['记录顺序']:
                            latest_products[model] = product
                
                # 插入产品
                for product in latest_products.values():
                    cursor.execute('''
                        INSERT INTO products (
                            客户ID, 订单ID, 产品型号, 产品名称, 数量_件, 规格_KG, 数量_KG,
                            单价, 金额, 单号, 记录顺序, 来源
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        customer_id,
                        order_id,
                        product.get('产品型号', ''),
                        product.get('产品名称', ''),
                        product.get('数量_件', 0.0),
                        product.get('规格_KG', 0.0),
                        product.get('数量_KG', 0.0),
                        product.get('单价', 0.0),
                        product.get('金额', 0.0),
                        product.get('单号', ''),
                        product.get('记录顺序', 0),
                        product.get('来源', '出货记录')
                    ))
                
                total_products += len(latest_products)
                print(f"插入产品: {len(latest_products)} 种")
            
            processed_files += 1
            
        except Exception as e:
            print(f"处理文件失败 {file_name}: {str(e)}")
    
    conn.commit()
    conn.close()
    
    print(f"\n=== 批量处理完成 ===")
    print(f"成功处理文件: {processed_files}/{len(excel_files)}")
    print(f"总产品数: {total_products}")

def verify_batch_database():
    """验证批量处理后的数据库"""
    print("\n=== 验证批量数据库 ===")
    
    conn = sqlite3.connect('customer_products_batch.db')
    
    # 客户统计
    customers = pd.read_sql_query("SELECT * FROM customers", conn)
    print(f"客户总数: {len(customers)}")
    
    # 产品统计
    products = pd.read_sql_query("SELECT * FROM products", conn)
    print(f"产品总数: {len(products)}")
    
    # 显示客户列表
    print("\n客户列表:")
    for _, customer in customers.iterrows():
        print(f"  - {customer['客户名称']} ({customer['联系人']}) - {customer['文件名']}")
    
    # 按文件统计
    print("\n按文件统计:")
    file_stats = customers.groupby('文件名').size()
    for file_name, count in file_stats.items():
        print(f"  - {file_name}: {count} 个客户")
    
    # 产品统计
    print(f"\n产品统计:")
    print(f"  - 产品种类: {len(products)} 种")
    print(f"  - 总规格: {products['规格_KG'].sum():,.0f} KG")
    print(f"  - 总重量: {products['数量_KG'].sum():,.0f} KG")
    print(f"  - 总金额: ¥{products['金额'].sum():,.2f}")
    
    conn.close()

if __name__ == "__main__":
    print("=== 批量处理发货单Excel文件 ===")
    
    # 批量处理所有Excel文件
    process_all_excel_files()
    
    # 验证结果
    verify_batch_database()
    
    print("\n=== 完成 ===")
    print("批量数据库文件: customer_products_batch.db")