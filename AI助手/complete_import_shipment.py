#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整的出货记录导入功能 - 读取所有出货记录到数据库
"""

import os
import sqlite3
import pandas as pd
import re
from datetime import datetime
import logging
import shutil

logger = logging.getLogger(__name__)

def complete_import_shipment_records():
    """完整导入所有出货记录到数据库"""
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 检测是否是打包环境
    is_frozen = hasattr(sys, '_MEIPASS')
    
    if is_frozen:
        # 打包环境 - 使用EXE同级目录的出货记录
        shipment_dir = os.path.join(base_dir, '出货记录')
    else:
        # 开发环境 - 使用上级目录的出货记录
        shipment_dir = os.path.join(base_dir, '..', '出货记录')
    
    db_path = os.path.join(base_dir, 'products.db')
    
    logger.info("📊 完整导入出货记录到数据库")
    logger.info(f"数据库路径: {db_path}")
    logger.info(f"出货记录目录: {shipment_dir}")
    
    if not os.path.exists(shipment_dir):
        logger.warning(f"❌ 出货记录文件夹不存在: {shipment_dir}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        logger.info(f"✅ 数据库连接成功: {db_path}")
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        return False
    
    client_dirs = []
    for item in os.listdir(shipment_dir):
        item_path = os.path.join(shipment_dir, item)
        if os.path.isdir(item_path) and item != '__pycache__':
            client_dirs.append((item, item_path))
    
    logger.info(f"📁 发现 {len(client_dirs)} 个客户目录")
    
    imported_count = 0
    failed_count = 0
    corrected_count = 0
    
    for client_name, client_dir in client_dirs:
        logger.info(f"\n🏭 处理客户: {client_name}")
        
        excel_files = []
        for file in os.listdir(client_dir):
            if file.endswith('.xlsx') and file != '出货记录模板.xlsx' and not file.startswith('~$'):
                excel_files.append(os.path.join(client_dir, file))
        
        if not excel_files:
            logger.warning(f"   ⚠️ 未找到Excel文件")
            failed_count += 1
            continue
        
        for excel_file in excel_files:
            try:
                logger.info(f"   📄 处理文件: {os.path.basename(excel_file)}")
                
                try:
                    all_sheets = pd.read_excel(excel_file, sheet_name=None)
                    logger.info(f"      工作表: {list(all_sheets.keys())}")
                    
                    for sheet_name, df in all_sheets.items():
                        if df.empty:
                            logger.info(f"      📋 {sheet_name}: 空工作表，跳过")
                            continue
                        
                        logger.info(f"      📋 {sheet_name}: {len(df)} 行, {len(df.columns)} 列")
                        
                        records_added, local_corrected = process_sheet_to_database(df, sheet_name, client_name, cursor)
                        imported_count += records_added
                        corrected_count += local_corrected
                        
                except Exception as e:
                    logger.error(f"      ❌ 读取文件失败: {e}")
                    failed_count += 1
                    continue
            
            except Exception as e:
                logger.error(f"   ❌ 处理文件失败: {e}")
                failed_count += 1
                continue
    
    conn.commit()
    conn.close()
    
    logger.info(f"\n🎉 完整导入完成！")
    logger.info(f"📊 统计:")
    logger.info(f"   ✅ 成功导入: {imported_count} 条记录")
    logger.info(f"   🔄 数据修正: {corrected_count} 条记录")
    logger.info(f"   ❌ 失败: {failed_count} 个")
    
    return imported_count > 0 or corrected_count > 0

def process_sheet_to_database(df, sheet_name, client_name, cursor):
    """处理单个工作表到数据库 - 按订单号分组处理"""
    
    records_added = 0
    local_corrected = 0
    
    try:
        columns = [str(col).strip() for col in df.columns]
        logger.info(f"         列名: {columns}")
        
        if sheet_name == '25出货' or any('出货' in col for col in columns):
            logger.info(f"         🎯 识别为出货记录工作表")
            
            product_rows = []
            for index, row in df.iterrows():
                if pd.isna(row.iloc[0]) or str(row.iloc[0]).strip() == '':
                    continue
                
                first_cell = str(row.iloc[0]).strip()
                if any(keyword in first_cell for keyword in ['日期', '单号', '产品', '合计', '总计']):
                    continue
                
                product_info = extract_product_info(row, df.columns, client_name, index)
                if product_info:
                    product_rows.append(product_info)
            
            logger.info(f"         📊 提取到 {len(product_rows)} 个有效产品记录")
            
            cursor.execute('SELECT id, order_number FROM orders WHERE purchase_unit = ?', (client_name,))
            existing_orders = cursor.fetchall()
            
            if not product_rows:
                if existing_orders:
                    logger.warning(f"         ⚠️ Excel为空，但数据库中有 {len(existing_orders)} 个订单，清理错误数据...")
                    for order_id, order_number in existing_orders:
                        cursor.execute('DELETE FROM orders WHERE id = ?', (order_id,))
                        logger.info(f"         🧹 已清理订单 {order_number}")
                        local_corrected += 1
                else:
                    logger.info(f"         ℹ️ Excel为空，数据库中也无订单，跳过")
                return 0
            
            orders_dict = {}
            for product in product_rows:
                order_number = product['order_number']
                if order_number not in orders_dict:
                    orders_dict[order_number] = {
                        'order_number': order_number,
                        'purchase_unit': product['purchase_unit'],
                        'products': [],
                        'total_amount': 0.0
                    }
                orders_dict[order_number]['products'].append(product)
                orders_dict[order_number]['total_amount'] += product.get('amount', 0.0)
            
            logger.info(f"         📦 汇总为 {len(orders_dict)} 个订单")
            
            for order_number, order_data in orders_dict.items():
                cursor.execute(
                    'SELECT id, total_amount FROM orders WHERE order_number = ? AND purchase_unit = ?', 
                    (order_number, order_data['purchase_unit'])
                )
                existing = cursor.fetchone()
                
                if existing:
                    order_id, existing_amount = existing
                    if abs(existing_amount - order_data['total_amount']) > 0.01:
                        logger.info(f"         🔄 修正订单 {order_number}: 数据库金额 {existing_amount:.2f} -> Excel金额 {order_data['total_amount']:.2f}")
                        cursor.execute('''
                            UPDATE orders 
                            SET total_amount = ?, updated_at = ?
                            WHERE id = ?
                        ''', (
                            order_data['total_amount'],
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            order_id
                        ))
                        local_corrected += 1
                        logger.info(f"         ✅ 成功修正订单 {order_number}")
                    else:
                        logger.info(f"         ℹ️ 订单 {order_number} 数据一致，无需更新")
                else:
                    try:
                        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        cursor.execute('''
                            INSERT INTO orders (order_number, purchase_unit, total_amount, status, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (
                            order_number,
                            order_data['purchase_unit'],
                            order_data['total_amount'],
                            'completed',
                            now,
                            now
                        ))
                        records_added += 1
                        logger.info(f"         ✅ 成功插入订单 {order_number}: {len(order_data['products'])} 个产品, 总金额: {order_data['total_amount']:.2f}")
                        
                    except Exception as e:
                        logger.error(f"         ❌ 插入订单失败 {order_number}: {e}")
                        continue
        
        else:
            logger.info(f"      ℹ️ 跳过非出货记录工作表: {sheet_name}")
    
    except Exception as e:
        logger.error(f"      ❌ 处理工作表失败: {e}")
    
    return records_added, local_corrected

def extract_product_info(row, columns, client_name, row_index):
    """提取单个产品的信息"""
    
    try:
        # 基本产品信息
        order_number = ""
        product_name = ""
        amount = 0.0
        
        # 查找订单号（在第2列）
        if len(row) > 1 and pd.notna(row.iloc[1]):
            order_value = str(row.iloc[1]).strip()
            if order_value and order_value != '单号':  # 跳过标题
                # 提取订单号
                order_match = re.search(r'[A-Z0-9\-_]+', order_value)
                if order_match:
                    order_number = order_match.group()
                else:
                    # 如果没有格式化的订单号，使用时间戳
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    order_number = f"{client_name}_{timestamp}_{row_index}"
        
        # 如果还是没有订单号，生成一个
        if not order_number:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            order_number = f"{client_name}_{timestamp}_{row_index}"
        
        # 查找产品名称（在第5列：产品名称）
        if len(row) > 5 and pd.notna(row.iloc[5]):
            product_name = str(row.iloc[5]).strip()
        
        # 查找金额 - 优先使用单价/元列
        amount = 0.0
        
        # 先检查第9列（单价/元）
        if len(row) > 9 and pd.notna(row.iloc[9]):
            try:
                amount = float(row.iloc[9])
                if amount > 0:
                    pass  # 使用单价
            except:
                amount = 0.0
        
        # 如果单价为0，检查第10列（金额/元）
        if amount == 0.0 and len(row) > 10 and pd.notna(row.iloc[10]):
            try:
                amount = float(row.iloc[10])
                if amount > 0:
                    pass  # 使用金额
            except:
                amount = 0.0
        
        # 返回产品信息
        return {
            'order_number': order_number,
            'purchase_unit': client_name,
            'product_name': product_name,
            'amount': amount,
            'row_index': row_index
        }
        
    except Exception as e:
        print(f"         ❌ 提取产品信息失败: {e}")
        return None

if __name__ == '__main__':
    success = complete_import_shipment_records()
    if success:
        print("\n✅ 完整导入成功！现在可以测试完整的购买单位筛选功能了。")
    else:
        print("\n❌ 完整导入失败或没有找到可导入的数据。")
