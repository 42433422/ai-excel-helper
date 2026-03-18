import requests

print("=== 测试订单编号功能 ===")

print("\n1. 测试获取最新订单编号...")
r = requests.get('http://127.0.0.1:5000/api/orders/latest')
print(f"Status: {r.status_code}")
print(f"Response: {r.json()}")

print("\n2. 测试设置订单编号...")
r = requests.post('http://127.0.0.1:5000/api/orders/set-sequence', 
                 json={'order_number': '26-02-00100A'})
print(f"Status: {r.status_code}")
print(f"Response: {r.json()}")

print("\n3. 再次获取最新订单编号...")
r = requests.get('http://127.0.0.1:5000/api/orders/latest')
print(f"Status: {r.status_code}")
print(f"Response: {r.json()}")

print("\n4. 测试重置订单编号...")
r = requests.post('http://127.0.0.1:5000/api/orders/reset-sequence')
print(f"Status: {r.status_code}")
print(f"Response: {r.json()}")

print("\n5. 重置后获取最新订单编号...")
r = requests.get('http://127.0.0.1:5000/api/orders/latest')
print(f"Status: {r.status_code}")
print(f"Response: {r.json()}")

print("\n=== 测试完成 ===")
