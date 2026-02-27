#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import sqlite3
import os
import re
from datetime import datetime
import glob

def safe_float(value):
    """安全转换为浮点数"""
    try:
        if pd.isna(value):
            return 0.0
        if isinstance(value, str):
            # 移除非数字字符，但保留小数点和负号
            cleaned = re.sub(r'[^\d.-]', '', value)
            if cleaned and cleaned.replace('-', '').replace('.', '').isdigit():
                return float(cleaned)
            return 0.0
        return float(value)
    except:
        return 0.0

def detect_column_layout(df, file_name):
    """检测列布局并返回列索引映射"""
    col_mapping = {
        '产品型号': None,
        '产品名称': None,
        '数量_件': None,
        '规格_KG': None,
        '数量_KG': None,
        '单价': None,
        '金额': None,
        '标题行': 0,
        '数据起始行': 1
    }
    
    # 查找标题行（包含'产品型号'、'产品名称'等关键字的行）
    title_row = 0
    for i in range(min(5, len(df))):
        row_str = ' '.join([str(df.iloc[i, j]) for j in range(min(10, len(df.columns)))])
        if any(keyword in row_str for keyword in ['产品型号', '产品名称', '数量/件', '规格/KG', '单价/元']):
            title_row = i
            break
    
    col_mapping['标题行'] = title_row
    col_mapping['数据起始行'] = title_row + 1
    
    # 遍历该行的所有列，识别标题
    for j in range(len(df.columns)):
        try:
            cell_value = str(df.iloc[title_row, j]) if j < len(df.columns) else ''
            cell_value_lower = cell_value.lower()
            
            # 识别列类型
            if '产品型号' in cell_value:
                col_mapping['产品型号'] = j
            elif '产品名称' in cell_value:
                col_mapping['产品名称'] = j
            elif '数量/件' in cell_value or (cell_value_lower == '数量' and 'kg' not in cell_value_lower):
                col_mapping['数量_件'] = j
            elif '规格' in cell_value and 'kg' in cell_value_lower:
                col_mapping['规格_KG'] = j
            elif '数量' in cell_value and 'kg' in cell_value_lower:
                col_mapping['数量_KG'] = j
            elif '单价' in cell_value and '元' in cell_value:
                col_mapping['单价'] = j
            elif '金额' in cell_value or '合计' in cell_value:
                col_mapping['金额'] = j
        except:
            continue
    
    # 如果没有找到标题行，尝试根据数据结构推断
    if all(v is None for v in [col_mapping['产品型号'], col_mapping['产品名称'], col_mapping['数量_件']]):
        # 尝试根据值的内容推断列
        print(f"  ⚠ 未找到标题行，使用数据推断...")
        for j in range(len(df.columns)):
            sample_values = []
            for i in range(title_row, min(title_row + 5, len(df))):
                if j < len(df.columns):
                    sample_values.append(str(df.iloc[i, j]))
            
            sample_str = ' '.join(sample_values)
            
            # 产品型号通常是短的字母数字组合
            if any(char.isalpha() for char in sample_str) and len(sample_str) < 30:
                if col_mapping['产品型号'] is None:
                    col_mapping['产品型号'] = j
                    continue
            
            # 产品名称通常包含中文油漆相关词汇
            if any(keyword in sample_str for keyword in ['漆', '剂', '底', '面', '固化', '稀释', '树脂']):
                if col_mapping['产品名称'] is None:
                    col_mapping['产品名称'] = j
                    continue
    
    return col_mapping

def extract_products_adaptive(file_path, file_name):
    """自适应提取产品信息"""
    try:
        products = []
        excel_file = pd.ExcelFile(file_path)
        
        # 获取产品工作表
        product_sheets = []
        
        # 优先查找包含"出货"的工作表
        for sheet in excel_file.sheet_names:
            if '出货' in sheet:
                product_sheets.append(sheet)
        
        # 如果没有"出货"表，尝试文件名同名的表
        customer_name = file_name.replace('.xlsx', '')
        if customer_name in excel_file.sheet_names:
            product_sheets.append(customer_name)
        
        # 添加其他工作表
        for sheet in excel_file.sheet_names:
            if sheet not in product_sheets:
                product_sheets.append(sheet)
        
        # 处理每个工作表
        for sheet_name in product_sheets:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                if len(df) < 2:
                    continue
                
                # 检测列布局
                col_mapping = detect_column_layout(df, file_name)
                print(f"  工作表: {sheet_name}")
                print(f"  标题行: {col_mapping['标题行']}, 数据起始行: {col_mapping['数据起始行']}")
                print(f"  列映射: {col_mapping}")
                
                # 提取产品数据
                data_start = col_mapping['数据起始行']
                for index in range(data_start, len(df)):
                    try:
                        row = df.iloc[index]
                        
                        product = {}
                        
                        # 提取各字段
                        fields = ['产品型号', '产品名称', '数量_件', '规格_KG', '数量_KG', '单价', '金额']
                        
                        for field in fields:
                            col_idx = col_mapping[field]
                            if col_idx is not None and col_idx < len(row):
                                value = row.iloc[col_idx]
                                
                                if field in ['数量_件', '规格_KG', '数量_KG', '单价', '金额']:
                                    product[field] = safe_float(value)
                                else:
                                    # 文本字段清理
                                    if pd.notna(value):
                                        value_str = str(value).strip()
                                        # 跳过纯数字和空值
                                        if value_str and not value_str.replace('.', '').isdigit():
                                            # 跳过备注信息
                                            if not any(skip in value_str for skip in ['还', '欠', '减账', '实际只有', '下欠']):
                                                product[field] = value_str
                                            else:
                                                product[field] = ''
                                        else:
                                            product[field] = ''
                                    else:
                                        product[field] = ''
                            
                            if field == '产品型号' and col_idx is not None:
                                # 验证产品型号格式
                                if col_idx < len(row):
                                    model_value = row.iloc[col_idx]
                                    if pd.notna(model_value):
                                        model_str = str(model_value).strip()
                                        # 如果是纯数字或太短，可能不是产品型号
                                        if model_str.replace('.', '').isdigit() or len(model_str) < 2:
                                            # 尝试从其他列获取
                                            pass
                        
                        # 确保有基本的产品信息
                        has_product_info = (
                            product.get('产品型号') or 
                            product.get('产品名称')
                        )
                        
                        if has_product_info:
                            # 过滤掉备注信息
                            if product.get('产品名称') and len(product.get('产品名称', '')) > 30:
                                continue
                            
                            product['记录顺序'] = index
                            product['来源'] = f'{sheet_name}-{file_name}'
                            products.append(product)
                    
                    except Exception as e:
                        continue
                
                if products:
                    print(f"  ✓ 提取到 {len(products)} 个产品")
                    break
                    
            except Exception as e:
                print(f"  ✗ 处理工作表失败: {e}")
                continue
        
        return products
        
    except Exception as e:
        print(f"提取产品信息失败 {file_path}: {str(e)}")
        return []

def extract_customer_info_correct(file_path, file_name):
    """提取客户信息（保持之前的正确逻辑）"""
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
        
        # 遍历所有工作表查找客户信息
        customer_found = False
        
        for sheet_name in excel_file.sheet_names:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                
                for i in range(min(10, len(df))):
                    for j in range(min(3, len(df.columns))):
                        try:
                            cell_value = str(df.iloc[i, j]) if not pd.isna(df.iloc[i, j]) else ""
                            
                            if not customer_found and ('购货单位' in cell_value or '购买单位' in cell_value):
                                customer_match = re.search(
                                    r'[购货购买]单位[（(][^）)]*[）)][：:]\s*(.+?)\s*(?:[\s联系人]|$)',
                                    cell_value
                                )
                                if customer_match:
                                    customer_name = customer_match.group(1).strip()
                                    if customer_name and len(customer_name) > 1:
                                        customer_info['客户名称'] = customer_name
                                        customer_found = True
                                        print(f"  ✓ 找到客户: {customer_name}")
                                
                                contact_match = re.search(
                                    r'联系人[：:]\s*(.+?)\s*(?:[\s日期]|$)',
                                    cell_value
                                )
                                if contact_match:
                                    contact = contact_match.group(1).strip()
                                    if contact and contact != ' ' and not contact[0].isdigit():
                                        customer_info['联系人'] = contact
                                
                                order_match = re.search(r'订单编号[：:]\s*([^\s联系人日期]+)', cell_value)
                                if order_match:
                                    customer_info['订单编号'] = order_match.group(1).strip()
                                
                                date_match = re.search(r'(\d{4}年\d{1,2}月\d{1,2}日)', cell_value)
                                if date_match:
                                    customer_info['日期'] = date_match.group(1)
                            
                        except:
                            continue
                    
                    if customer_found:
                        break
                
                if customer_found:
                    break
                    
            except:
                continue
        
        if not customer_info['客户名称']:
            customer_info['客户名称'] = file_name.replace('.xlsx', '')
            print(f"  ⚠ 使用文件名作为客户名: {customer_info['客户名称']}")
        
        return customer_info
        
    except Exception as e:
        print(f"提取客户信息失败 {file_path}: {str(e)}")
        return None

def create_product_corrected_database():
    """创建产品信息修正后的数据库"""
    print("\n=== 创建产品修正后的数据库 ===")
    
    try:
        os.remove('customer_products_final_corrected.db')
    except:
        pass
    
    conn = sqlite3.connect('customer_products_final_corrected.db')
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
            产品型号 TEXT,
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
    
    print("产品修正后的数据库创建完成")

def process_all_files_product_corrected():
    """产品信息修正后批量处理所有文件"""
    print("=== 产品信息修正后批量处理 ===")
    print("目标: 正确提取产品型号、名称、规格、单价")
    
    excel_files = glob.glob('发货单/*.xlsx')
    
    if not excel_files:
        print("未找到Excel文件")
        return
    
    print(f"找到 {len(excel_files)} 个Excel文件")
    
    # 创建数据库
    create_product_corrected_database()
    
    conn = sqlite3.connect('customer_products_final_corrected.db')
    cursor = conn.cursor()
    
    processed_files = 0
    total_products = 0
    
    print("\n开始处理...")
    print("=" * 80)
    
    for file_path in excel_files:
        file_name = os.path.basename(file_path)
        print(f"\n处理文件: {file_name}")
        
        try:
            # 提取客户信息
            customer_info = extract_customer_info_correct(file_path, file_name)
            if not customer_info or not customer_info['客户名称']:
                print(f"  ⚠ 跳过: 无法提取客户信息")
                continue
            
            # 检查客户是否已存在
            cursor.execute('SELECT customer_id FROM customers WHERE 客户名称 = ?', 
                         (customer_info['客户名称'],))
            existing_customer = cursor.fetchone()
            
            if existing_customer:
                customer_id = existing_customer[0]
                print(f"  ✓ 客户: {customer_info['客户名称']}")
            else:
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
            
            # 提取产品信息（修正后的逻辑）
            products = extract_products_adaptive(file_path, file_name)
            
            if products:
                # 去重
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
            print(f"  ✗ 处理失败: {str(e)}")
    
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 80)
    print(f"\n=== 处理完成 ===")
    print(f"成功处理: {processed_files}/{len(excel_files)}")
    print(f"总产品数: {total_products}")

def verify_corrected_database():
    """验证修正后的数据库"""
    print("\n=== 验证产品修正后的数据库 ===")
    
    conn = sqlite3.connect('customer_products_final_corrected.db')
    
    customers = pd.read_sql_query("SELECT * FROM customers", conn)
    products = pd.read_sql_query("SELECT * FROM products", conn)
    
    print(f"客户总数: {len(customers)}")
    print(f"产品总数: {len(products)}")
    
    # 抽样检查几个客户的产品信息
    print("\n抽样检查产品信息:")
    print("-" * 100)
    
    for _, customer in customers.head(5).iterrows():
        print(f"\n客户: {customer['客户名称']}")
        customer_products = products[products['客户ID'] == customer['customer_id']].head(3)
        
        for i, (_, prod) in enumerate(customer_products.iterrows(), 1):
            print(f"  {i}. 型号: {prod.get('产品型号', 'N/A'):<15} 名称: {prod.get('产品名称', 'N/A')[:30]:<30} 规格: {prod.get('规格_KG', 0):<6} 单价: {prod.get('单价', 0):<8} 金额: {prod.get('金额', 0):<10}")
    
    # 统计验证
    print(f"\n统计验证:")
    print(f"  - 有产品型号的记录: {len(products[products['产品型号'] != ''])}")
    print(f"  - 有产品名称的记录: {len(products[products['产品名称'] != ''])}")
    print(f"  - 有规格的记录: {len(products[products['规格_KG'] > 0])}")
    print(f"  - 有单价的记录: {len(products[products['单价'] > 0])}")
    print(f"  - 有金额的记录: {len(products[products['金额'] > 0])}")
    
    print(f"\n数据质量评估:")
    model_rate = len(products[products['产品型号'] != '']) / len(products) * 100
    name_rate = len(products[products['产品名称'] != '']) / len(products) * 100
    spec_rate = len(products[products['规格_KG'] > 0]) / len(products) * 100
    price_rate = len(products[products['单价'] > 0]) / len(products) * 100
    
    print(f"  - 产品型号完整率: {model_rate:.1f}%")
    print(f"  - 产品名称完整率: {name_rate:.1f}%")
    print(f"  - 规格完整率: {spec_rate:.1f}%")
    print(f"  - 单价完整率: {price_rate:.1f}%")
    
    conn.close()

if __name__ == "__main__":
    print("=== 产品信息修正后批量处理 ===")
    print("目标: 正确识别不同文件的列布局，提取准确的产品型号、名称、规格、单价")
    print()
    
    # 批量处理
    process_all_files_product_corrected()
    
    # 验证结果
    verify_corrected_database()
    
    print("\n=== 完成 ===")
    print("数据库文件: customer_products_final_corrected.db")