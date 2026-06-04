import requests
import json

url = "http://127.0.0.1:8000/api/sales-contract/generate"
payload = {
    "customer_name": "七彩乐园",
    "products": [
        {
            "model_number": "3721",
            "name": "",
            "spec": "",
            "unit": "",
            "quantity": "3",
            "unit_price": "0",
            "amount": "0",
        },
        {
            "model_number": "1870D",
            "name": "",
            "spec": "",
            "unit": "",
            "quantity": "3",
            "unit_price": "0",
            "amount": "0",
        },
        {
            "model_number": "8828",
            "name": "",
            "spec": "",
            "unit": "",
            "quantity": "4",
            "unit_price": "0",
            "amount": "0",
        },
    ],
}

response = requests.post(url, json=payload)
print(f"Status: {response.status_code}")
result = response.json()
print(f"Success: {result.get('success')}")
if result.get("success"):
    data = result.get("data", {})
    print(f"File: {data.get('file_path')}")
    print(f"Products: {json.dumps(data.get('products', []), indent=2, ensure_ascii=False)}")
else:
    print(f"Error: {result.get('error')}")
