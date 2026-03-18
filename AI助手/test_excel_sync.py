#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试Excel出货记录同步功能
"""

import sys
import os
import logging

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shipment_document import DocumentAPIGenerator
from shipment_excel_sync import ShipmentRecordSyncManager, ShipmentRecord

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_intelligent_excel_analysis():
    """测试智能Excel列分析"""
    print("=" * 80)
    print("测试1: 智能Excel列分析")
    print("=" * 80)

    excel_path = "尹玉华132.xlsx"

    if not os.path.exists(excel_path):
        print(f"❌ 文件不存在: {excel_path}")
        return False

    try:
        manager = ShipmentRecordSyncManager(excel_path)
        print(f"✅ 成功加载Excel文件: {excel_path}")

        # 分析列结构
        print("\n正在使用AI分析列结构...")
        mapping = manager.analyze_and_configure()

        print(f"\n📊 列映射结果:")
        print(f"  客户名称列: {mapping.customer_column}")
        print(f"  订单编号列: {mapping.order_number_column}")
        print(f"  产品名称列: {mapping.product_column}")
        print(f"  数量列: {mapping.quantity_column}")
        print(f"  单价列: {mapping.unit_price_column}")
        print(f"  金额列: {mapping.amount_column}")
        print(f"  日期列: {mapping.date_column}")
        print(f"  备注列: {mapping.remarks_column}")

        return True

    except Exception as e:
        print(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_record_insertion():
    """测试记录插入"""
    print("\n" + "=" * 80)
    print("测试2: 测试记录插入")
    print("=" * 80)

    excel_path = "尹玉华132.xlsx"

    try:
        manager = ShipmentRecordSyncManager(excel_path)
        manager.analyze_and_configure()

        # 创建测试记录
        test_record = ShipmentRecord(
            customer_name="测试客户",
            order_number="26-010001A",
            product_name="PU白底漆",
            quantity=20.0,
            unit_price=15.0,
            amount=300.0,
            date="2026-01-28",
            remarks="测试记录"
        )

        print(f"\n📝 测试记录:")
        print(f"  客户: {test_record.customer_name}")
        print(f"  订单号: {test_record.order_number}")
        print(f"  产品: {test_record.product_name}")
        print(f"  数量: {test_record.quantity}KG")
        print(f"  单价: {test_record.unit_price}元")
        print(f"  金额: {test_record.amount}元")

        # 插入记录
        print("\n正在插入记录...")
        if manager.insert_shipment_record(test_record):
            print("✅ 记录插入成功!")
            return True
        else:
            print("❌ 记录插入失败!")
            return False

    except Exception as e:
        print(f"❌ 插入测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_document_generation_with_sync():
    """测试发货单生成并同步"""
    print("\n" + "=" * 80)
    print("测试3: 发货单生成并同步到Excel")
    print("=" * 80)

    excel_path = "尹玉华132.xlsx"

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

        # 生成测试订单
        test_order = "蕊芯PU哑光黑面漆20公斤"

        print(f"\n📦 测试订单: {test_order}")
        print("正在生成发货单...")

        result = api_gen.parse_and_generate(test_order)

        if result["success"]:
            print("✅ 发货单生成成功!")

            # 检查Excel同步结果
            if "excel_sync" in result:
                sync_info = result["excel_sync"]
                print(f"\n📊 Excel同步信息:")
                print(f"  已启用: {sync_info['enabled']}")
                print(f"  同步成功: {sync_info['success']}")

            print(f"\n📄 发货单文件: {result['document']['filename']}")
            print(f"  订单编号: {result['document']['order_number']}")
            print(f"  购买单位: {result['purchase_unit']['name'] if result['purchase_unit'] else '未知'}")
            print(f"  产品: {result['parsed_data']['product_name']}")
            print(f"  数量: {result['parsed_data']['quantity_kg']}KG")

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
    """主测试函数"""
    print("\n" + "=" * 80)
    print("🧪 Excel出货记录同步功能测试")
    print("=" * 80)

    # 切换到AI助手目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    results = []

    # 测试1: 智能Excel列分析
    results.append(("智能Excel列分析", test_intelligent_excel_analysis()))

    # 测试2: 记录插入
    results.append(("记录插入", test_record_insertion()))

    # 测试3: 发货单生成并同步
    results.append(("发货单生成并同步", test_document_generation_with_sync()))

    # 汇总结果
    print("\n" + "=" * 80)
    print("📋 测试结果汇总")
    print("=" * 80)

    all_passed = True
    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 80)
    if all_passed:
        print("🎉 所有测试通过!")
    else:
        print("⚠️  部分测试失败，请检查错误信息")
    print("=" * 80)

    return all_passed


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
