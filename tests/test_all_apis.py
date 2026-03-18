#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XCAGI 功能验证测试脚本

用于验证所有 API 接口是否真正工作。
"""

import requests
import json
import os

BASE_URL = "http://localhost:5000/api"


def test_customers_list():
    """测试购买单位列表查询"""
    print("\n=== 测试 1: GET /api/customers/list ===")

    response = requests.get(f"{BASE_URL}/customers/list")
    print(f"状态码：{response.status_code}")
    print(f"响应：{json.dumps(response.json(), indent=2, ensure_ascii=False)}")


def test_products_list():
    """测试产品列表"""
    print("\n=== 测试 2: GET /api/products/list ===")

    response = requests.get(f"{BASE_URL}/products/list")
    print(f"状态码：{response.status_code}")
    data = response.json()
    print(f"产品总数：{data.get('total', 0)}")


def test_shipment_list():
    """测试发货单列表"""
    print("\n=== 测试 3: GET /api/shipment/list ===")

    response = requests.get(f"{BASE_URL}/shipment/list")
    print(f"状态码：{response.status_code}")
    data = response.json()
    print(f"发货单总数：{data.get('total', 0)}")


def test_wechat_contacts():
    """测试微信联系人列表"""
    print("\n=== 测试 4: GET /api/wechat/contacts ===")

    response = requests.get(f"{BASE_URL}/wechat/contacts")
    print(f"状态码：{response.status_code}")
    data = response.json()
    print(f"联系人总数：{data.get('total', 0)}")


def test_wechat_tasks():
    """测试微信任务列表"""
    print("\n=== 测试 5: GET /api/wechat/tasks ===")

    response = requests.get(f"{BASE_URL}/wechat/tasks")
    print(f"状态码：{response.status_code}")
    data = response.json()
    print(f"任务总数：{data.get('total', 0)}")


def test_printers():
    """测试打印机列表"""
    print("\n=== 测试 6: GET /api/print/printers ===")

    response = requests.get(f"{BASE_URL}/print/printers")
    print(f"状态码：{response.status_code}")
    data = response.json()
    print(f"打印机数量：{data.get('count', 0)}")
    print(f"响应：{json.dumps(data, indent=2, ensure_ascii=False)}")


def test_print_default():
    """测试获取默认打印机"""
    print("\n=== 测试 7: GET /api/print/default ===")

    response = requests.get(f"{BASE_URL}/print/default")
    print(f"状态码：{response.status_code}")
    data = response.json()
    print(f"响应：{json.dumps(data, indent=2, ensure_ascii=False)}")


def test_print_validate():
    """测试打印机验证"""
    print("\n=== 测试 8: GET /api/print/validate ===")

    response = requests.get(f"{BASE_URL}/print/validate")
    print(f"状态码：{response.status_code}")
    data = response.json()
    print(f"响应：{json.dumps(data, indent=2, ensure_ascii=False)}")


def test_ocr_test():
    """测试OCR服务"""
    print("\n=== 测试 9: GET /api/ocr/test ===")

    response = requests.get(f"{BASE_URL}/ocr/test")
    print(f"状态码：{response.status_code}")
    data = response.json()
    print(f"响应：{json.dumps(data, indent=2, ensure_ascii=False)}")


def test_ai_chat():
    """测试AI聊天"""
    print("\n=== 测试 10: POST /api/ai/chat ===")

    response = requests.post(
        f"{BASE_URL}/ai/chat",
        json={"message": "你好"}
    )
    print(f"状态码：{response.status_code}")
    data = response.json()
    print(f"响应：{json.dumps(data, indent=2, ensure_ascii=False)}")


def test_ai_test():
    """测试AI服务"""
    print("\n=== 测试 11: GET /api/ai/test ===")

    response = requests.get(f"{BASE_URL}/ai/test")
    print(f"状态码：{response.status_code}")
    data = response.json()
    print(f"响应：{json.dumps(data, indent=2, ensure_ascii=False)}")


def test_intent_test():
    """测试意图识别"""
    print("\n=== 测试 12: POST /api/ai/intent/test ===")

    response = requests.post(
        f"{BASE_URL}/ai/intent/test",
        json={"message": "生成发货单"}
    )
    print(f"状态码：{response.status_code}")
    data = response.json()
    print(f"响应：{json.dumps(data, indent=2, ensure_ascii=False)}")


def main():
    """主测试函数"""
    print("=" * 60)
    print("XCAGI 功能验证测试")
    print("=" * 60)
    print("\n请确保 Flask 应用已在 http://localhost:5000 运行")
    print("按 Enter 键开始测试...")
    input()

    try:
        test_customers_list()
        test_products_list()
        test_shipment_list()
        test_wechat_contacts()
        test_wechat_tasks()
        test_printers()
        test_print_default()
        test_print_validate()
        test_ocr_test()
        test_ai_chat()
        test_ai_test()
        test_intent_test()

        print("\n" + "=" * 60)
        print("✅ 所有测试完成！")
        print("=" * 60)

    except requests.exceptions.ConnectionError:
        print("\n❌ 错误：无法连接到 Flask 应用")
        print("请确保已运行：python run.py")
    except Exception as e:
        print(f"\n❌ 测试过程中出错：{e}")


if __name__ == "__main__":
    main()
