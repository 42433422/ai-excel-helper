#!/usr/bin/env python3
import requests
import sys

url = "http://127.0.0.1:5000/api/shipment/search-products"
params = {
    "q": "PE白底",
    "unit": "蕊芯家私",
    "number_mode": "false"
}

try:
    response = requests.get(url, params=params, timeout=10)
    print(f"Status code: {response.status_code}")
    print(f"Response text: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
