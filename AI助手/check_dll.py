import ctypes
import os
import sys
import struct

def check_dll_architecture(dll_path):
    """检查DLL架构（32位或64位）"""
    try:
        with open(dll_path, 'rb') as f:
            # 读取DOS头
            dos_header = f.read(64)
            if len(dos_header) < 64:
                return "Invalid file"
            
            # 获取PE头偏移
            pe_offset = struct.unpack('<L', dos_header[60:64])[0]
            
            # 跳转到PE头
            f.seek(pe_offset)
            pe_header = f.read(24)
            
            if len(pe_header) < 24:
                return "Invalid PE header"
            
            # 检查PE签名
            if pe_header[:4] != b'PE\x00\x00':
                return "Not a PE file"
            
            # 获取机器类型
            machine_type = struct.unpack('<H', pe_header[4:6])[0]
            
            arch_map = {
                0x14c: "x86 (32-bit)",
                0x8664: "x64 (64-bit)",
                0xaa64: "ARM64",
                0x1c0: "ARM"
            }
            
            return arch_map.get(machine_type, f"Unknown (0x{machine_type:04x})")
            
    except Exception as e:
        return f"Error: {e}"

def list_dll_exports(dll_path):
    """列出DLL导出的函数"""
    try:
        # 加载DLL
        dll = ctypes.windll.LoadLibrary(dll_path)
        
        # 获取模块句柄
        handle = dll._handle
        
        print(f"✅ DLL加载成功: {dll_path}")
        print(f"模块句柄: {handle}")
        
        # 尝试获取导出函数（使用Windows API）
        from ctypes import wintypes
        
        kernel32 = ctypes.windll.kernel32
        
        # GetProcAddress需要模块句柄和函数名
        # 这里我们无法直接列出所有导出函数，需要其他方法
        
        return True
        
    except Exception as e:
        print(f"❌ DLL加载失败: {e}")
        return False

# 检查科密DLL
comet_path = r"C:\Program Files\Comet Scanner_V2.0(1.1)"

dll_files = [
    "CameraPro.dll",
    "CM_ImagePro.dll"
]

print("=" * 60)
print("科密DLL架构检查")
print("=" * 60)

for dll_name in dll_files:
    dll_path = os.path.join(comet_path, dll_name)
    if os.path.exists(dll_path):
        arch = check_dll_architecture(dll_path)
        print(f"\n{dll_name}:")
        print(f"  路径: {dll_path}")
        print(f"  架构: {arch}")
        
        # 尝试加载
        print(f"  加载测试:")
        list_dll_exports(dll_path)
    else:
        print(f"\n{dll_name}: 文件不存在")

print("\n" + "=" * 60)
print("Python架构信息")
print("=" * 60)
print(f"Python版本: {sys.version}")
print(f"Python架构: {struct.calcsize('P') * 8}-bit")
print(f"平台: {sys.platform}")
