import requests
import json

# 测试科密扫描服务API
base_url = "http://127.0.0.1:5001"

print("=" * 50)
print("测试科密CM500扫描服务")
print("=" * 50)

# 1. 测试状态接口
print("\n1. 测试状态接口...")
try:
    response = requests.get(f"{base_url}/api/status", timeout=5)
    print(f"状态码: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"错误: {e}")

# 2. 测试扫描接口
print("\n2. 测试扫描接口...")
try:
    response = requests.post(
        f"{base_url}/api/scan",
        json={"resolution": "high"},
        timeout=10
    )
    print(f"状态码: {response.status_code}")
    result = response.json()
    if result.get('success'):
        print(f"✅ 扫描成功!")
        print(f"   图像ID: {result.get('image_id')}")
        print(f"   文件名: {result.get('filename')}")
        print(f"   分辨率: {result.get('width')}x{result.get('height')}")
        print(f"   模式: {result.get('mode')}")
        print(f"   Base64长度: {len(result.get('image_base64', ''))}")
    else:
        print(f"❌ 扫描失败: {result.get('error')}")
except Exception as e:
    print(f"错误: {e}")

print("\n" + "=" * 50)
print("测试完成")
print("=" * 50)
