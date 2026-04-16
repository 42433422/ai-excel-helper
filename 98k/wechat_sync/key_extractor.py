"""
微信数据库密钥提取模块
支持从微信进程内存中提取 SQLCipher 密钥
"""
import os
import sys
import json
import struct
import glob
import platform
from datetime import datetime


def get_wechat_db_dir():
    """自动检测微信数据目录"""
    system = platform.system().lower()
    
    if system == "windows":
        # Windows: 从 %APPDATA%\Tencent\xwechat\config\*.ini 读取
        appdata = os.environ.get("APPDATA", "")
        config_dir = os.path.join(appdata, "Tencent", "xwechat", "config")
        
        if os.path.isdir(config_dir):
            data_roots = []
            for ini_file in glob.glob(os.path.join(config_dir, "*.ini")):
                try:
                    content = None
                    for enc in ("utf-8", "gbk"):
                        try:
                            with open(ini_file, "r", encoding=enc) as f:
                                content = f.read(1024).strip()
                            break
                        except UnicodeDecodeError:
                            continue
                    if content and os.path.isdir(content):
                        data_roots.append(content)
                except:
                    continue
            
            # 搜索 xwechat_files\*\db_storage
            for root in data_roots:
                pattern = os.path.join(root, "xwechat_files", "*", "db_storage")
                for match in glob.glob(pattern):
                    if os.path.isdir(match):
                        return match
    
    elif system == "linux":
        # Linux: 搜索 ~/Documents/xwechat_files
        home = os.path.expanduser("~")
        pattern = os.path.join(home, "Documents", "xwechat_files", "*", "db_storage")
        matches = glob.glob(pattern)
        if matches:
            # 按修改时间排序，返回最新的
            matches.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            return matches[0]
    
    return None


def extract_keys_from_memory(wechat_process="Weixin.exe"):
    """
    从微信进程内存中提取数据库密钥
    返回: {db_path: {salt_hex, enc_key_hex}}
    """
    system = platform.system().lower()
    
    if system == "windows":
        return _extract_keys_windows(wechat_process)
    elif system == "linux":
        return _extract_keys_linux(wechat_process)
    else:
        raise RuntimeError(f"不支持的平台: {system}")


def _extract_keys_windows(process_name="Weixin.exe"):
    """Windows 版密钥提取"""
    try:
        import pymem
        import psutil
    except ImportError:
        print("[!] 请先安装依赖: pip install pymem psutil")
        return {}
    
    # 查找微信进程
    pids = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and process_name.lower() in proc.info['name'].lower():
                pids.append(proc.info['pid'])
        except:
            pass
    
    if not pids:
        print(f"[!] 未找到微信进程: {process_name}")
        return {}
    
    print(f"[*] 找到微信进程 PID: {pids}")
    
    # 扫描内存查找密钥模式
    all_keys = {}
    key_pattern = b'x\''  # SQLCipher raw key 格式: x'<64hex><32hex>'
    
    for pid in pids:
        try:
            pm = pymem.Pymem(pid)
            
            # 扫描所有可读内存区域
            for m in pm.list_modules():
                try:
                    base = m.lpBaseOfDll
                    size = m.SizeOfImage
                    
                    # 读取内存
                    data = pm.read_bytes(base, size)
                    
                    # 查找密钥模式
                    idx = 0
                    while True:
                        idx = data.find(key_pattern, idx)
                        if idx == -1:
                            break
                        
                        # 提取可能的密钥
                        try:
                            # 格式: x'<64hex_key><32hex_salt>'
                            key_data = data[idx:idx+100]
                            key_str = key_data.decode('ascii', errors='ignore')
                            
                            if key_str.startswith("x'") and len(key_str) >= 98:
                                hex_part = key_str[2:98]  # 64+32=96 hex chars
                                if all(c in '0123456789abcdefABCDEF' for c in hex_part):
                                    enc_key = hex_part[:64]
                                    salt = hex_part[64:96]
                                    
                                    # 尝试关联数据库
                                    db_path = _find_db_for_key(pm, base, idx, data)
                                    if db_path:
                                        all_keys[db_path] = {
                                            "salt": salt,
                                            "enc_key": enc_key
                                        }
                        except:
                            pass
                        
                        idx += 1
                        
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"[!] 扫描进程 {pid} 失败: {e}")
            continue
    
    return all_keys


def _extract_keys_linux(process_name="wechat"):
    """Linux 版密钥提取"""
    import psutil
    
    # 查找微信进程
    pids = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] and process_name.lower() in proc.info['name'].lower():
                pids.append(proc.info['pid'])
        except:
            pass
    
    if not pids:
        print(f"[!] 未找到微信进程: {process_name}")
        return {}
    
    all_keys = {}
    
    for pid in pids:
        try:
            mem_path = f"/proc/{pid}/mem"
            maps_path = f"/proc/{pid}/maps"
            
            # 读取内存映射
            with open(maps_path, 'r') as f:
                maps = f.readlines()
            
            # 扫描可读内存区域
            with open(mem_path, 'rb') as mem:
                for line in maps:
                    parts = line.split()
                    if len(parts) < 2:
                        continue
                    
                    addr_range = parts[0]
                    perms = parts[1]
                    
                    if 'r' not in perms:  # 不可读
                        continue
                    
                    try:
                        start, end = addr_range.split('-')
                        start = int(start, 16)
                        end = int(end, 16)
                        
                        # 读取内存区域
                        mem.seek(start)
                        data = mem.read(end - start)
                        
                        # 查找密钥模式 x'<64hex><32hex>'
                        idx = 0
                        while True:
                            idx = data.find(b"x'", idx)
                            if idx == -1:
                                break
                            
                            try:
                                key_data = data[idx:idx+100]
                                key_str = key_data.decode('ascii', errors='ignore')
                                
                                if key_str.startswith("x'") and len(key_str) >= 98:
                                    hex_part = key_str[2:98]
                                    if all(c in '0123456789abcdefABCDEF' for c in hex_part):
                                        enc_key = hex_part[:64]
                                        salt = hex_part[64:96]
                                        
                                        # 这里简化处理，实际应该关联数据库
                                        all_keys[f"db_{len(all_keys)}"] = {
                                            "salt": salt,
                                            "enc_key": enc_key
                                        }
                            except:
                                pass
                            
                            idx += 1
                            
                    except:
                        continue
                        
        except Exception as e:
            print(f"[!] 扫描进程 {pid} 失败: {e}")
            continue
    
    return all_keys


def _find_db_for_key(pm, base, idx, data):
    """
    尝试在密钥附近找到关联的数据库路径
    这是一个启发式方法
    """
    # 在密钥前后搜索可能的文件路径
    search_start = max(0, idx - 500)
    search_end = min(len(data), idx + 500)
    search_data = data[search_start:search_end]
    
    # 查找 .db 字符串
    db_idx = search_data.find(b'.db')
    if db_idx > 0:
        # 向前查找路径开始
        path_start = db_idx
        while path_start > 0:
            c = search_data[path_start - 1]
            if c in (0, ord('/'), ord('\\')):
                break
            if 32 <= c < 127:  # 可打印字符
                path_start -= 1
            else:
                break
        
        try:
            path = search_data[path_start:db_idx+3].decode('utf-8', errors='ignore')
            if '.db' in path and len(path) > 5:
                return path
        except:
            pass
    
    return None


def save_keys(keys, output_file, db_dir=None):
    """保存密钥到文件"""
    output = {
        "_extracted_at": datetime.now().isoformat(),
        "_db_dir": db_dir,
    }
    output.update(keys)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"[*] 已保存 {len(keys)} 个密钥到: {output_file}")


def main():
    """主函数 - 提取密钥"""
    print("=" * 60)
    print("  微信数据库密钥提取工具")
    print("=" * 60)
    
    # 检测微信数据目录
    db_dir = get_wechat_db_dir()
    if db_dir:
        print(f"[*] 检测到微信数据目录: {db_dir}")
    else:
        print("[!] 未能自动检测微信数据目录")
        db_dir = input("请手动输入微信数据目录 (db_storage): ").strip()
    
    # 提取密钥
    print("[*] 正在从微信进程内存中提取密钥...")
    print("    (需要管理员/root权限)")
    
    keys = extract_keys_from_memory()
    
    if not keys:
        print("[!] 未能提取到任何密钥")
        print("    可能原因:")
        print("    1. 微信未运行")
        print("    2. 权限不足 (请以管理员/root运行)")
        print("    3. 微信版本不兼容")
        return
    
    # 保存密钥
    output_file = "all_keys.json"
    save_keys(keys, output_file, db_dir)
    
    print(f"[*] 成功提取 {len(keys)} 个数据库密钥")
    for db_path in keys:
        print(f"    - {db_path}")


if __name__ == "__main__":
    main()
