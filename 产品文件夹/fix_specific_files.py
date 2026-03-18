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

# 提取客户信息
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

# 针对七彩乐园.xlsx的专门提取
# 从之前的分析可知，该文件的25出货工作表第2行为标题行
# 列2: 单号, 列3: 产品型号, 列5: 产品名称, 列6: 数量/件, 列7: 规格/KG, 列8: 数量/KG, 列9: 单价/元, 列10: 金额/元
def extract_products_specific(file_path, file_name):
    """针对特定文件的专门产品信息提取"""
    try:
        products = []
        
        if '七彩乐园' in file_name:
            print(f"  处理七彩乐园.xlsx，使用专门提取逻辑")
            # 七彩乐园.xlsx的25出货工作表，第2行为标题行
            df = pd.read_excel(file_path, sheet_name='25出货', header=1)
            
            # 查看原始列名
            print(f"  原始列名: {df.columns.tolist()}")
            
            # 直接按列索引提取
            for index, row in df.iterrows():
                product = {
                    '产品型号': '',
                    '产品名称': '',
                    '数量_件': 0.0,
                    '规格_KG': 0.0,
                    '数量_KG': 0.0,
                    '单价': 0.0,
                    '金额': 0.0,
                    '单号': '',
                    '来源': f'25出货-{file_name}'
                }
                
                # 列索引2: 产品型号
                if len(row) > 2 and pd.notna(row.iloc[2]):
                    product['产品型号'] = str(row.iloc[2]).strip()
                
                # 列索引5: 产品名称
                if len(row) > 5 and pd.notna(row.iloc[5]):
                    product['产品名称'] = str(row.iloc[5]).strip()
                
                # 列索引6: 数量/件
                if len(row) > 6 and pd.notna(row.iloc[6]):
                    try:
                        product['数量_件'] = float(row.iloc[6])
                    except:
                        pass
                
                # 列索引7: 规格/KG
                if len(row) > 7 and pd.notna(row.iloc[7]):
                    try:
                        product['规格_KG'] = float(row.iloc[7])
                    except:
                        pass
                
                # 列索引8: 数量/KG
                if len(row) > 8 and pd.notna(row.iloc[8]):
                    try:
                        product['数量_KG'] = float(row.iloc[8])
                    except:
                        # 如果无法直接获取数量/KG，尝试计算
                        if product['数量_件'] > 0 and product['规格_KG'] > 0:
                            product['数量_KG'] = product['数量_件'] * product['规格_KG']
                
                # 列索引9: 单价/元
                if len(row) > 9 and pd.notna(row.iloc[9]):
                    try:
                        product['单价'] = float(row.iloc[9])
                    except:
                        pass
                
                # 列索引10: 金额/元
                if len(row) > 10 and pd.notna(row.iloc[10]):
                    try:
                        product['金额'] = float(row.iloc[10])
                    except:
                        # 如果无法直接获取金额，尝试计算
                        if product['数量_KG'] > 0 and product['单价'] > 0:
                            product['金额'] = product['数量_KG'] * product['单价']
                
                # 列索引1: 单号
                if len(row) > 1 and pd.notna(row.iloc[1]):
                    product['单号'] = str(row.iloc[1]).strip()
                
                # 验证产品信息，至少需要产品名称且包含关键词
                if product['产品名称'] and any(keyword in product['产品名称'] for keyword in ['漆', '剂', '底', '面', '稀释', '固化']):
                    products.append(product)
        
        # 添加针对其他文件的专门提取逻辑
        # 这里可以根据需要添加更多文件的专门处理
        
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
            products = extract_products_specific(file_path, file_name)
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