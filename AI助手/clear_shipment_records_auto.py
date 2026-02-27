#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
出货记录清空脚本 - 自动执行版
"""

import os
import shutil
import pandas as pd
from datetime import datetime

def clear_all_shipment_records_auto():
    """自动清空所有客户的出货记录并用模板替换"""
    
    # 基础路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
    shipment_dir = os.path.join(base_dir, '..', '出货记录')
    template_file = os.path.join(shipment_dir, '出货记录模板.xlsx')
    
    print("📊 出货记录清空脚本启动")
    print("=" * 50)
    
    # 检查模板文件是否存在
    if not os.path.exists(template_file):
        print(f"❌ 模板文件不存在: {template_file}")
        return False
    
    print(f"✅ 模板文件: {template_file}")
    
    # 读取模板文件内容
    try:
        template_data = pd.read_excel(template_file, sheet_name=None)  # 读取所有工作表
        template_sheets = list(template_data.keys())
        print(f"✅ 模板工作表: {template_sheets}")
        
        # 显示模板内容详情
        for sheet_name, df in template_data.items():
            print(f"   📄 {sheet_name}: {len(df)} 行, {len(df.columns)} 列")
            if len(df) > 0:
                print(f"      列名: {list(df.columns)}")
                print(f"      前2行:")
                print(df.head(2).to_string(index=False))
            else:
                print(f"      内容: 空")
        
    except Exception as e:
        print(f"❌ 读取模板文件失败: {e}")
        return False
    
    # 获取所有客户目录（排除模板文件本身）
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
                
                # 备份原文件
                backup_file = excel_file + f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
                shutil.copy2(excel_file, backup_file)
                print(f"   💾 原文件已备份: {os.path.basename(backup_file)}")
                
                # 清空原文件并写入模板内容
                with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                    for sheet_name in template_sheets:
                        if sheet_name in template_data:
                            # 复制模板工作表
                            template_df = template_data[sheet_name]
                            template_df.to_excel(writer, sheet_name=sheet_name, index=False)
                            print(f"      ✅ 已清空并写入模板: {sheet_name}")
                
                print(f"   ✅ 文件处理完成")
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
    success = clear_all_shipment_records_auto()
    if success:
        print("\n✅ 所有出货记录清空操作完成！")
        print("🎯 现在所有客户的出货记录都已用模板清空")
    else:
        print("\n❌ 出货记录清空操作失败！")
