import requests

# Test batch delete API
url = "http://127.0.0.1:5000/api/materials/batch-delete"

# First, get the list of materials to find some IDs to delete
response = requests.get("http://127.0.0.1:5000/api/materials?page=1&per_page=5")
data = response.json()
print("Materials before delete:")
print(f"  Total: {data.get('total')}")
for m in data.get('data', []):
    print(f"  ID={m['id']}, name={m['name']}")

# Get IDs
ids = [m['id'] for m in data.get('data', [])[:3]]  # Take first 3
print(f"\nAttempting to delete IDs: {ids}")

# Now try batch delete
response = requests.post(url, json={"material_ids": ids})
print(f"\nBatch delete response: {response.status_code}")
print(f"Response body: {response.json()}")

# Get the list again
response = requests.get("http://127.0.0.1:5000/api/materials?page=1&per_page=5")
data = response.json()
print("\nMaterials after delete:")
print(f"  Total: {data.get('total')}")
for m in data.get('data', []):
    print(f"  ID={m['id']}, name={m['name']}")