import requests
import json

print("=" * 60)
print("测试32位扫描代理服务")
print("=" * 60)

try:
    # 测试服务状态
    print("\n1. 测试服务状态...")
    response = requests.get('http://127.0.0.1:5002/', timeout=5)
    print(f"   状态码: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   服务: {data.get('service')}")
        print(f"   DLL加载: {data.get('dll_loaded')}")
    else:
        print(f"   响应: {response.text}")
        
except Exception as e:
    print(f"   ❌ 连接失败: {e}")
    print("   请确保32位代理服务已启动")

print("\n" + "=" * 60)
