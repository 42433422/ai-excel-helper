#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细检查清空结果
"""

import os
import pandas as pd

def detailed_check():
    """详细检查清空结果"""
    
    # 随机选择几个客户进行详细检查
    clients_to_check = ['七彩乐园', '侯雪梅', '博旺家私', '金汉武']
    shipment_dir = r"C:\Users\97088\Desktop\新建文件夹 (4)\出货记录"
    
    print("🔍 详细检查清空结果")
    print("=" * 50)
    
    for client in clients_to_check:
        print(f"\n🏭 检查客户: {client}")
        
        client_dir = os.path.join(shipment_dir, client)
        
        # 查找Excel文件
        for file in os.listdir(client_dir):
            if file.endswith('.xlsx') and file != '出货记录模板.xlsx':
                file_path = os.path.join(client_dir, file)
                
                print(f"📄 文件: {file}")
                print(f"   大小: {os.path.getsize(file_path)} bytes")
                
                try:
                    # 读取工作表
                    data = pd.read_excel(file_path, sheet_name=None)
                    
                    for sheet_name, df in data.items():
                        print(f"   📋 工作表: {sheet_name}")
                        print(f"      行数: {len(df)}")
                        print(f"      列数: {len(df.columns)}")
                        print(f"      列名: {list(df.columns)}")
                        
                        if len(df) == 0:
                            print(f"      ✅ 内容: 空（已清空）")
                        else:
                            print(f"      📊 前3行:")
                            print(df.head(3).to_string(index=False))
                        
                        print()
                
                except Exception as e:
                    print(f"   ❌ 读取失败: {e}")
                
                print("-" * 40)

def check_template():
    """检查模板内容"""
    template_file = r"C:\Users\97088\Desktop\新建文件夹 (4)\出货记录\出货记录模板.xlsx"
    
    print("\n📊 模板文件内容")
    print("=" * 30)
    
    try:
        data = pd.read_excel(template_file, sheet_name=None)
        
        for sheet_name, df in data.items():
            print(f"📋 工作表: {sheet_name}")
            print(f"   行数: {len(df)}")
            print(f"   列数: {len(df.columns)}")
            print(f"   列名: {list(df.columns)}")
            
            if len(df) == 0:
                print(f"   内容: 空")
            else:
                print(f"   前3行:")
                print(df.head(3).to_string(index=False))
            
            print()
    
    except Exception as e:
        print(f"❌ 读取模板失败: {e}")

if __name__ == '__main__':
    detailed_check()
    check_template()
