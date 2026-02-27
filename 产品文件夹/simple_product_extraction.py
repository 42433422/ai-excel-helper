import pandas as pd
import sqlite3
import os
import re
from datetime import datetime
import glob

# 定义数据库路径
DB_PATH = 'customer_products_final_corrected.db'

# 删除旧数据库
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
    print(f"已删除旧数据库: {DB_PATH}")

# 连接到新的SQLite数据库
conn = sqlite3.connect(DB_PATH)
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
        订单状态 TEXT,
        创建时间 DATETIME DEFAULT CURRENT_TIMESTAMP,
        更新时间 DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (客户ID) REFERENCES customers(customer_id)
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
        数量_件 REAL,
        规格_KG REAL,
        数量_KG REAL,
        单价 REAL,
        金额 REAL,
        单号 TEXT,
        记录顺序 INTEGER,
        来源 TEXT,
        创建时间 DATETIME DEFAULT CURRENT_TIMESTAMP,
        更新时间 DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (客户ID) REFERENCES customers(customer_id),
        FOREIGN KEY (订单ID) REFERENCES orders(order_id)
    )
''')

conn.commit()

# 修复后的提取逻辑
def extract_customer_info(file_path, file_name):
    """提取客户信息"""
    try:
        customer_info = {
            '客户名称': '',
            '联系人': ' ',
            '电话': '',
            '供应商名称': '成都国圣工业有限公司',
            '供应商电话': '028-85852618',
            '文件名': file_name
        }
        
        # 尝试从文件名获取客户名称
        customer_info['客户名称'] = file_name.replace('.xlsx', '')
        print(f"  ✔️ 使用文件名作为客户名称: {customer_info['客户名称']}")
        
        return customer_info
        
    except Exception as e:
        print(f"提取客户信息失败 {file_path}: {str(e)}")
        return None

# 简化的产品提取逻辑
def extract_products(file_path, file_name):
    """简化的产品信息提取，基于行数据特征"""
    try:
        products = []
        excel_file = pd.ExcelFile(file_path)
        
        # 尝试不同的工作表
        for sheet_name in excel_file.sheet_names:
            try:
                # 只处理出货相关的工作表
                if '出货' in sheet_name or len(sheet_name) < 10:
                    print(f"  尝试工作表: {sheet_name}")
                    df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
                    
                    # 直接遍历所有行，寻找产品数据
                    for index, row in df.iterrows():
                        # 跳过前5行可能的标题行
                        if index < 5:
                            continue
                        
                        # 跳过超过200行的数据（可能是其他数据）
                        if index > 200:
                            break
                        
                        product = {
                            '产品型号': '',
                            '产品名称': '',
                            '数量_件': 0.0,
                            '规格_KG': 0.0,
                            '数量_KG': 0.0,
                            '单价': 0.0,
                            '金额': 0.0,
                            '单号': '',
                            '来源': f'{sheet_name}-{file_name}'
                        }
                        
                        # 遍历所有列
                        for j in range(min(15, len(row))):
                            cell_value = row.iloc[j]
                            if pd.isna(cell_value):
                                continue
                            
                            cell_str = str(cell_value).strip()
                            if not cell_str or cell_str == 'nan':
                                continue
                            
                            # 跳过公式和特殊字符
                            if '=' in cell_str or '@' in cell_str or 'SUM' in cell_str.upper():
                                continue
                            
                            # 识别产品名称（包含特定关键词）
                            if any(keyword in cell_str for keyword in ['漆', '剂', '底', '面', '稀释', '固化']):
                                product['产品名称'] = cell_str
                            # 识别产品型号（通常是字母数字组合，不含中文，长度适中）
                            elif len(cell_str) < 20 and not any(ord(char) > 127 for char in cell_str) and (re.match(r'^[A-Za-z0-9\-_.]+$', cell_str) or cell_str.isdigit()):
                                if not product['产品型号']:
                                    product['产品型号'] = cell_str
                            # 识别数值字段
                            else:
                                try:
                                    num_value = float(cell_str)
                                    # 根据数值大小和位置判断字段类型
                                    if 0 < num_value < 100 and not product['单价']:
                                        product['单价'] = num_value
                                    elif 0 < num_value < 100 and not product['规格_KG']:
                                        product['规格_KG'] = num_value
                                    elif 0 < num_value < 100 and not product['数量_件']:
                                        product['数量_件'] = num_value
                                    elif num_value > 100 and not product['金额']:
                                        product['金额'] = num_value
                                except:
                                    continue
                        
                        # 验证产品信息，至少需要产品名称
                        if product['产品名称'] and any(keyword in product['产品名称'] for keyword in ['漆', '剂', '底', '面', '稀释', '固化']):
                            # 计算数量_KG（如果没有直接提供）
                            if product['数量_KG'] == 0 and product['数量_件'] > 0 and product['规格_KG'] > 0:
                                product['数量_KG'] = product['数量_件'] * product['规格_KG']
                            
                            products.append(product)
                    
                    # 如果找到产品，就不再尝试其他工作表
                    if products:
                        print(f"  ✔️ 在工作表 {sheet_name} 找到 {len(products)} 个产品")
                        break
                    
            except Exception as e:
                print(f"  处理工作表 {sheet_name} 失败: {str(e)}")
                continue
        
        return products
        
    except Exception as e:
        print(f"提取产品信息失败 {file_path}: {str(e)}")
        return []

# 主处理逻辑
def main():
    """主处理函数"""
    print("开始处理Excel文件...")
    
    # 获取所有Excel文件
    excel_files = glob.glob('e:\\女娲1号\\发货单\\*.xlsx')
    print(f"找到 {len(excel_files)} 个Excel文件")
    
    for file_path in excel_files:
        try:
            file_name = os.path.basename(file_path)
            print(f"\n处理文件: {file_name}")
            
            # 提取客户信息
            customer_info = extract_customer_info(file_path, file_name)
            if not customer_info:
                print(f"  ❌ 无法提取客户信息")
                continue
            
            # 插入客户信息
            cursor.execute('''
                INSERT INTO customers (客户名称, 联系人, 电话, 供应商名称, 供应商电话, 文件名)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (customer_info['客户名称'], customer_info['联系人'], customer_info['电话'],
                  customer_info['供应商名称'], customer_info['供应商电话'], customer_info['文件名']))
            conn.commit()
            customer_id = cursor.lastrowid
            print(f"  ✔️ 插入客户: {customer_info['客户名称']} (ID: {customer_id})")
            
            # 提取产品信息
            products = extract_products(file_path, file_name)
            if not products:
                print(f"  ⚠ 未找到有效产品信息")
                continue
            
            print(f"  共找到 {len(products)} 个产品")
            
            # 插入产品信息
            for product in products:
                cursor.execute('''
                    INSERT INTO products (客户ID, 产品型号, 产品名称, 数量_件, 规格_KG, 数量_KG, 单价, 金额, 来源)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (customer_id, product['产品型号'], product['产品名称'],
                      product['数量_件'], product['规格_KG'], product['数量_KG'],
                      product['单价'], product['金额'], product['来源']))
            
            conn.commit()
            print(f"  ✔️ 插入 {len(products)} 个产品")
            
        except Exception as e:
            print(f"处理文件 {file_path} 失败: {str(e)}")
            continue
    
    print(f"\n处理完成！数据库已保存到: {DB_PATH}")
    conn.close()

if __name__ == "__main__":
    main()