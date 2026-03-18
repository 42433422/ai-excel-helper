#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证正确的清空结果
"""

import os
import pandas as pd

def verify_correct_result():
    """验证正确的清空结果"""
    
    # 随机选择几个客户进行验证
    clients_to_check = ['七彩乐园', '侯雪梅', '博旺家私', '金汉武']
    shipment_dir = r"C:\Users\97088\Desktop\新建文件夹 (4)\出货记录"
    template_file = os.path.join(shipment_dir, '出货记录模板.xlsx')
    
    print("🔍 验证正确的清空结果")
    print("=" * 50)
    
    # 先检查模板
    print("📊 模板文件内容:")
    template_data = pd.read_excel(template_file, sheet_name=None, header=None)
    for sheet_name, df in template_data.items():
        print(f"   📄 {sheet_name}: {df.shape[0]} 行, {df.shape[1]} 列")
        print(f"      前3行:")
        print(df.head(3).to_string(index=False))
        print()
    
    print("📁 客户文件验证:")
    print("=" * 30)
    
    for client in clients_to_check:
        print(f"\n🏭 客户: {client}")
        
        client_dir = os.path.join(shipment_dir, client)
        
        # 查找Excel文件
        for file in os.listdir(client_dir):
            if file.endswith('.xlsx') and file != '出货记录模板.xlsx':
                file_path = os.path.join(client_dir, file)
                
                print(f"📄 文件: {file}")
                print(f"   大小: {os.path.getsize(file_path)} bytes")
                
                try:
                    # 读取文件
                    data = pd.read_excel(file_path, sheet_name=None, header=None)
                    
                    for sheet_name, df in data.items():
                        print(f"   📋 工作表: {sheet_name}")
                        print(f"      行数: {df.shape[0]}")
                        print(f"      列数: {df.shape[1]}")
                        
                        # 检查格式是否与模板一致
                        template_df = template_data[sheet_name]
                        if df.shape == template_df.shape:
                            print(f"      ✅ 格式与模板一致 ({template_df.shape[0]} 行, {template_df.shape[1]} 列)")
                        else:
                            print(f"      ❌ 格式与模板不一致")
                            print(f"         模板: {template_df.shape[0]} 行, {template_df.shape[1]} 列")
                            print(f"         文件: {df.shape[0]} 行, {df.shape[1]} 列")
                        
                        # 显示前几行内容
                        if len(df) > 0:
                            print(f"      前2行:")
                            print(df.head(2).to_string(index=False))
                        else:
                            print(f"      内容: 空")
                        
                        print()
                
                except Exception as e:
                    print(f"   ❌ 读取失败: {e}")
                
                print("-" * 40)

if __name__ == '__main__':
    verify_correct_result()
