import requests

url = "http://127.0.0.1:5000/api/materials"

response = requests.get(f"{url}?page=1&per_page=5")
data = response.json()

print("当前数据:")
for m in data.get('data', []):
    print(f"  ID={m['id']} (type={type(m['id']).__name__}), name={m['name']}")

print("\n测试字符串ID vs 整数ID:")

ids_int = [m['id'] for m in data.get('data', [])[:3]]
ids_str = [str(m['id']) for m in data.get('data', [])[:3]]

print(f"  Integer IDs: {ids_int}")
print(f"  String IDs: {ids_str}")

print("\n删除测试（使用整数ID）:")
response = requests.post(f"{url}/batch-delete", json={"material_ids": ids_int})
result = response.json()
print(f"  Result: {result}")

response = requests.get(f"{url}?page=1&per_page=5")
data = response.json()
print(f"  删除后总数: {data.get('total')}")