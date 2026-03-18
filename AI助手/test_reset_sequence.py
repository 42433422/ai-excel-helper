import requests

print("测试重置订单序列API...")

try:
    response = requests.post('http://127.0.0.1:5000/api/orders/reset-sequence', timeout=10)
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.text}")
except Exception as e:
    print(f"错误: {e}")
