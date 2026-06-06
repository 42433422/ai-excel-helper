"""
销售合同功能测试
测试前后端集成的销售合同生成和表格显示功能
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"


def test_health():
    """测试后端健康状态"""
    response = requests.get(f"{BASE_URL}/api/health")
    print(f"后端健康状态：{response.status_code} - {response.json()}")
    return response.status_code == 200


def test_sales_contract_generate():
    """测试销售合同生成"""
    print("\n=== 测试销售合同生成 ===")

    url = f"{BASE_URL}/api/sales-contract/generate"
    payload = {
        "customer_name": "深圳市百木鼎家具有限公司",
        "products": [
            {"model_number": "3721", "quantity": "3"},
            {"model_number": "1870D", "quantity": "3"},
            {"model_number": "8828", "quantity": "4"},
        ],
    }

    response = requests.post(url, json=payload)
    print(f"状态码：{response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"成功：{result.get('success')}")

        if result.get("success"):
            data = result.get("data", {})
            products = data.get("products", [])

            print(f"\n合同信息:")
            print(f"  客户：{data.get('customer_name')}")
            print(f"  文件：{data.get('filename')}")
            print(f"  路径：{data.get('file_path')}")

            print(f"\n产品列表:")
            total = 0
            for p in products:
                qty = float(p.get("quantity", 0))
                spec_qty = (
                    float(p.get("specification", "0").replace("KG", "").replace("桶", ""))
                    if p.get("specification")
                    else 1
                )
                price = float(p.get("unit_price", 0))
                amount = float(p.get("amount", 0))
                total += amount

                print(f"  - 型号 {p.get('model_number')}:")
                print(f"      名称：{p.get('name')}")
                print(f"      规格：{p.get('specification')}")
                print(f"      单位：{p.get('unit')}")
                print(f"      数量：{qty}")
                print(f"      单价：{price}")
                print(f"      金额：{amount}")

            print(f"\n总计金额：{total:.2f}元")

            # 验证金额计算
            print(f"\n验证金额计算:")
            for p in products:
                qty = float(p.get("quantity", 0))
                spec = p.get("specification", "")
                import re

                match = re.search(
                    r"(\d+(?:\.\d+)?)\s*(KG|公斤 | 克 | 升 | 毫升 | 桶)", spec, re.IGNORECASE
                )
                spec_qty = float(match.group(1)) if match else 1.0
                price = float(p.get("unit_price", 0))
                expected = qty * spec_qty * price
                actual = float(p.get("amount", 0))

                print(
                    f"  {p.get('model_number')}: {qty} × {spec_qty} × {price} = {expected:.2f} (实际：{actual:.2f}) {'✓' if abs(expected - actual) < 0.01 else '✗'}"
                )

            return True
        else:
            print(f"错误：{result.get('error')}")
            return False
    else:
        print(f"请求失败：{response.text}")
        return False


def test_ai_chat():
    """测试 AI 统一对话接口"""
    print("\n=== 测试 AI 统一对话接口 ===")

    url = f"{BASE_URL}/api/ai/unified_chat"
    payload = {
        "message": "打印销售合同 客户：深圳市百木鼎家具有限公司 产品：3721 3 KG, 1870D 3 KG, 8828 4 KG"
    }

    response = requests.post(url, json=payload, timeout=60)
    print(f"状态码：{response.status_code}")

    if response.status_code == 200:
        result = response.json()
        text = result.get("text", "")

        print(f"\nAI 响应:")
        print(text[:500] if len(text) > 500 else text)

        # 检查是否包含 HTML 表格
        if "<table" in text:
            print("\n✓ 响应包含 HTML 表格")
        else:
            print("\n✗ 响应不包含 HTML 表格")

        return True
    else:
        print(f"请求失败：{response.text}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("销售合同功能测试")
    print("=" * 60)

    # 测试后端健康
    if not test_health():
        print("\n❌ 后端未运行或异常")
        exit(1)

    # 测试销售合同生成
    contract_ok = test_sales_contract_generate()

    # 测试 AI 对话
    ai_ok = test_ai_chat()

    print("\n" + "=" * 60)
    print("测试结果:")
    print(f"  销售合同生成：{'✓ 通过' if contract_ok else '✗ 失败'}")
    print(f"  AI 对话接口：{'✓ 通过' if ai_ok else '✗ 失败'}")
    print("=" * 60)

    if contract_ok and ai_ok:
        print("\n✅ 所有测试通过！")
    else:
        print("\n❌ 部分测试失败")
