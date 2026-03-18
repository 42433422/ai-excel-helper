import ctypes
import os
import sys

print("=" * 60)
print("测试32位Python加载科密DLL")
print("=" * 60)

comet_path = r"C:\Program Files\Comet Scanner_V2.0(1.1)"

# 测试加载CameraPro.dll
camera_dll_path = os.path.join(comet_path, "CameraPro.dll")
print(f"\n1. 测试加载 CameraPro.dll")
print(f"   路径: {camera_dll_path}")
print(f"   文件存在: {os.path.exists(camera_dll_path)}")

try:
    camera_dll = ctypes.windll.LoadLibrary(camera_dll_path)
    print(f"   ✅ 加载成功!")
    print(f"   模块句柄: {camera_dll._handle}")
except Exception as e:
    print(f"   ❌ 加载失败: {e}")

# 测试加载CM_ImagePro.dll
image_dll_path = os.path.join(comet_path, "CM_ImagePro.dll")
print(f"\n2. 测试加载 CM_ImagePro.dll")
print(f"   路径: {image_dll_path}")
print(f"   文件存在: {os.path.exists(image_dll_path)}")

try:
    image_dll = ctypes.windll.LoadLibrary(image_dll_path)
    print(f"   ✅ 加载成功!")
    print(f"   模块句柄: {image_dll._handle}")
except Exception as e:
    print(f"   ❌ 加载失败: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
