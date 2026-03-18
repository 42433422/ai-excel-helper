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

def extract_customer_info_adaptive(file_path, file_name):
    """自适应提取客户信息"""
    try:
        excel_file = pd.ExcelFile(file_path)
        customer_info = {
            '客户名称': '',
            '联系人': ' ',
            '电话': '',
            '供应商名称': '成都国圣工业有限公司',
            '供应商电话': '028-85852618',
            '文件名': file_name
        }
        
        # 尝试不同的策略来获取客户信息
        
        # 策略1: 寻找"尹"工作表
        if '尹' in excel_file.sheet_names:
            df = pd.read_excel(file_path, sheet_name='尹')
            if len(df) > 0:
                customer_text = str(df.iloc[0, 0]) if not pd.isna(df.iloc[0, 0]) else ""
                customer_match = re.search(r'购货单位[：:]([^联系方式]*)', customer_text)
                if customer_match:
                    customer_info['客户名称'] = customer_match.group(1).strip()
        
        # 策略2: 寻找与文件名同名的工作表
        if not customer_info['客户名称']:
            customer_name = file_name.replace('.xlsx', '')
            if customer_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=customer_name)
                
                # 尝试第一行
                if len(df) > 0:
                    for row_idx in [0, 1]:  # 尝试前两行
                        try:
                            row_text = str(df.iloc[row_idx, 0]) if not pd.isna(df.iloc[row_idx, 0]) else ""
                            if '购货单位' in row_text:
                                customer_match = re.search(r'购货单位[：:]([^联系人]*)', row_text)
                                if customer_match:
                                    customer_info['客户名称'] = customer_match.group(1).strip()
                                    break
                                # 尝试提取括号内的信息
                                bracket_match = re.search(r'（[^）]*）', row_text)
                                if bracket_match:
                                    customer_info['客户名称'] = bracket_match.group(0).strip('（）')
                                    break
                                    
                            # 如果没有"购货单位"，尝试从文件名提取
                            if not customer_info['客户名称']:
                                customer_info['客户名称'] = customer_name
                        except:
                            continue
                        
                        # 如果还没找到客户名称，使用文件名
                        if not customer_info['客户名称']:
                            customer_info['客户名称'] = customer_name
        
        # 策略3: 寻找"出货"工作表，查找客户信息
        if not customer_info['客户名称'] and '出货' in excel_file.sheet_names:
            df = pd.read_excel(file_path, sheet_name='出货')
            if len(df) > 0:
                # 查找第一列的客户信息
                for i in range(min(10, len(df))):
                    try:
                        cell_value = str(df.iloc[i, 0]) if not pd.isna(df.iloc[i, 0]) else ""
                        if cell_value and len(cell_value) > 1 and not cell_value.isdigit():
                            customer_info['客户名称'] = cell_value.strip()
                            break
                    except:
                        continue
        
        # 策略4: 如果仍然没有客户名称，使用文件名
        if not customer_info['客户名称']:
            customer_info['客户名称'] = file_name.replace('.xlsx', '')
        
        # 提取联系人信息
        contact_text = ''
        for sheet in excel_file.sheet_names:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet)
                for i in range(min(5, len(df))):
                    for j in range(min(5, len(df.columns))):
                        try:
                            cell_value = str(df.iloc[i, j]) if not pd.isna(df.iloc[i, j]) else ""
                            if '联系人' in cell_value:
                                contact_match = re.search(r'联系人[：:]([^日期]*)', cell_value)
                                if contact_match:
                                    contact_text = contact_match.group(1).strip()
                                    break
                        except:
                            continue
                    if contact_text:
                        break
                if contact_text:
                    break
            except:
                continue
        
        if contact_text:
            customer_info['联系人'] = contact_text
        
        # 提取订单信息
        for sheet in excel_file.sheet_names:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet)
                for i in range(min(5, len(df))):
                    for j in range(min(5, len(df.columns))):
                        try:
                            cell_value = str(df.iloc[i, j]) if not pd.isna(df.iloc[i, j]) else ""
                            if '订单编号' in cell_value:
                                order_match = re.search(r'订单编号[：:]([^联系方式]*?)$', cell_value)
                                if order_match:
                                    customer_info['订单编号'] = order_match.group(1).strip()
                                    break
                                    
                            if re.search(r'(\d{4}年\d{2}月\d{2}日)', cell_value):
                                date_match = re.search(r'(\d{4}年\d{2}月\d{2}日)', cell_value)
                                if date_match:
                                    customer_info['日期'] = date_match.group(1)
                                    break
                        except:
                            continue
            except:
                continue
        
        return customer_info
        
    except Exception as e:
        print(f"提取客户信息失败 {file_path}: {str(e)}")
        return None

def extract_products_adaptive(file_path, file_name):
    """自适应提取产品信息"""
    try:
        products = []
        excel_file = pd.ExcelFile(file_path)
        
        # 尝试不同的工作表来获取产品数据
        product_sheets = []
        
        # 优先顺序：出货 -> 客户名 -> 第一个工作表
        if '出货' in excel_file.sheet_names:
            product_sheets.append('出货')
        
        customer_name = file_name.replace('.xlsx', '')
        if customer_name in excel_file.sheet_names:
            product_sheets.append(customer_name)
        
        # 添加其他可能包含产品数据的工作表
        for sheet in excel_file.sheet_names:
            if sheet not in product_sheets and len(sheet) < 10:  # 避免过长的表名
                product_sheets.append(sheet)
        
        # 处理每个产品工作表
        for sheet_name in product_sheets:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                if len(df) < 2:  # 跳过空表或过小的表
                    continue
                
                # 查找数据开始行
                data_start_row = 0
                for i in range(min(10, len(df))):
                    # 查找包含产品相关标题的行
                    row_has_headers = False
                    for j in range(min(10, len(df.columns))):
                        cell_value = str(df.iloc[i, j]) if not pd.isna(df.iloc[i, j]) else ""
                        if any(keyword in cell_value for keyword in ['产品型号', '产品名称', '数量', '规格', '单价']):
                            row_has_headers = True
                            break
                    if row_has_headers:
                        data_start_row = i + 1
                        break
                
                # 提取产品数据
                for index in range(data_start_row, len(df)):
                    try:
                        row = df.iloc[index]
                        
                        # 跳过空行或标题行
                        if index == data_start_row - 1:
                            continue
                        
                        product = {}
                        
                        # 尝试不同的列布局
                        product_model = None
                        product_name = None
                        quantity_pieces = 0.0
                        spec_kg = 0.0
                        quantity_kg = 0.0
                        unit_price = 0.0
                        amount = 0.0
                        date = None
                        order_no = None
                        
                        # 遍历所有列寻找产品信息
                        for j in range(len(df.columns)):
                            cell_value = row.iloc[j] if j < len(row) else None
                            
                            if pd.isna(cell_value):
                                continue
                            
                            cell_str = str(cell_value).strip()
                            
                            # 跳过空值
                            if not cell_str or cell_str == 'nan':
                                continue
                            
                            # 尝试识别产品型号（通常是比较短的字母数字组合）
                            if (len(cell_str) < 20 and 
                                not any(char in cell_str for char in ['漆', '剂', '底', '面', '稀释', '固化']) and
                                not cell_str.replace('.', '').replace('-', '').isdigit() and
                                not any(keyword in cell_str for keyword in ['单位', '联系人', '日期', '编号'])):
                                if not product_model:
                                    product_model = cell_str
                            
                            # 尝试识别产品名称（通常包含特定关键词）
                            elif any(keyword in cell_str for keyword in ['漆', '剂', '底', '面', '稀释', '固化', '白', '黑', '黄', '蓝']):
                                if not product_name:
                                    product_name = cell_str
                            
                            # 尝试识别数值字段
                            try:
                                num_value = float(cell_str)
                                # 根据位置和大小推断字段类型
                                if 0 < num_value < 1000 and not product_model:  # 可能是产品型号
                                    product_model = cell_str
                                elif 0 < num_value < 1000 and not quantity_pieces:  # 可能是数量/件
                                    quantity_pieces = num_value
                                elif 0 < num_value < 500 and not spec_kg:  # 可能是规格/KG
                                    spec_kg = num_value
                                elif 0 < num_value < 10000 and not quantity_kg:  # 可能是数量/KG
                                    quantity_kg = num_value
                                elif 0 < num_value < 10000 and not unit_price:  # 可能是单价
                                    unit_price = num_value
                                elif num_value > 100 and not amount:  # 可能是金额
                                    amount = num_value
                            except:
                                # 检查是否为日期或单号
                                if re.match(r'^\d{4}年\d{2}月\d{2}日', cell_str):
                                    date = cell_str
                                elif re.match(r'^\d+$', cell_str) and 10 < len(cell_str) < 50:
                                    order_no = cell_str
                                elif len(cell_str) < 10 and re.match(r'^[A-Za-z0-9\-]+$', cell_str):
                                    order_no = cell_str
                        
                        # 只有当有基本的产品信息时才添加
                        if product_model or product_name:
                            product['产品型号'] = product_model if product_model else ''
                            product['产品名称'] = product_name if product_name else ''
                            product['数量_件'] = quantity_pieces
                            product['规格_KG'] = spec_kg
                            product['数量_KG'] = quantity_kg
                            product['单价'] = unit_price
                            product['金额'] = amount
                            product['日期'] = date
                            product['单号'] = order_no
                            product['记录顺序'] = index
                            product['来源'] = f'{sheet_name}-{file_name}'
                            
                            products.append(product)
                    
                    except Exception as e:
                        continue  # 跳过有问题的行
                
                if products:  # 如果找到了产品数据，就不再处理其他表
                    break
                    
            except Exception as e:
                continue  # 跳过有问题的表
        
        return products
        
    except Exception as e:
        print(f"提取产品信息失败 {file_path}: {str(e)}")
        return []

def create_unified_database():
    """创建统一的数据库"""
    print("=== 创建统一数据库 ===")
    
    # 删除旧数据库
    try:
        os.remove('customer_products_unified.db')
    except:
        pass
    
    # 连接到新的SQLite数据库
    conn = sqlite3.connect('customer_products_unified.db')
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
    cursor.execute('CREATE INDEX idx_products_source ON products (来源)')
    
    conn.commit()
    conn.close()
    
    print("统一数据库创建完成")

def process_all_files_unified():
    """统一处理所有文件"""
    print("=== 统一处理所有Excel文件 ===")
    
    # 获取发货单目录下的所有Excel文件
    excel_files = glob.glob('发货单/*.xlsx')
    
    if not excel_files:
        print("未找到Excel文件")
        return
    
    print(f"找到 {len(excel_files)} 个Excel文件")
    
    # 创建数据库
    create_unified_database()
    
    # 连接数据库
    conn = sqlite3.connect('customer_products_unified.db')
    cursor = conn.cursor()
    
    processed_files = 0
    total_products = 0
    failed_files = []
    
    for file_path in excel_files:
        file_name = os.path.basename(file_path)
        print(f"\n处理文件: {file_name}")
        
        try:
            # 自适应提取客户信息
            customer_info = extract_customer_info_adaptive(file_path, file_name)
            if not customer_info or not customer_info['客户名称']:
                print(f"跳过文件 {file_name}: 无法提取客户信息")
                failed_files.append(file_name)
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
            
            # 自适应提取产品信息
            products = extract_products_adaptive(file_path, file_name)
            
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
            else:
                print("未找到产品信息")
            
            processed_files += 1
            
        except Exception as e:
            print(f"处理文件失败 {file_name}: {str(e)}")
            failed_files.append(file_name)
    
    conn.commit()
    conn.close()
    
    print(f"\n=== 统一处理完成 ===")
    print(f"成功处理文件: {processed_files}/{len(excel_files)}")
    print(f"失败文件: {len(failed_files)}")
    if failed_files:
        print("失败文件列表:")
        for file in failed_files:
            print(f"  - {file}")
    print(f"总产品数: {total_products}")

def verify_unified_database():
    """验证统一处理后的数据库"""
    print("\n=== 验证统一数据库 ===")
    
    conn = sqlite3.connect('customer_products_unified.db')
    
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
    
    # 按来源统计
    print("\n按来源统计:")
    source_stats = products.groupby('来源').size()
    for source, count in source_stats.items():
        print(f"  - {source}: {count} 种产品")
    
    # 产品统计
    print(f"\n产品统计:")
    print(f"  - 产品种类: {len(products)} 种")
    print(f"  - 总规格: {products['规格_KG'].sum():,.0f} KG")
    print(f"  - 总重量: {products['数量_KG'].sum():,.0f} KG")
    print(f"  - 总金额: ¥{products['金额'].sum():,.2f}")
    
    conn.close()

if __name__ == "__main__":
    print("=== 统一批量处理发货单Excel文件 ===")
    
    # 统一处理所有Excel文件
    process_all_files_unified()
    
    # 验证结果
    verify_unified_database()
    
    print("\n=== 完成 ===")
    print("统一数据库文件: customer_products_unified.db")