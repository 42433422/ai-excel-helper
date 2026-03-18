#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
正确的出货记录清空脚本 - 完全复制模板格式
"""

import os
import shutil
import pandas as pd
from datetime import datetime

def clear_shipment_records_correct():
    """正确清空出货记录 - 完全复制模板格式"""
    
    # 基础路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    shipment_dir = os.path.join(base_dir, '..', '出货记录')
    template_file = os.path.join(shipment_dir, '出货记录模板.xlsx')
    
    print("📊 正确的出货记录清空脚本")
    print("=" * 50)
    
    # 检查模板文件是否存在
    if not os.path.exists(template_file):
        print(f"❌ 模板文件不存在: {template_file}")
        return False
    
    print(f"✅ 模板文件: {template_file}")
    
    # 读取模板文件内容，保持原始格式
    try:
        # 使用pandas读取模板，保持原始工作表结构
        template_data = pd.read_excel(template_file, sheet_name=None, header=None)
        template_sheets = list(template_data.keys())
        print(f"✅ 模板工作表: {template_sheets}")
        
        # 显示模板内容详情
        for sheet_name, df in template_data.items():
            print(f"   📄 {sheet_name}: {df.shape[0]} 行, {df.shape[1]} 列")
            print(f"      前3行:")
            print(df.head(3).to_string(index=False))
        
    except Exception as e:
        print(f"❌ 读取模板文件失败: {e}")
        return False
    
    # 获取所有客户目录
    client_dirs = []
    for item in os.listdir(shipment_dir):
        item_path = os.path.join(shipment_dir, item)
        if os.path.isdir(item_path) and item != '__pycache__':
            client_dirs.append((item, item_path))
    
    print(f"\n📁 发现 {len(client_dirs)} 个客户目录")
    
    # 处理每个客户的出货记录
    processed_count = 0
    failed_count = 0
    
    for i, (client_name, client_dir) in enumerate(client_dirs, 1):
        print(f"\n🏭 [{i}/{len(client_dirs)}] 处理客户: {client_name}")
        
        # 查找客户的Excel文件
        excel_files = []
        for file in os.listdir(client_dir):
            if file.endswith('.xlsx') and file != '出货记录模板.xlsx':
                excel_files.append(os.path.join(client_dir, file))
        
        if not excel_files:
            print(f"   ⚠️ 未找到Excel文件")
            failed_count += 1
            continue
        
        # 处理每个Excel文件
        for excel_file in excel_files:
            try:
                print(f"   📄 处理文件: {os.path.basename(excel_file)}")
                
                # 方法1：直接复制模板文件（最准确的格式复制）
                # 先复制模板到临时位置
                temp_file = excel_file + '.temp'
                shutil.copy2(template_file, temp_file)
                
                # 删除原文件
                os.remove(excel_file)
                
                # 将临时文件重命名为目标文件名
                shutil.move(temp_file, excel_file)
                
                print(f"   ✅ 文件格式已完全复制模板")
                processed_count += 1
                
            except Exception as e:
                print(f"   ❌ 处理失败: {e}")
                failed_count += 1
                continue
    
    print(f"\n🎉 清空操作完成！")
    print(f"📊 处理统计:")
    print(f"   客户目录数: {len(client_dirs)}")
    print(f"   成功处理文件数: {processed_count}")
    print(f"   失败文件数: {failed_count}")
    
    return True

if __name__ == '__main__':
    success = clear_shipment_records_correct()
    if success:
        print("\n✅ 所有出货记录格式已正确清空！")
        print("🎯 现在所有客户的出货记录都完全按照模板格式")
    else:
        print("\n❌ 出货记录清空操作失败！")
