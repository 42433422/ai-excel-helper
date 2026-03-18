import requests

print("=== 检查服务器路由 ===")

# 测试获取最新订单编号
r = requests.get('http://127.0.0.1:5000/api/orders/latest')
print(f"GET /api/orders/latest: {r.status_code}")

# 测试设置订单编号 - 使用 OPTIONS 方法检查
r = requests.options('http://127.0.0.1:5000/api/orders/set-sequence')
print(f"OPTIONS /api/orders/set-sequence: {r.status_code}")
print(f"Allow header: {r.headers.get('Allow', 'N/A')}")

# 测试设置订单编号 - 使用 POST
r = requests.post('http://127.0.0.1:5000/api/orders/set-sequence', 
                 json={'order_number': '26-02-00100A'},
                 headers={'Content-Type': 'application/json'})
print(f"POST /api/orders/set-sequence: {r.status_code}")
print(f"Response text: {r.text[:500] if r.text else 'Empty'}")
