import requests
import json

# 测试并显示详细日志
url = "http://127.0.0.1:5000/api/generate"
data = {
    "order_text": "七彩乐园PE白底漆10桶规格28",
    "template_name": "尹玉华1.xlsx",
    "excel_sync": True
}

print("=== 测试同步 ===\n")

response = requests.post(url, json=data, timeout=30)
result = response.json()

print(f"成功: {result.get('success')}")
print(f"Excel同步: {result.get('excel_sync')}")
print()

# 解析数据
parsed = result.get('parsed_data', {})
print("parsed_data:")
print(json.dumps(parsed, ensure_ascii=False, indent=2))
