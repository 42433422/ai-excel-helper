# -*- coding: utf-8 -*-
"""
从 WeChat.exe / WeChatAppEx.exe 进程内存中扫描并提取 dbkey 候选（64/96 位 Hex），并用 SQLCipher 验证。
需微信已启动；读取进程内存需以管理员身份运行本脚本（否则 ReadProcessMemory 会读不到数据）。

新版本限制：若微信采用盐值动态/加密存储或 dbkey 二次加密（如 AES-128）后存内存，
则内存中可能无明文 64/96 hex，本脚本会扫不到或验证失败，需依赖 wechat-decrypt 等工具更新。
用法: python wechat_db_key_from_memory.py [db_path]
  db_path 可选，用于自动验证候选密钥；不传则只输出候选列表。
  也可设置环境变量 WECHAT_DATA_DIR=C:\\xwechat_files 自动解析 db。
  调试: 设置 WECHAT_KEY_DEBUG=1 可打印扫描过程（区域数、读取字节数等）。
"""
import os
import re
import sys

# 控制台 UTF-8（Windows 下避免中文乱码）
if sys.stdout.encoding and sys.stdout.encoding.upper() != "UTF-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

# Windows API
import ctypes as c
from ctypes import wintypes as w

k32 = c.WinDLL("kernel32", use_last_error=True)
PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
MEM_COMMIT = 0x1000
PAGE_READONLY = 0x02
PAGE_READWRITE = 0x04
PAGE_EXECUTE_READ = 0x20
PAGE_EXECUTE_READWRITE = 0x40
PAGE_READWRITE_V = (PAGE_READONLY, PAGE_READWRITE, PAGE_EXECUTE_READ, PAGE_EXECUTE_READWRITE)

# 64-bit MEMORY_BASIC_INFORMATION (with padding)
class MEMORY_BASIC_INFORMATION(c.Structure):
    _fields_ = [
        ("BaseAddress", c.c_void_p),
        ("AllocationBase", c.c_void_p),
        ("AllocationProtect", w.DWORD),
        ("_align1", w.DWORD),
        ("RegionSize", c.c_size_t),
        ("State", w.DWORD),
        ("Protect", w.DWORD),
        ("Type", w.DWORD),
        ("_align2", w.DWORD),
    ]


def find_wechat_pids():
    """返回微信进程 PID 列表。优先 WeChat.exe，否则全部 WeChatAppEx.exe（新版多进程）。"""
    TH32CS_SNAPPROCESS = 0x02
    INVALID_HANDLE_VALUE = c.c_void_p(-1).value

    class PROCESSENTRY32W(c.Structure):
        _fields_ = [
            ("dwSize", w.DWORD),
            ("cntUsage", w.DWORD),
            ("th32ProcessID", w.DWORD),
            ("th32DefaultHeapID", c.c_void_p),
            ("th32ModuleID", w.DWORD),
            ("cntThreads", w.DWORD),
            ("th32ParentProcessID", w.DWORD),
            ("pcPriClassBase", w.LONG),
            ("dwFlags", w.DWORD),
            ("szExeFile", w.WCHAR * 260),
        ]

    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == INVALID_HANDLE_VALUE or snap is None:
        return []
    wechat_pids = []
    app_pids = []
    try:
        pe = PROCESSENTRY32W()
        pe.dwSize = c.sizeof(PROCESSENTRY32W)
        ok = k32.Process32FirstW(snap, c.byref(pe))
        while ok:
            name = (pe.szExeFile or "").strip()
            if name == "WeChat.exe":
                wechat_pids.append(pe.th32ProcessID)
            elif name == "WeChatAppEx.exe":
                app_pids.append(pe.th32ProcessID)
            ok = k32.Process32NextW(snap, c.byref(pe))
        return wechat_pids if wechat_pids else app_pids
    finally:
        k32.CloseHandle(snap)


def find_wechat_pid():
    """返回第一个微信进程 PID（兼容旧接口）。"""
    pids = find_wechat_pids()
    return pids[0] if pids else None


def scan_process_memory_for_hex_keys(pid, hex_len=64, max_candidates=200, chunk_size=1024 * 1024):
    """
    扫描进程内存，提取长度为 hex_len 的连续十六进制字符串作为候选密钥。
    返回去重后的候选列表，最多 max_candidates 个。
    """
    OpenProcess = k32.OpenProcess
    OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    OpenProcess.restype = w.HANDLE
    h = OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
    if not h or h == c.c_void_p(-1).value:
        return None, "OpenProcess 失败（请尝试以管理员身份运行）"
    if os.environ.get("WECHAT_KEY_DEBUG", "").strip() == "1":
        print("[DEBUG] pid=%s OpenProcess ok, scanning..." % pid)

    VirtualQueryEx = k32.VirtualQueryEx
    VirtualQueryEx.argtypes = [w.HANDLE, c.c_void_p, c.POINTER(MEMORY_BASIC_INFORMATION), c.c_size_t]
    VirtualQueryEx.restype = c.c_size_t

    ReadProcessMemory = k32.ReadProcessMemory
    ReadProcessMemory.argtypes = [w.HANDLE, c.c_void_p, c.c_void_p, c.c_size_t, c.POINTER(c.c_size_t)]
    ReadProcessMemory.restype = w.BOOL

    CloseHandle = k32.CloseHandle

    debug = os.environ.get("WECHAT_KEY_DEBUG", "").strip() == "1"
    mbi = MEMORY_BASIC_INFORMATION()
    seen = set()
    candidates = []
    addr = 0
    ptr_size = 8  # 64-bit
    max_addr = (1 << (8 * ptr_size)) - 1 if ptr_size == 8 else 0x7FFFFFFF
    regions_ok = 0
    bytes_read = 0

    pattern = re.compile(rb"[0-9a-fA-F]{%d}" % hex_len)
    # 部分版本密钥以 UTF-16LE 存放：每字符两字节
    pattern_utf16 = re.compile(rb"(?:[0-9a-fA-F]\x00){%d}" % hex_len) if hex_len else None

    while addr < max_addr and len(candidates) < max_candidates:
        mbi_size = c.sizeof(MEMORY_BASIC_INFORMATION)
        if VirtualQueryEx(h, c.c_void_p(addr), c.byref(mbi), mbi_size) != mbi_size:
            break
        base = mbi.BaseAddress
        if base is None:
            break
        addr = base.value if hasattr(base, "value") else base
        size = mbi.RegionSize
        state = mbi.State
        protect = mbi.Protect
        if state != MEM_COMMIT or protect not in PAGE_READWRITE_V:
            addr += size
            continue
        if size > 100 * 1024 * 1024:
            size = 100 * 1024 * 1024
        offset = 0
        while offset < size:
            to_read = min(chunk_size, size - offset)
            buf = (c.c_char * to_read)()
            read_addr = addr + offset
            nread = c.c_size_t(0)
            if ReadProcessMemory(h, c.c_void_p(read_addr), buf, to_read, c.byref(nread)) and nread.value:
                regions_ok += 1
                bytes_read += nread.value
                data = bytes(buf[: nread.value])
                for m in pattern.finditer(data):
                    key = m.group(0).decode("ascii")
                    if key not in seen:
                        seen.add(key)
                        candidates.append(key)
                        if len(candidates) >= max_candidates:
                            break
                if pattern_utf16 and len(candidates) < max_candidates:
                    for m in pattern_utf16.finditer(data):
                        raw = m.group(0)
                        key = "".join(chr(raw[i]) for i in range(0, len(raw), 2))
                        if len(key) == hex_len and key not in seen:
                            seen.add(key)
                            candidates.append(key)
                            if len(candidates) >= max_candidates:
                                break
            if len(candidates) >= max_candidates:
                break
            offset += to_read
        addr += mbi.RegionSize

    CloseHandle(h)
    if debug:
        print("[DEBUG] pid=%s chunks_read=%s bytes_read=%s candidates=%s" % (pid, regions_ok, bytes_read, len(candidates)))
    return candidates, None


def scan_process_memory_near_signature(pid, signature=b"Msg", before=128, hex_len=64, max_candidates=100):
    """在进程内存中找 signature 出现位置，在其前 before 字节内找 hex_len 位 hex 作为候选。"""
    OpenProcess = k32.OpenProcess
    OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    OpenProcess.restype = w.HANDLE
    h = OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
    if not h or h == c.c_void_p(-1).value:
        return [], "OpenProcess 失败"

    VirtualQueryEx = k32.VirtualQueryEx
    VirtualQueryEx.argtypes = [w.HANDLE, c.c_void_p, c.POINTER(MEMORY_BASIC_INFORMATION), c.c_size_t]
    VirtualQueryEx.restype = c.c_size_t
    ReadProcessMemory = k32.ReadProcessMemory
    ReadProcessMemory.argtypes = [w.HANDLE, c.c_void_p, c.c_void_p, c.c_size_t, c.POINTER(c.c_size_t)]
    ReadProcessMemory.restype = w.BOOL
    CloseHandle = k32.CloseHandle

    mbi = MEMORY_BASIC_INFORMATION()
    seen = set()
    candidates = []
    addr = 0
    chunk = 512 * 1024
    pattern = re.compile(rb"[0-9a-fA-F]{%d}" % hex_len)

    while addr < 0x7FFFFFFF and len(candidates) < max_candidates:
        if VirtualQueryEx(h, c.c_void_p(addr), c.byref(mbi), c.sizeof(MEMORY_BASIC_INFORMATION)) != c.sizeof(MEMORY_BASIC_INFORMATION):
            break
        base = mbi.BaseAddress
        addr = int(getattr(base, "value", base) or 0)
        region_size = int(getattr(mbi.RegionSize, "value", mbi.RegionSize) or 0)
        size = min(region_size, 50 * 1024 * 1024)
        if mbi.State != MEM_COMMIT or mbi.Protect not in PAGE_READWRITE_V:
            addr += mbi.RegionSize
            continue
        offset = 0
        while offset < size and len(candidates) < max_candidates:
            to_read = min(chunk, size - offset)
            buf = (c.c_char * to_read)()
            nread = c.c_size_t(0)
            if not ReadProcessMemory(h, c.c_void_p(addr + offset), buf, to_read, c.byref(nread)) or not nread.value:
                offset += to_read
                continue
            data = bytes(buf[: nread.value])
            idx = data.find(signature)
            while idx >= 0 and len(candidates) < max_candidates:
                start = max(0, idx - before)
                block = data[start : idx + 64]
                for m in pattern.finditer(block):
                    key = m.group(0).decode("ascii")
                    if key not in seen:
                        seen.add(key)
                        candidates.append(key)
                idx = data.find(signature, idx + 1)
            offset += to_read
        addr += region_size
    CloseHandle(h)
    return candidates, None


def extract_and_verify(db_path=None, wechat_data_dir=None):
    """
    从 WeChat 进程提取候选密钥，若提供 db_path 或可解析出 db，则逐个验证直至成功。
    返回 (有效密钥, 错误信息)。有效密钥为 None 时表示未找到。
    """
    from wechat_db_read import (
        verify_wechat_db_key,
        get_wechat_contact_db_path,
        get_wechat_msg_db_paths,
        get_default_wechat_data_dir,
    )

    pids = find_wechat_pids()
    if not pids:
        return None, "未找到 WeChat.exe / WeChatAppEx.exe 进程，请先启动微信"

    all_candidates = []
    for pid in pids:
        candidates_64, err = scan_process_memory_for_hex_keys(pid, hex_len=64, max_candidates=400)
        if not err:
            all_candidates.extend(candidates_64 or [])
            candidates_96, _ = scan_process_memory_for_hex_keys(pid, hex_len=96, max_candidates=200)
            all_candidates.extend(candidates_96 or [])
        near, _ = scan_process_memory_near_signature(pid, signature=b"Msg", before=128, hex_len=64, max_candidates=100)
        all_candidates.extend(near)
        near2, _ = scan_process_memory_near_signature(pid, signature=b"FTSContact", before=200, hex_len=64, max_candidates=100)
        all_candidates.extend(near2)
    candidates = list(dict.fromkeys(all_candidates))

    if not candidates:
        return None, "未在进程内存中扫描到符合 64/96 位 Hex 特征的候选密钥（请以管理员身份运行；若仍为空可尝试 wechat-decrypt 等工具）"

    # 解析 db_path
    test_db = db_path
    if not test_db:
        dir_ = wechat_data_dir or get_default_wechat_data_dir()
        if dir_:
            test_db = get_wechat_contact_db_path(dir_)
            if not test_db:
                paths = get_wechat_msg_db_paths(dir_)
                if paths:
                    test_db = paths[0]

    if not test_db or not os.path.isfile(test_db):
        return candidates[0] if candidates else None, "扫描到 %d 个候选，未提供有效 db 路径无法验证（请传 db_path 或配置 wechat_data_dir）" % len(candidates)

    for key in candidates:
        r = verify_wechat_db_key(key, test_db)
        if r.get("valid"):
            return key, None
    return None, "扫描到 %d 个候选，均无法解密 %s" % (len(candidates), test_db)


def main():
    db_path = (sys.argv[1].strip() if len(sys.argv) > 1 else None) or None
    wechat_data_dir = os.environ.get("WECHAT_DATA_DIR") or None
    if not wechat_data_dir:
        try:
            from wechat_db_read import get_default_wechat_data_dir
            wechat_data_dir = get_default_wechat_data_dir()
        except Exception:
            pass
    if not wechat_data_dir and os.path.isdir(r"C:\xwechat_files"):
        wechat_data_dir = r"C:\xwechat_files"

    key, err = extract_and_verify(db_path=db_path, wechat_data_dir=wechat_data_dir)
    if err:
        print(err)
    if key:
        print("有效密钥(hex):", key[:32] + "..." if len(key) > 32 else key)
        print("可将上述 key 填入 wechat_db_key.json 的 key_hex")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
