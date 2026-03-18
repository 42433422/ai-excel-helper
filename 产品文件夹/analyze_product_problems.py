#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import sqlite3

def analyze_product_issues():
    """分析数据库中产品信息的问题"""
    conn = sqlite3.connect('customer_products_final_corrected.db')
    
    # 获取客户信息
    customers = pd.read_sql_query("SELECT * FROM customers", conn)
    
    # 获取产品信息
    products = pd.read_sql_query("SELECT * FROM products", conn)
    
    # 首先查看蕊芯（正确的示例）的产品信息
    rui_xin_id = customers[customers['客户名称'] == '蕊芯']['customer_id'].iloc[0]
    rui_xin_products = products[products['客户ID'] == rui_xin_id]
    
    print("=== 蕊芯（正确示例）的产品信息 ===")
    print(rui_xin_products[['产品型号', '产品名称', '规格_KG', '单价']].head(10))
    
    # 查看其他几个客户的产品信息
    print("\n=== 其他客户的产品信息 ===")
    for customer_name in ['七彩乐园家私', '尹玉华1', '志泓家私', '温总']:
        if customer_name in customers['客户名称'].tolist():
            customer_id = customers[customers['客户名称'] == customer_name]['customer_id'].iloc[0]
            customer_products = products[products['客户ID'] == customer_id]
            print(f"\n--- {customer_name} ---")
            print(customer_products[['产品型号', '产品名称', '规格_KG', '单价']].head(10))
    
    conn.close()

def check_excel_layouts():
    """检查原始Excel文件的列布局"""
    # 检查蕊芯对应的Excel文件（尹玉华1.xlsx）和其他几个文件的布局
    files_to_check = [
        '发货单/尹玉华1.xlsx',  # 蕊芯（正确）
        '发货单/七彩乐园.xlsx',   # 七彩乐园家私
        '发货单/志泓.xlsx',      # 志泓家私
        '发货单/温总.xlsx',       # 温总
    ]
    
    for file_path in files_to_check:
        print(f"\n=== 检查文件: {file_path} ===")
        try:
            # 读取不同工作表，重点查看出货相关工作表
            excel_file = pd.ExcelFile(file_path)
            print(f"工作表: {excel_file.sheet_names}")
            
            # 找出包含出货数据的工作表
            for sheet_name in excel_file.sheet_names:
                # 优先检查包含"出货"或与文件名相关的工作表
                if '出货' in sheet_name or sheet_name in file_path.split('/')[-1].replace('.xlsx', ''):
                    df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=20)
                    print(f"\n工作表: {sheet_name}")
                    print("前10行数据:")
                    print(df.head(10))
                    break
        except Exception as e:
            print(f"读取文件失败: {e}")

if __name__ == "__main__":
    analyze_product_issues()
    check_excel_layouts()