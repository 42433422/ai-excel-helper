import requests
import json

# 测试余额查询API
response = requests.get('http://127.0.0.1:5000/api/ocr/balance')
print("状态码:", response.status_code)
print("\n返回数据:")
print(json.dumps(response.json(), ensure_ascii=False, indent=2))
