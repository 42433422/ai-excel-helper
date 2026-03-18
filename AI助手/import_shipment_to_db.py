#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量从出货记录文件导入数据到数据库
"""

import os
import sqlite3
import pandas as pd
import openpyxl
from datetime import datetime
import re

def import_shipment_records_to_database():
    """批量从出货记录文件导入数据到数据库"""
    
    # 路径配置
    base_dir = os.path.dirname(os.path.abspath(__file__))
    shipment_dir = os.path.join(base_dir, '..', '出货记录')
    db_path = 'database.db'
    
    print("📊 批量导入出货记录到数据库")
    print("=" * 50)
    
    if not os.path.exists(shipment_dir):
        print(f"❌ 出货记录文件夹不存在: {shipment_dir}")
        return False
    
    # 连接数据库
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        print(f"✅ 数据库连接成功: {db_path}")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False
    
    # 获取所有客户目录
    client_dirs = []
    for item in os.listdir(shipment_dir):
        item_path = os.path.join(shipment_dir, item)
        if os.path.isdir(item_path) and item != '__pycache__':
            client_dirs.append((item, item_path))
    
    print(f"📁 发现 {len(client_dirs)} 个客户目录")
    
    imported_count = 0
    failed_count = 0
    
    for client_name, client_dir in client_dirs:
        print(f"\n🏭 处理客户: {client_name}")
        
        # 查找Excel文件
        excel_files = []
        for file in os.listdir(client_dir):
            if file.endswith('.xlsx') and file != '出货记录模板.xlsx':
                excel_files.append(os.path.join(client_dir, file))
        
        if not excel_files:
            print(f"   ⚠️ 未找到Excel文件")
            failed_count += 1
            continue
        
        for excel_file in excel_files:
            try:
                print(f"   📄 处理文件: {os.path.basename(excel_file)}")
                
                # 读取Excel文件
                try:
                    # 尝试读取所有工作表
                    all_sheets = pd.read_excel(excel_file, sheet_name=None)
                    print(f"      工作表: {list(all_sheets.keys())}")
                    
                    # 处理每个工作表
                    for sheet_name, df in all_sheets.items():
                        if df.empty:
                            print(f"      📋 {sheet_name}: 空工作表，跳过")
                            continue
                        
                        print(f"      📋 {sheet_name}: {len(df)} 行, {len(df.columns)} 列")
                        
                        # 检查是否包含订单数据（寻找关键列）
                        columns = [str(col).strip() for col in df.columns]
                        print(f"         列名: {columns}")
                        
                        # 寻找可能的订单列
                        potential_order_cols = []
                        for i, col in enumerate(df.columns):
                            col_str = str(col).strip().lower()
                            if any(keyword in col_str for keyword in ['单号', '订单', 'order', '编号', '号']):
                                potential_order_cols.append((i, col))
                        
                        if not potential_order_cols:
                            print(f"         ⚠️ 未找到订单号列，跳过此工作表")
                            continue
                        
                        print(f"         🎯 找到可能的订单列: {[(i, col) for i, col in potential_order_cols]}")
                        
                        # 提取订单数据
                        for _, row in df.iterrows():
                            # 检查是否是有效的数据行
                            if pd.isna(row.iloc[0]) or str(row.iloc[0]).strip() == '':
                                continue
                            
                            # 尝试提取订单信息
                            order_data = extract_order_info(row, df.columns, client_name)
                            
                            if order_data:
                                # 检查订单是否已存在
                                cursor.execute(
                                    'SELECT id FROM orders WHERE order_number = ?', 
                                    (order_data['order_number'],)
                                )
                                existing = cursor.fetchone()
                                
                                if existing:
                                    print(f"         ⚠️ 订单 {order_data['order_number']} 已存在，跳过")
                                    continue
                                
                                # 插入新订单
                                try:
                                    cursor.execute('''
                                        INSERT INTO orders (order_number, purchase_unit, total_amount, status, created_at, updated_at)
                                        VALUES (?, ?, ?, ?, ?, ?)
                                    ''', (
                                        order_data['order_number'],
                                        order_data['purchase_unit'],
                                        order_data['total_amount'],
                                        order_data['status'],
                                        order_data['created_at'],
                                        order_data['updated_at']
                                    ))
                                    
                                    imported_count += 1
                                    print(f"         ✅ 导入订单: {order_data['order_number']} - {order_data['purchase_unit']}")
                                    
                                except Exception as e:
                                    print(f"         ❌ 插入订单失败: {e}")
                                    failed_count += 1
                
                except Exception as e:
                    print(f"      ❌ 读取文件失败: {e}")
                    failed_count += 1
                    continue
            
            except Exception as e:
                print(f"   ❌ 处理文件失败: {e}")
                failed_count += 1
                continue
    
    # 提交更改
    conn.commit()
    conn.close()
    
    print(f"\n🎉 批量导入完成！")
    print(f"📊 统计:")
    print(f"   ✅ 成功导入: {imported_count} 个订单")
    print(f"   ❌ 失败: {failed_count} 个")
    
    return imported_count > 0

def extract_order_info(row, columns, client_name):
    """从Excel行中提取订单信息"""
    
    try:
        # 基本订单信息
        order_number = ""
        order_date = datetime.now().strftime("%Y-%m-%d")
        total_amount = 0.0
        status = "completed"
        
        # 查找订单号
        for i, value in enumerate(row):
            if pd.notna(value):
                value_str = str(value).strip()
                # 检查是否是订单号格式
                if any(pattern in value_str.upper() for pattern in ['ORD', '订单', 'NO']):
                    # 提取可能的订单号
                    order_match = re.search(r'[A-Z0-9\-_]+', value_str)
                    if order_match:
                        order_number = order_match.group()
                        break
        
        # 如果没有找到合适的订单号，生成一个
        if not order_number:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            order_number = f"IMP_{client_name}_{timestamp}"
        
        # 查找金额
        for i, value in enumerate(row):
            if pd.notna(value):
                try:
                    amount = float(value)
                    if amount > 0:
                        total_amount = amount
                        break
                except:
                    continue
        
        # 设置时间
        created_at = datetime.now().isoformat()
        updated_at = datetime.now().isoformat()
        
        return {
            'order_number': order_number,
            'purchase_unit': client_name,
            'total_amount': total_amount,
            'status': status,
            'created_at': created_at,
            'updated_at': updated_at
        }
        
    except Exception as e:
        print(f"         ❌ 提取订单信息失败: {e}")
        return None

if __name__ == '__main__':
    success = import_shipment_records_to_database()
    if success:
        print("\n✅ 批量导入成功！现在可以测试购买单位筛选功能了。")
    else:
        print("\n❌ 批量导入失败或没有找到可导入的数据。")
