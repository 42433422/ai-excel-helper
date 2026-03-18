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

# 客户信息提取函数
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
                                    r'[购货购买]单位(?:[（(][^）)]*[）)])?[：:]\s*(.+?)\s*(?:[\s联系人]|$)',
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
                                
                            elif not customer_found and '客户' in cell_value and '名称' in cell_value:
                                # 另一种可能的格式
                                customer_match = re.search(r'客户名称[：:]\s*(.+?)\s*(?:[,，]|$)', cell_value)
                                if customer_match:
                                    customer_name = customer_match.group(1).strip()
                                    if customer_name and len(customer_name) > 1:
                                        customer_info['客户名称'] = customer_name
                                        customer_found = True
                                        print(f"  ✓ 找到客户名称: {customer_name}")
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

# 精确的产品提取逻辑
def extract_products_exact(file_path, file_name):
    """精确的产品信息提取，先识别标题行，再确定列索引"""
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
                    
                    # 1. 识别标题行
                    header_row = -1
                    product_model_col = -1
                    product_name_col = -1
                    quantity_pieces_col = -1
                    spec_kg_col = -1
                    quantity_kg_col = -1
                    unit_price_col = -1
                    amount_col = -1
                    order_no_col = -1
                    
                    # 遍历前15行寻找标题行
                    for i in range(min(15, len(df))):
                        row = df.iloc[i]
                        
                        # 检查是否包含足够的产品相关关键词
                        keyword_count = 0
                        for j in range(min(15, len(row))):
                            cell_value = row.iloc[j]
                            if pd.notna(cell_value):
                                cell_str = str(cell_value).strip().lower()
                                # 统计产品相关关键词
                                if any(keyword in cell_str for keyword in ['产品型号', '型号', '产品名称', '名称', '规格', '单价', '数量', '金额', '件数', 'kg', '数量/件', '规格/kg', '数量/kg', '单价/元', '金额/元']):
                                    keyword_count += 1
                        
                        if keyword_count >= 3:  # 至少包含3个产品相关关键词
                            header_row = i
                            print(f"    找到标题行: {i + 1}")
                            
                            # 2. 确定各字段的列索引
                            for j in range(min(15, len(df.columns))):
                                cell_value = row.iloc[j]
                                if pd.notna(cell_value):
                                    cell_str = str(cell_value).strip().lower()
                                    if '产品型号' in cell_str or '型号' in cell_str:
                                        product_model_col = j
                                        print(f"    产品型号列: {j + 1}")
                                    elif '产品名称' in cell_str or '名称' in cell_str:
                                        product_name_col = j
                                        print(f"    产品名称列: {j + 1}")
                                    elif '数量/件' in cell_str or '数量件' in cell_str or '件数' in cell_str:
                                        quantity_pieces_col = j
                                        print(f"    数量/件列: {j + 1}")
                                    elif '规格/kg' in cell_str or '规格' in cell_str:
                                        spec_kg_col = j
                                        print(f"    规格/KG列: {j + 1}")
                                    elif '数量/kg' in cell_str or '总重量' in cell_str:
                                        quantity_kg_col = j
                                        print(f"    数量/KG列: {j + 1}")
                                    elif '单价/元' in cell_str or '单价' in cell_str:
                                        unit_price_col = j
                                        print(f"    单价列: {j + 1}")
                                    elif '金额/元' in cell_str or '金额' in cell_str:
                                        amount_col = j
                                        print(f"    金额列: {j + 1}")
                                    elif '单号' in cell_str or '编号' in cell_str:
                                        order_no_col = j
                                        print(f"    单号列: {j + 1}")
                            
                            break
                    
                    # 如果找到了标题行和至少产品名称列，就开始提取产品信息
                    if header_row != -1 and product_name_col != -1:
                        print("    开始提取产品信息...")
                        
                        # 跳过标题行，从下一行开始提取
                        for index in range(header_row + 1, len(df)):
                            row = df.iloc[index]
                            
                            # 检查是否有产品名称
                            if pd.isna(row.iloc[product_name_col]):
                                continue
                            
                            product_name = str(row.iloc[product_name_col]).strip()
                            if not product_name or product_name == 'nan':
                                continue
                            
                            # 验证产品名称是否包含关键词
                            if not any(keyword in product_name for keyword in ['漆', '剂', '底', '面', '稀释', '固化']):
                                continue
                            
                            product = {
                                '产品型号': '',
                                '产品名称': product_name,
                                '数量_件': 0.0,
                                '规格_KG': 0.0,
                                '数量_KG': 0.0,
                                '单价': 0.0,
                                '金额': 0.0,
                                '单号': '',
                                '来源': f'{sheet_name}-{file_name}'
                            }
                            
                            # 提取产品型号
                            if product_model_col != -1 and pd.notna(row.iloc[product_model_col]):
                                product_model = str(row.iloc[product_model_col]).strip()
                                if product_model and product_model != 'nan':
                                    # 确保产品型号不是日期或其他错误格式
                                    if not re.match(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{4}年\d{1,2}月\d{1,2}日', product_model):
                                        product['产品型号'] = product_model
                            
                            # 提取数量/件
                            if quantity_pieces_col != -1 and pd.notna(row.iloc[quantity_pieces_col]):
                                try:
                                    product['数量_件'] = float(row.iloc[quantity_pieces_col])
                                except:
                                    pass
                            
                            # 提取规格/KG
                            if spec_kg_col != -1 and pd.notna(row.iloc[spec_kg_col]):
                                try:
                                    product['规格_KG'] = float(row.iloc[spec_kg_col])
                                except:
                                    pass
                            
                            # 提取数量/KG
                            if quantity_kg_col != -1 and pd.notna(row.iloc[quantity_kg_col]):
                                try:
                                    product['数量_KG'] = float(row.iloc[quantity_kg_col])
                                except:
                                    pass
                            elif product['数量_件'] > 0 and product['规格_KG'] > 0:
                                # 计算数量/KG
                                product['数量_KG'] = product['数量_件'] * product['规格_KG']
                            
                            # 提取单价
                            if unit_price_col != -1 and pd.notna(row.iloc[unit_price_col]):
                                try:
                                    product['单价'] = float(row.iloc[unit_price_col])
                                except:
                                    pass
                            
                            # 提取金额
                            if amount_col != -1 and pd.notna(row.iloc[amount_col]):
                                try:
                                    product['金额'] = float(row.iloc[amount_col])
                                except:
                                    pass
                            
                            # 提取单号
                            if order_no_col != -1 and pd.notna(row.iloc[order_no_col]):
                                order_no = str(row.iloc[order_no_col]).strip()
                                if order_no and order_no != 'nan':
                                    product['单号'] = order_no
                            
                            # 添加到产品列表
                            products.append(product)
                        
                        if products:
                            print(f"  ✔️ 在工作表 {sheet_name} 找到 {len(products)} 个产品")
                            break
                    else:
                        print("    未找到足够的产品相关关键词或产品名称列")
                    
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
            products = extract_products_exact(file_path, file_name)
            if not products:
                print(f"  ⚠ 未找到有效产品信息")
                continue
            
            print(f"  共找到 {len(products)} 个产品")
            
            # 插入产品信息
            for product in products:
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