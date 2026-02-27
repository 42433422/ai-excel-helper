import requests
import json

print("=" * 60)
print("测试完整扫描流程")
print("=" * 60)

# 1. 测试主服务状态
print("\n1. 测试主服务状态...")
try:
    response = requests.get('http://127.0.0.1:5001/api/status', timeout=5)
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ 主服务正常")
        print(f"   SDK加载: {data['device_info'].get('sdk_loaded')}")
        print(f"   设备连接: {data['device_info'].get('device_connected')}")
    else:
        print(f"   ❌ 主服务异常: {response.status_code}")
except Exception as e:
    print(f"   ❌ 连接失败: {e}")

# 2. 测试扫描功能
print("\n2. 测试扫描功能...")
try:
    response = requests.post(
        'http://127.0.0.1:5001/api/scan',
        json={'resolution': 'high'},
        timeout=30
    )
    
    if response.status_code == 200:
        result = response.json()
        if result.get('success'):
            print(f"   ✅ 扫描成功!")
            print(f"   图像ID: {result.get('image_id')}")
            print(f"   分辨率: {result.get('width')}x{result.get('height')}")
            print(f"   模式: {result.get('mode')}")
            print(f"   Base64长度: {len(result.get('image_base64', ''))}")
        else:
            print(f"   ❌ 扫描失败: {result.get('error')}")
    else:
        print(f"   ❌ 请求失败: {response.status_code}")
        
except Exception as e:
    print(f"   ❌ 请求异常: {e}")

print("\n" + "=" * 60)
print("测试完成！")
print("=" * 60)
