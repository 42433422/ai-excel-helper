import requests
import json

url = "http://127.0.0.1:8000/api/ai/unified_chat"
payload = {"message": "客户：深圳市百木鼎家具有限公司 产品：3721 3 KG, 1870D 3 KG, 8828 4 KG"}

response = requests.post(url, json=payload)
print(f"Status: {response.status_code}")
result = response.json()
print(f"\nResponse text:\n{result.get('text', '')}")
print(f"\nFull response:\n{json.dumps(result, indent=2, ensure_ascii=False)}")
