import requests

url = "http://127.0.0.1:5000/api/materials"

response = requests.get(f"{url}?page=1&per_page=100")
data = response.json()
total_before = data.get('total', 0)
print(f"删除前总数: {total_before}")

if total_before >= 20:
    ids_to_delete = [m['id'] for m in data.get('data', [])[:20]]
    print(f"要删除的IDs: {ids_to_delete[:5]}... (共{len(ids_to_delete)}个)")

    response = requests.post(f"{url}/batch-delete", json={"material_ids": ids_to_delete})
    result = response.json()
    print(f"删除API响应: {result}")

    response = requests.get(f"{url}?page=1&per_page=100")
    data = response.json()
    total_after = data.get('total', 0)
    print(f"删除后总数: {total_after}")
    print(f"实际删除: {total_before - total_after} 条")
else:
    print(f"材料不足20条，当前只有 {total_before} 条")