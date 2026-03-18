#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看出货记录模板文件结构
"""

import os
import pandas as pd

def inspect_template():
    """检查模板文件结构"""
    
    # 模板文件路径
    template_file = r"C:\Users\97088\Desktop\新建文件夹 (4)\出货记录\出货记录模板.xlsx"
    
    print("📊 出货记录模板文件检查")
    print("=" * 50)
    
    if not os.path.exists(template_file):
        print(f"❌ 模板文件不存在: {template_file}")
        return
    
    print(f"✅ 模板文件: {template_file}")
    
    try:
        # 读取所有工作表
        template_data = pd.read_excel(template_file, sheet_name=None)
        
        print(f"📋 工作表数量: {len(template_data)}")
        print(f"📋 工作表列表: {list(template_data.keys())}")
        print()
        
        # 显示每个工作表的结构
        for sheet_name, df in template_data.items():
            print(f"📄 工作表: {sheet_name}")
            print(f"   行数: {len(df)}")
            print(f"   列数: {len(df.columns)}")
            print(f"   列名: {list(df.columns)}")
            
            if len(df) > 0:
                print(f"   前3行内容:")
                print(df.head(3).to_string(index=False))
            else:
                print(f"   内容: 空")
            
            print()
    
    except Exception as e:
        print(f"❌ 读取模板文件失败: {e}")

def list_all_client_files():
    """列出所有客户文件"""
    
    shipment_dir = r"C:\Users\97088\Desktop\新建文件夹 (4)\出货记录"
    
    print("📁 所有客户出货记录文件")
    print("=" * 50)
    
    client_dirs = []
    for item in os.listdir(shipment_dir):
        item_path = os.path.join(shipment_dir, item)
        if os.path.isdir(item_path) and item != '__pycache__':
            client_dirs.append((item, item_path))
    
    print(f"📊 总计客户数: {len(client_dirs)}")
    print()
    
    for i, (client_name, client_dir) in enumerate(client_dirs, 1):
        print(f"{i:2d}. {client_name}")
        
        excel_files = []
        for file in os.listdir(client_dir):
            if file.endswith('.xlsx') and file != '出货记录模板.xlsx':
                file_path = os.path.join(client_dir, file)
                try:
                    # 尝试读取文件获取工作表信息
                    data = pd.read_excel(file_path, sheet_name=None)
                    sheet_count = len(data)
                    sheet_names = list(data.keys())
                except Exception as e:
                    sheet_count = "读取失败"
                    sheet_names = str(e)
                
                excel_files.append({
                    'name': file,
                    'path': file_path,
                    'size': os.path.getsize(file_path),
                    'sheets': sheet_count,
                    'sheet_names': sheet_names
                })
        
        if excel_files:
            for file_info in excel_files:
                size = file_info['size']
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                else:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                
                print(f"    📄 {file_info['name']} ({size_str})")
                if isinstance(file_info['sheets'], int):
                    print(f"        工作表: {file_info['sheets']} 个")
                    if isinstance(file_info['sheet_names'], list):
                        print(f"        名称: {file_info['sheet_names']}")
                else:
                    print(f"        状态: {file_info['sheet_names']}")
        else:
            print(f"    ⚠️ 无Excel文件")
        
        print()

if __name__ == '__main__':
    # 检查模板文件结构
    inspect_template()
    
    print("\n" + "="*60 + "\n")
    
    # 列出所有客户文件
    list_all_client_files()
