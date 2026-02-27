#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试具体订单的Excel同步功能
"""

import sys
import os
import logging

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shipment_document import DocumentAPIGenerator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_specific_order():
    """测试具体订单"""
    print("=" * 80)
    print("🧪 测试具体订单Excel同步")
    print("=" * 80)

    excel_path = "尹玉华132.xlsx"
    test_order = "蕊芯Pe白底漆10桶，规格28KG，PE稀释剂:1桶，规格180KG"

    try:
        # 创建文档生成器
        api_gen = DocumentAPIGenerator()

        # 启用Excel同步
        print(f"\n📁 启用Excel同步: {excel_path}")
        if api_gen.enable_excel_sync(excel_path):
            print("✅ Excel同步已启用")
        else:
            print("❌ Excel同步启用失败")
            return False

        # 分析列结构
        print("\n正在分析Excel列结构...")
        mapping = api_gen.analyze_excel_columns()
        print(f"✅ 列分析完成: 客户列={mapping.customer_column}, 产品列={mapping.product_column}")

        print(f"\n📦 测试订单: {test_order}")
        print("正在生成发货单并同步到Excel...")

        result = api_gen.parse_and_generate(test_order)

        if result["success"]:
            print("✅ 发货单生成成功!")

            # 检查Excel同步结果
            if "excel_sync" in result:
                sync_info = result["excel_sync"]
                print(f"\n📊 Excel同步信息:")
                print(f"  已启用: {sync_info['enabled']}")
                print(f"  同步成功: {sync_info['success']}")

            print(f"\n📄 发货单详情:")
            print(f"  文件: {result['document']['filename']}")
            print(f"  订单编号: {result['document']['order_number']}")
            print(f"  购买单位: {result['purchase_unit']['name'] if result['purchase_unit'] else '未知'}")
            print(f"  产品: {result['parsed_data']['product_name']}")
            print(f"  数量: {result['parsed_data']['quantity_kg']}KG")
            print(f"  桶数: {result['parsed_data']['quantity_tins']}桶")

            # 检查多个产品
            if result['parsed_data'].get('products'):
                print(f"\n📋 所有产品:")
                for i, product in enumerate(result['parsed_data']['products'], 1):
                    print(f"  {i}. {product['name']} - {product['quantity_tins']}桶, {product['quantity_kg']}KG")

            return True
        else:
            print(f"❌ 发货单生成失败: {result['message']}")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    # 切换到AI助手目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    success = test_specific_order()

    print("\n" + "=" * 80)
    if success:
        print("🎉 具体订单测试通过!")
    else:
        print("⚠️  测试失败，请检查错误信息")
    print("=" * 80)

    return success


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
