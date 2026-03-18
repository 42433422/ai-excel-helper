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
        excel_file = pd.ExcelFile(file_path)
        customer_info = {
            '客户名称': '',
            '联系人': ' ',
            '电话': '',
            '供应商名称': '成都国圣工业有限公司',
            '供应商电话': '028-85852618',
            '文件名': file_name
        }
        
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
                                
                            # 提取联系人
                            contact_match = re.search(
                                r'联系人[：:]\s*(.+?)\s*(?:[\s日期]|$)',
                                cell_value
                            )
                            if contact_match:
                                contact = contact_match.group(1).strip()
                                if contact and contact != ' ' and not contact[0].isdigit():
                                    customer_info['联系人'] = contact
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
        
        return customer_info
        
    except Exception as e:
        print(f"提取客户信息失败 {file_path}: {str(e)}")
        return None

# 修复后的产品提取逻辑
def extract_products(file_path, file_name):
    """修复后的产品信息提取"""
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
        
        for sheet in excel_file.sheet_names:
            if sheet not in product_sheets and len(sheet) < 10:
                product_sheets.append(sheet)
        
        # 处理每个产品工作表
        for sheet_name in product_sheets:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                if len(df) < 5:
                    continue
                
                # 查找标题行
                header_row = -1
                for i in range(min(10, len(df))):
                    row = df.iloc[i]
                    has_product_keywords = False
                    has_number_fields = False
                    
                    for j in range(min(15, len(row))):
                        cell_value = str(row.iloc[j]) if not pd.isna(row.iloc[j]) else ""
                        # 检查是否包含产品相关关键词
                        if any(keyword in cell_value for keyword in ['产品型号', '产品名称', '规格', '单价', '数量']):
                            has_product_keywords = True
                        # 检查是否包含数字字段（可能是数量、规格等）
                        if re.match(r'^[数量/件|规格/KG|数量/KG|单价/元|金额/元]$', cell_value):
                            has_number_fields = True
                    
                    if has_product_keywords or has_number_fields:
                        header_row = i
                        break
                
                if header_row == -1:
                    # 如果没有找到明确的标题行，跳过
                    continue
                
                # 重新读取数据，使用正确的标题行
                df_with_header = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row)
                if len(df_with_header) < 5:
                    continue
                
                print(f"  使用工作表: {sheet_name}, 标题行: {header_row + 1}")
                print(f"  列名: {df_with_header.columns.tolist()}")
                
                # 标准化列名
                normalized_columns = []
                for col in df_with_header.columns:
                    col_str = str(col).strip()
                    if '产品型号' in col_str or '型号' in col_str:
                        normalized_columns.append('产品型号')
                    elif '产品名称' in col_str or '名称' in col_str:
                        normalized_columns.append('产品名称')
                    elif '数量/件' in col_str or '数量件' in col_str or '件数' in col_str:
                        normalized_columns.append('数量/件')
                    elif '规格' in col_str or 'kg' in col_str.lower() or 'KG' in col_str:
                        normalized_columns.append('规格/KG')
                    elif '数量/kg' in col_str.lower() or '数量KG' in col_str or '总重量' in col_str:
                        normalized_columns.append('数量/KG')
                    elif '单价' in col_str:
                        normalized_columns.append('单价')
                    elif '金额' in col_str:
                        normalized_columns.append('金额')
                    elif '日期' in col_str:
                        normalized_columns.append('日期')
                    elif '单号' in col_str or '编号' in col_str:
                        normalized_columns.append('单号')
                    else:
                        normalized_columns.append(col_str)
                
                df_with_header.columns = normalized_columns
                
                # 提取产品数据
                for index, row in df_with_header.iterrows():
                    product = {
                        '产品型号': '',
                        '产品名称': '',
                        '数量/件': 0.0,
                        '规格/KG': 0.0,
                        '数量/KG': 0.0,
                        '单价': 0.0,
                        '金额': 0.0,
                        '单号': '',
                        '日期': ''
                    }
                    
                    # 遍历所有标准化列
                    for col in df_with_header.columns:
                        try:
                            cell_value = row[col]
                            if pd.isna(cell_value):
                                continue
                            
                            cell_str = str(cell_value).strip()
                            if not cell_str or cell_str == 'nan':
                                continue
                            
                            # 跳过公式和特殊字符
                            if '=' in cell_str or '@' in cell_str or 'SUM' in cell_str.upper():
                                continue
                            
                            if col == '产品型号':
                                # 产品型号不应是纯数字或日期
                                if not cell_str.replace('.', '').replace('-', '').isdigit() and len(cell_str) < 20:
                                    product['产品型号'] = cell_str
                            elif col == '产品名称':
                                product['产品名称'] = cell_str
                            elif col in ['数量/件', '规格/KG', '数量/KG', '单价', '金额']:
                                # 处理数值字段
                                try:
                                    num_value = float(cell_str)
                                    product[col] = num_value
                                except:
                                    continue
                            elif col == '单号':
                                product['单号'] = cell_str
                            elif col == '日期':
                                product['日期'] = cell_str
                        except:
                            continue
                    
                    # 验证产品信息
                    if (product['产品型号'] or product['产品名称']) and any(ord(char) > 127 for char in product['产品名称']) and (product['数量/件'] > 0 or product['数量/KG'] > 0):
                        # 添加到产品列表
                        products.append({
                            '产品型号': product['产品型号'],
                            '产品名称': product['产品名称'],
                            '数量_件': product['数量/件'],
                            '规格_KG': product['规格/KG'],
                            '数量_KG': product['数量/KG'],
                            '单价': product['单价'],
                            '金额': product['金额'],
                            '单号': product['单号'],
                            '日期': product['日期'],
                            '来源': f'{sheet_name}-{file_name}'
                        })
                
                if products:
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
            
            print(f"  找到 {len(products)} 个产品")
            
            # 插入产品信息
            for product in products:
                # 验证产品型号和名称
                if not product['产品型号'] and not product['产品名称']:
                    continue
                if not any(keyword in product['产品名称'] for keyword in ['漆', '剂', '底', '面', '稀释', '固化']):
                    continue
                
                cursor.execute('''
                    INSERT INTO products (客户ID, 产品型号, 产品名称, 数量_件, 规格_KG, 数量_KG, 单价, 金额, 单号, 来源)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (customer_id, product['产品型号'], product['产品名称'],
                      product['数量_件'], product['规格_KG'], product['数量_KG'],
                      product['单价'], product['金额'], product['单号'], product['来源']))
            
            conn.commit()
            print(f"  ✔️ 插入 {len(products)} 个产品")
            
        except Exception as e:
            print(f"处理文件 {file_path} 失败: {str(e)}")
            continue
    
    print(f"\n处理完成！数据库已保存到: {DB_PATH}")
    conn.close()

if __name__ == "__main__":
    main()