import requests
import json

# 测试生成发货单并详细检查返回数据
url = "http://127.0.0.1:5000/api/generate"
data = {
    "order_text": "七彩乐园PE白底漆10桶规格28",
    "template_name": "尹玉华1.xlsx",
    "excel_sync": True
}

print("=== 详细测试 ===\n")

response = requests.post(url, json=data, timeout=30)
result = response.json()

print("完整返回结果:")
print(json.dumps(result, ensure_ascii=False, indent=2))
