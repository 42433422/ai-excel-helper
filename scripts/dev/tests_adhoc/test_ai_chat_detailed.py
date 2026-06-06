"""
测试 AI 对话接口返回的数据
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"


def test_ai_chat_detailed():
    """测试 AI 对话接口详细输出"""
    print("=== 测试 AI 对话接口 ===\n")

    url = f"{BASE_URL}/api/ai/unified_chat"
    payload = {
        "message": "打印销售合同 客户：深圳市百木鼎家具有限公司 产品：3721 3 KG, 1870D 3 KG, 8828 4 KG"
    }

    response = requests.post(url, json=payload, timeout=60)
    print(f"状态码：{response.status_code}")

    if response.status_code == 200:
        result = response.json()

        print(f"\n完整响应:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        print(f"\n\n=== 分析 ===")
        print(f"text 字段长度：{len(result.get('text', ''))}")
        print(f"data 字段：{json.dumps(result.get('data', {}), indent=2, ensure_ascii=False)}")

        # 检查是否包含 HTML 表格
        text = result.get("text", "")
        if "<table" in text:
            print("\n✓ text 字段包含 HTML 表格")
            # 提取表格部分
            start = text.find("<table")
            end = text.find("</table>") + 8
            if start >= 0 and end > start:
                print(f"\n表格 HTML:\n{text[start:end]}")
        else:
            print("\n✗ text 字段不包含 HTML 表格")
            print(f"\ntext 内容:\n{text}")
    else:
        print(f"请求失败：{response.text}")


if __name__ == "__main__":
    test_ai_chat_detailed()
