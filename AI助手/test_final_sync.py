#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终测试Excel同步修复
"""

from shipment_document import DocumentAPIGenerator

def test_final_excel_sync():
    """测试最终的Excel同步功能"""
    print("=== 最终测试Excel同步修复 ===")
    
    # 创建文档生成器
    api = DocumentAPIGenerator()
    
    # 使用正确的Excel文件路径
    excel_path = r'C:\Users\97088\Desktop\新建文件夹 (4)\出货记录\七彩乐园\七彩乐园.xlsx'
    
    print(f"Excel文件路径: {excel_path}")
    
    # 启用Excel同步
    success = api.enable_excel_sync(excel_path, '25出货')
    print(f"启用Excel同步: {success}")
    print(f"同步管理器存在: {api.excel_sync_manager is not None}")
    print(f"同步已启用: {api.excel_sync_enabled}")
    
    # 测试订单文本
    test_order = '七彩乐园PE白底10桶规格28，PE白底稀释剂180kg1桶，Pu哑光白面漆5桶规格20'
    
    print(f"\n测试订单: {test_order}")
    
    # 解析并生成
    result = api.parse_and_generate(test_order, enable_excel_sync=True)
    
    print(f"\n解析结果: {'成功' if result['success'] else '失败'}")
    
    if result['success']:
        print(f"产品数量: {len(result['parsed_data']['products'])}")
        print("产品列表:")
        for p in result['parsed_data']['products']:
            print(f"- {p['name']} {p['quantity_tins']}桶")
        
        if 'excel_sync' in result:
            print(f"Excel同步结果: {result['excel_sync']['success']}")
            if result['excel_sync']['success']:
                print("✅ Excel同步成功！")
            else:
                print("❌ Excel同步失败！")
    else:
        print(f"失败原因: {result['message']}")

if __name__ == '__main__':
    test_final_excel_sync()
