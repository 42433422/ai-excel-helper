#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pandas as pd
import sqlite3
from datetime import datetime
import re

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

def extract_customer_info():
    """提取客户信息"""
    print('=== 第二步：提取客户信息 ===')
    
    # 读取发货单工作表（尹）
    df = pd.read_excel('e:\\女娲1号\\发货单\\尹玉华1.xlsx', sheet_name='尹')
    print(f"尹工作表大小: {df.shape}")
    
    customer_info = {}
    
    # 从第1行提取客户信息（索引0）
    if len(df) > 0:
        customer_row = df.iloc[0]
        customer_text = str(customer_row.iloc[0]) if not pd.isna(customer_row.iloc[0]) else ""
        print(f"第1行客户信息文本: {customer_text}")
        
        # 使用正则表达式提取信息
        # 购货单位：蕊芯 家私
        customer_match = re.search(r'购货单位：([^联系方式]*)', customer_text)
        if customer_match:
            customer_info['客户名称'] = customer_match.group(1).strip()
        
        # 联系人：郭总
        contact_match = re.search(r'联系人：([^日期]*?)(\s|$)', customer_text)
        if contact_match:
            customer_info['联系人'] = contact_match.group(1).strip()
        
        # 日期：2026年01月09日
        date_match = re.search(r'(\d{4}年\d{2}月\d{2}日)', customer_text)
        if date_match:
            customer_info['日期'] = date_match.group(1)
        
        # 订单编号：26-0100021A
        order_match = re.search(r'订单编号：([^联系方式]*?)$', customer_text)
        if order_match:
            customer_info['订单编号'] = order_match.group(1).strip()
    
    # 从其他行查找公司信息
    for i in range(len(df)):
        for j in range(len(df.columns)):
            cell_value = df.iloc[i, j]
            if not pd.isna(cell_value) and isinstance(cell_value, str):
                if '成都国圣工业有限公司' in cell_value:
                    customer_info['供应商名称'] = '成都国圣工业有限公司'
                    customer_info['电话'] = '028-85852618'
                    break
    
    print("提取的客户信息:")
    for key, value in customer_info.items():
        print(f"  {key}: {value}")
    
    return customer_info

def extract_product_info():
    """提取产品信息"""
    print('\n=== 第四步：提取产品信息 ===')
    
    # 读取出货记录
    df_出货 = pd.read_excel('e:\\女娲1号\\发货单\\尹玉华1.xlsx', sheet_name='出货')
    print(f"出货工作表大小: {df_出货.shape}")
    
    # 读取发货单产品
    df_尹 = pd.read_excel('e:\\女娲1号\\发货单\\尹玉华1.xlsx', sheet_name='尹')
    print(f"尹工作表大小: {df_尹.shape}")
    
    products = []
    
    # 从出货工作表提取产品
    for index, row in df_出货.iterrows():
        if index == 0 or index == 1:  # 跳过标题行
            continue
            
        product = {}
        
        # 提取产品信息
        if not pd.isna(row.iloc[3]):  # 产品型号
            product['产品型号'] = str(row.iloc[3]).strip()
        else:
            continue  # 跳过没有产品型号的行
            
        if not pd.isna(row.iloc[6]):  # 产品名称
            product['产品名称'] = str(row.iloc[6]).strip()
            
        if not pd.isna(row.iloc[8]):  # 规格/KG
            product['规格_KG'] = safe_float(row.iloc[8])
            
        if not pd.isna(row.iloc[10]):  # 数量/KG
            product['数量_KG'] = safe_float(row.iloc[10])
            
        if not pd.isna(row.iloc[11]):  # 单价
            product['单价'] = safe_float(row.iloc[11])
            
        if not pd.isna(row.iloc[12]):  # 金额
            product['金额'] = safe_float(row.iloc[12])
            
        if not pd.isna(row.iloc[1]):  # 日期
            product['日期'] = row.iloc[1]
            
        if not pd.isna(row.iloc[2]):  # 单号
            product['单号'] = str(row.iloc[2])
            
        # 添加行号作为记录顺序
        product['记录顺序'] = index
        product['来源'] = '出货记录'
        
        products.append(product)
    
    # 从尹工作表提取产品（发货单）
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
        尹_product['记录顺序'] = 9999  # 发货单记录优先级最高
        
        products.append(尹_product)
    
    print(f"提取到 {len(products)} 条产品记录")
    print("前5条产品记录:")
    for i, product in enumerate(products[:5]):
        print(f"  {i+1}. {product}")
    
    return products

def deduplicate_products(products):
    """去重处理，保留最新记录"""
    print('\n=== 去重处理：保留最新记录 ===')
    
    # 按产品型号分组，保留记录顺序最大的（最新的）
    latest_products = {}
    
    for product in products:
        model = product.get('产品型号', '')
        if model:
            record_order = product.get('记录顺序', 0)
            
            # 如果是新产品型号，或者当前记录更新
            if model not in latest_products or record_order > latest_products[model]['记录顺序']:
                latest_products[model] = product
    
    deduplicated = list(latest_products.values())
    print(f"去重前：{len(products)} 条记录")
    print(f"去重后：{len(deduplicated)} 条记录")
    
    return deduplicated

if __name__ == "__main__":
    # 执行提取和分析
    customer_info = extract_customer_info()
    products = extract_product_info()
    latest_products = deduplicate_products(products)
    
    print(f"\n=== 结果汇总 ===")
    print(f"客户数量：1 个")
    print(f"产品种类：{len(latest_products)} 种")
    print(f"最新记录已优先保留")