#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证出货记录清空结果
"""

import os
import pandas as pd

def verify_clear_results():
    """验证清空结果"""
    
    shipment_dir = r"C:\Users\97088\Desktop\新建文件夹 (4)\出货记录"
    template_file = os.path.join(shipment_dir, '出货记录模板.xlsx')
    
    print("🔍 验证出货记录清空结果")
    print("=" * 50)
    
    # 检查模板文件大小
    template_size = os.path.getsize(template_file)
    print(f"📊 模板文件大小: {template_size} bytes ({template_size/1024:.1f} KB)")
    
    # 获取所有客户目录
    client_dirs = []
    for item in os.listdir(shipment_dir):
        item_path = os.path.join(shipment_dir, item)
        if os.path.isdir(item_path) and item != '__pycache__':
            client_dirs.append((item, item_path))
    
    print(f"📁 检查 {len(client_dirs)} 个客户文件")
    print()
    
    success_count = 0
    failed_files = []
    
    for i, (client_name, client_dir) in enumerate(client_dirs, 1):
        print(f"{i:2d}. {client_name}")
        
        # 查找Excel文件
        excel_files = []
        for file in os.listdir(client_dir):
            if file.endswith('.xlsx') and file != '出货记录模板.xlsx':
                file_path = os.path.join(client_dir, file)
                excel_files.append(file_path)
        
        if excel_files:
            for file_path in excel_files:
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                
                # 验证文件
                try:
                    # 尝试读取文件
                    data = pd.read_excel(file_path, sheet_name=None)
                    sheet_count = len(data)
                    sheet_names = list(data.keys())
                    
                    # 检查是否是空文件（只有标题行）
                    is_empty = True
                    for sheet_name, df in data.items():
                        if len(df) > 0:
                            is_empty = False
                            break
                    
                    # 判断是否成功清空
                    if is_empty and file_size <= template_size * 1.5:  # 允许一定误差
                        status = "✅ 已清空"
                        success_count += 1
                    elif file_size > template_size * 2:
                        status = "⚠️ 可能未清空"
                        failed_files.append((client_name, file_name, "文件过大"))
                    else:
                        status = "⚠️ 状态不明确"
                        failed_files.append((client_name, file_name, "状态不明确"))
                    
                    print(f"    📄 {file_name}")
                    print(f"        大小: {file_size} bytes ({file_size/1024:.1f} KB)")
                    print(f"        工作表: {sheet_count} 个 - {sheet_names}")
                    print(f"        状态: {status}")
                    
                except Exception as e:
                    status = f"❌ 读取失败: {e}"
                    failed_files.append((client_name, file_name, f"读取失败: {e}"))
                    print(f"    📄 {file_name}")
                    print(f"        状态: {status}")
        else:
            print(f"    ⚠️ 未找到Excel文件")
        
        print()
    
    print("📊 验证结果统计")
    print("=" * 30)
    print(f"✅ 成功清空: {success_count} 个文件")
    print(f"❌ 失败/问题: {len(failed_files)} 个文件")
    
    if failed_files:
        print("\n❌ 问题文件列表:")
        for client, filename, reason in failed_files:
            print(f"   - {client}/{filename}: {reason}")

if __name__ == '__main__':
    verify_clear_results()
