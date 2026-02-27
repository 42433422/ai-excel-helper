#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
出货记录清空脚本 - 使用模板清空所有客户的出货记录
"""

import os
import shutil
import pandas as pd
from datetime import datetime

def clear_all_shipment_records():
    """清空所有客户的出货记录并用模板替换"""
    
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
    except Exception as e:
        print(f"❌ 读取模板文件失败: {e}")
        return False
    
    # 获取所有客户目录（排除模板文件本身）
    client_dirs = []
    for item in os.listdir(shipment_dir):
        item_path = os.path.join(shipment_dir, item)
        if os.path.isdir(item_path) and item != '__pycache__':
            client_dirs.append((item, item_path))
    
    print(f"📁 发现 {len(client_dirs)} 个客户目录")
    
    # 处理每个客户的出货记录
    processed_count = 0
    for client_name, client_dir in client_dirs:
        print(f"\n🏭 处理客户: {client_name}")
        
        # 查找客户的Excel文件
        excel_files = []
        for file in os.listdir(client_dir):
            if file.endswith('.xlsx') and file != '出货记录模板.xlsx':
                excel_files.append(os.path.join(client_dir, file))
        
        if not excel_files:
            print(f"   ⚠️ 未找到Excel文件")
            continue
        
        # 处理每个Excel文件
        for excel_file in excel_files:
            try:
                print(f"   📄 处理文件: {os.path.basename(excel_file)}")
                
                # 备份原文件（可选）
                backup_file = excel_file + '.backup'
                shutil.copy2(excel_file, backup_file)
                print(f"   💾 原文件已备份: {os.path.basename(backup_file)}")
                
                # 清空原文件
                with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                    for sheet_name in template_sheets:
                        if sheet_name in template_data:
                            # 复制模板工作表
                            template_df = template_data[sheet_name]
                            template_df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                print(f"   ✅ 文件已清空并用模板替换")
                processed_count += 1
                
            except Exception as e:
                print(f"   ❌ 处理失败: {e}")
                continue
    
    print(f"\n🎉 清空完成！")
    print(f"📊 处理统计:")
    print(f"   客户目录数: {len(client_dirs)}")
    print(f"   成功处理文件数: {processed_count}")
    
    return True

def show_summary():
    """显示处理摘要"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    shipment_dir = os.path.join(base_dir, '..', '出货记录')
    
    print("\n📋 出货记录目录摘要")
    print("=" * 50)
    
    # 获取所有客户目录
    client_dirs = []
    for item in os.listdir(shipment_dir):
        item_path = os.path.join(shipment_dir, item)
        if os.path.isdir(item_path) and item != '__pycache__':
            client_dirs.append((item, item_path))
    
    print(f"总计客户数: {len(client_dirs)}")
    print()
    
    for i, (client_name, client_dir) in enumerate(client_dirs, 1):
        excel_files = []
        for file in os.listdir(client_dir):
            if file.endswith('.xlsx'):
                excel_files.append(file)
        
        print(f"{i:2d}. {client_name}")
        for excel_file in excel_files:
            file_path = os.path.join(client_dir, excel_file)
            file_size = os.path.getsize(file_path)
            if file_size < 1024:
                size_str = f"{file_size} B"
            elif file_size < 1024 * 1024:
                size_str = f"{file_size / 1024:.1f} KB"
            else:
                size_str = f"{file_size / (1024 * 1024):.1f} MB"
            print(f"    📄 {excel_file} ({size_str})")
        print()

if __name__ == '__main__':
    # 显示目录摘要
    show_summary()
    
    print("\n🔄 准备清空所有出货记录...")
    print("⚠️  此操作将清空所有客户的出货记录并用模板替换")
    print("⚠️  原文件将被备份为 .backup 文件")
    
    # 确认操作
    confirm = input("\n❓ 确认执行清空操作吗？(输入 'yes' 确认): ")
    
    if confirm.lower() in ['yes', 'y', '确认', '是']:
        success = clear_all_shipment_records()
        if success:
            print("\n✅ 所有出货记录清空操作完成！")
        else:
            print("\n❌ 出货记录清空操作失败！")
    else:
        print("\n❌ 操作已取消")
