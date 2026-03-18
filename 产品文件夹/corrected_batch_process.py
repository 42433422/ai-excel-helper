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

def extract_customer_info_corrected(file_path, file_name):
    """修正后的客户信息提取"""
    try:
        excel_file = pd.ExcelFile(file_path)
        customer_info = {
            '客户名称': '',
            '联系人': ' ',  # 联系人用空格代替
            '电话': '',
            '供应商名称': '成都国圣工业有限公司',
            '供应商电话': '028-85852618',
            '文件名': file_name
        }
        
        # 遍历所有工作表查找客户信息
        customer_found = False
        
        for sheet_name in excel_file.sheet_names:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                # 查找包含客户信息的行
                for i in range(min(10, len(df))):
                    for j in range(min(3, len(df.columns))):
                        try:
                            cell_value = str(df.iloc[i, j]) if not pd.isna(df.iloc[i, j]) else ""
                            
                            if not customer_found and ('购货单位' in cell_value or '购买单位' in cell_value):
                                # 修正后的客户名称提取逻辑
                                # 格式: 购货单位（乙方）：陈洪强
                                # 或者: 购买单位（甲方）：XXX
                                customer_match = re.search(
                                    r'[购货购买]单位[（(][^）)]*[）)][：:]\s*(.+?)\s*(?:[\s联系人]|$)',
                                    cell_value
                                )
                                if customer_match:
                                    customer_name = customer_match.group(1).strip()
                                    # 确保客户名称不为空
                                    if customer_name and len(customer_name) > 1:
                                        customer_info['客户名称'] = customer_name
                                        customer_found = True
                                        print(f"  ✓ 找到客户名称: {customer_name}")
                                
                                # 提取联系人
                                contact_match = re.search(
                                    r'联系人[：:]\s*(.+?)\s*(?:[\s日期]|$)',
                                    cell_value
                                )
                                if contact_match:
                                    contact = contact_match.group(1).strip()
                                    # 确保联系人不是空的日期或其他内容
                                    if contact and contact != ' ' and not contact[0].isdigit():
                                        customer_info['联系人'] = contact
                                        print(f"  ✓ 找到联系人: {contact}")
                                
                                # 提取订单编号
                                order_match = re.search(
                                    r'订单编号[：:]\s*([^\s联系人日期]+)',
                                    cell_value
                                )
                                if order_match:
                                    order_no = order_match.group(1).strip()
                                    if order_no:
                                        customer_info['订单编号'] = order_no
                                
                                # 提取日期
                                date_match = re.search(
                                    r'(\d{4}年\d{1,2}月\d{1,2}日)',
                                    cell_value
                                )
                                if date_match:
                                    customer_info['日期'] = date_match.group(1)
                            
                        except Exception as e:
                            continue
                    
                    if customer_found:
                        break
                
                if customer_found:
                    break
                    
            except Exception as e:
                continue
        
        # 如果仍然没有找到客户名称，使用文件名
        if not customer_info['客户名称']:
            customer_info['客户名称'] = file_name.replace('.xlsx', '')
            print(f"  ⚠ 未找到客户信息，使用文件名: {customer_info['客户名称']}")
        
        return customer_info
        
    except Exception as e:
        print(f"提取客户信息失败 {file_path}: {str(e)}")
        return None

def extract_products_corrected(file_path, file_name):
    """修正后的产品信息提取"""
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
            if sheet not in product_sheets and len(sheet) < 10:
                product_sheets.append(sheet)
        
        # 处理每个产品工作表
        for sheet_name in product_sheets:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                if len(df) < 2:
                    continue
                
                # 查找数据开始行
                data_start_row = 0
                for i in range(min(10, len(df))):
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
                            
                            if not cell_str or cell_str == 'nan':
                                continue
                            
                            # 尝试识别产品型号
                            if (len(cell_str) < 20 and 
                                not any(char in cell_str for char in ['漆', '剂', '底', '面', '稀释', '固化']) and
                                not cell_str.replace('.', '').replace('-', '').isdigit() and
                                not any(keyword in cell_str for keyword in ['单位', '联系人', '日期', '编号'])):
                                if not product_model:
                                    product_model = cell_str
                            
                            # 尝试识别产品名称
                            elif any(keyword in cell_str for keyword in ['漆', '剂', '底', '面', '稀释', '固化', '白', '黑', '黄', '蓝']):
                                if not product_name:
                                    product_name = cell_str
                            
                            # 尝试识别数值字段
                            try:
                                num_value = float(cell_str)
                                if 0 < num_value < 1000 and not product_model:
                                    product_model = cell_str
                                elif 0 < num_value < 1000 and not quantity_pieces:
                                    quantity_pieces = num_value
                                elif 0 < num_value < 500 and not spec_kg:
                                    spec_kg = num_value
                                elif 0 < num_value < 10000 and not quantity_kg:
                                    quantity_kg = num_value
                                elif 0 < num_value < 10000 and not unit_price:
                                    unit_price = num_value
                                elif num_value > 100 and not amount:
                                    amount = num_value
                            except:
                                if re.match(r'^\d{4}年\d{1,2}月\d{1,2}日', cell_str):
                                    date = cell_str
                                elif len(cell_str) < 10 and re.match(r'^[A-Za-z0-9\-]+$', cell_str):
                                    order_no = cell_str
                        
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
                        continue
                
                if products:
                    break
                    
            except Exception as e:
                continue
        
        return products
        
    except Exception as e:
        print(f"提取产品信息失败 {file_path}: {str(e)}")
        return []

def create_corrected_database():
    """创建修正后的数据库"""
    print("=== 创建修正后的数据库 ===")
    
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
    
    print("修正后的数据库创建完成")

def process_all_files_corrected():
    """修正后批量处理所有文件"""
    print("=== 修正后批量处理所有Excel文件 ===")
    
    # 获取发货单目录下的所有Excel文件
    excel_files = glob.glob('发货单/*.xlsx')
    
    if not excel_files:
        print("未找到Excel文件")
        return
    
    print(f"找到 {len(excel_files)} 个Excel文件")
    
    # 创建数据库
    create_corrected_database()
    
    # 连接数据库
    conn = sqlite3.connect('customer_products_corrected.db')
    cursor = conn.cursor()
    
    processed_files = 0
    total_products = 0
    failed_files = []
    
    # 显示处理进度
    print("\n开始处理文件...")
    print("=" * 80)
    
    for file_path in excel_files:
        file_name = os.path.basename(file_path)
        print(f"\n处理文件: {file_name}")
        
        try:
            # 修正后的客户信息提取
            customer_info = extract_customer_info_corrected(file_path, file_name)
            if not customer_info or not customer_info['客户名称']:
                print(f"  ⚠ 跳过文件 {file_name}: 无法提取客户信息")
                failed_files.append(file_name)
                continue
            
            # 检查客户是否已存在（按客户名称检查）
            cursor.execute('SELECT customer_id FROM customers WHERE 客户名称 = ?', 
                         (customer_info['客户名称'],))
            existing_customer = cursor.fetchone()
            
            if existing_customer:
                customer_id = existing_customer[0]
                print(f"  ✓ 客户已存在: {customer_info['客户名称']}")
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
                print(f"  ✓ 新增客户: {customer_info['客户名称']}")
            
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
            
            # 修正后的产品信息提取
            products = extract_products_corrected(file_path, file_name)
            
            if products:
                # 去重处理（按产品型号，保留最新记录）
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
                print(f"  ✓ 插入产品: {len(latest_products)} 种")
            else:
                print(f"  ⚠ 未找到产品信息")
            
            processed_files += 1
            
        except Exception as e:
            print(f"  ✗ 处理文件失败 {file_name}: {str(e)}")
            failed_files.append(file_name)
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 80)
    print(f"\n=== 修正后批量处理完成 ===")
    print(f"成功处理文件: {processed_files}/{len(excel_files)}")
    print(f"失败文件: {len(failed_files)}")
    if failed_files:
        print("\n失败文件列表:")
        for file in failed_files:
            print(f"  - {file}")
    print(f"总产品数: {total_products}")

def verify_corrected_database():
    """验证修正后的数据库"""
    print("\n=== 验证修正后的数据库 ===")
    
    conn = sqlite3.connect('customer_products_corrected.db')
    
    # 客户统计
    customers = pd.read_sql_query("SELECT * FROM customers", conn)
    print(f"\n客户总数: {len(customers)}")
    
    # 产品统计
    products = pd.read_sql_query("SELECT * FROM products", conn)
    print(f"产品总数: {len(products)}")
    
    # 显示客户列表
    print("\n修正后的客户列表:")
    print("-" * 80)
    for _, customer in customers.iterrows():
        print(f"✓ {customer['客户名称']} ({customer['联系人']}) - {customer['文件名']}")
    print("-" * 80)
    
    # 验证关键客户
    key_customers = ['陈洪强', '中江博郡家私', '七彩乐园家私', '宗南家私', '宜榢家私', '志泓家私', '温总', '澜宇家私']
    print("\n关键客户验证:")
    for customer_name in key_customers:
        found = customers[customers['客户名称'] == customer_name]
        if len(found) > 0:
            print(f"  ✓ {customer_name}")
        else:
            print(f"  ✗ {customer_name} - 未找到!")
    
    # 产品统计
    print(f"\n产品统计:")
    print(f"  - 产品种类: {len(products)} 种")
    print(f"  - 总规格: {products['规格_KG'].sum():,.0f} KG")
    print(f"  - 总重量: {products['数量_KG'].sum():,.0f} KG")
    print(f"  - 总金额: ¥{products['金额'].sum():,.2f}")
    
    conn.close()

if __name__ == "__main__":
    print("=== 修正后批量处理发货单Excel文件 ===")
    print("目标: 正确提取客户名称（从'购货单位（乙方）：XXX'中提取'XXX'）")
    print()
    
    # 修正后批量处理所有Excel文件
    process_all_files_corrected()
    
    # 验证结果
    verify_corrected_database()
    
    print("\n=== 完成 ===")
    print("修正后的数据库文件: customer_products_corrected.db")