import requests

url = "http://127.0.0.1:5000/api/materials"

response = requests.get(f"{url}?page=1&per_page=100")
data = response.json()
print(f"当前原材料总数: {data.get('total')}")
print(f"当前页材料数量: {len(data.get('data', []))}")

if data.get('data'):
    print("\n前5条材料:")
    for m in data.get('data')[:5]:
        print(f"  ID={m['id']}, name={m['name']}")