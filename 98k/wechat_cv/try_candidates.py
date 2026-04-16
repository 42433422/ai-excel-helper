# -*- coding: utf-8 -*-
"""
读取 wechat-decrypt 导出的 hex_candidates.json，逐个用 SQLCipher 试解指定 db。
用法: python try_candidates.py [hex_candidates.json] [db_path]
  不传则默认: wechat-decrypt/hex_candidates.json, db_dir 下全部 .db

若所有候选均无法解密：可能是新版本微信对盐值/dbkey 做了加固（动态盐、加密存储或 dbkey 二次加密），
内存中的候选并非明文密钥，需关注 wechat-decrypt 等项目的更新。
"""
import os
import sys
import json

_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

from wechat_db_read import verify_wechat_db_key, get_wechat_contact_db_path, get_wechat_msg_db_paths, get_default_wechat_data_dir

# 从 db 文件第一页读 salt（前 16 字节 hex = 32 字符）
def _read_salt_hex(db_path):
    try:
        with open(db_path, "rb") as f:
            page1 = f.read(4096)
        if len(page1) >= 16:
            return page1[:16].hex()
    except Exception:
        pass
    return None


def main():
    candidates_file = sys.argv[1] if len(sys.argv) > 1 else None
    db_path = sys.argv[2] if len(sys.argv) > 2 else None

    if not candidates_file or not os.path.isfile(candidates_file):
        default_candidates = os.path.join(os.path.dirname(_here), "wechat-decrypt", "hex_candidates.json")
        if os.path.isfile(default_candidates):
            candidates_file = default_candidates
        else:
            print("用法: python try_candidates.py [hex_candidates.json] [db_path]")
            print("  或先将 wechat-decrypt 运行一次（0/17 时会生成 hex_candidates.json）")
            return 1

    with open(candidates_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    candidates = data.get("candidates") or []
    if not candidates:
        print("hex_candidates.json 中无候选")
        return 1

    db_dir = data.get("db_dir") or ""
    db_list = []
    if db_dir and os.path.isdir(db_dir):
        for root, _, files in os.walk(db_dir):
            for f in files:
                if f.endswith(".db") and not f.endswith("-wal") and not f.endswith("-shm"):
                    db_list.append(os.path.join(root, f))
    if not db_path or not os.path.isfile(db_path):
        db_path = db_list[0] if db_list else None
    if not db_path:
        dir_ = get_default_wechat_data_dir() or ""
        if not dir_ and os.path.isdir(r"C:\xwechat_files"):
            dir_ = r"C:\xwechat_files"
        if dir_:
            db_path = get_wechat_contact_db_path(dir_)
            if not db_path:
                paths = get_wechat_msg_db_paths(dir_)
                db_path = paths[0] if paths else None
    if not db_list and db_path and os.path.isfile(db_path):
        db_list = [db_path]
    if not db_list:
        print("未找到 db 文件，请传 db_path 或配置 wechat_data_dir")
        return 1
    if db_path not in db_list:
        db_list.insert(0, db_path)
    print(f"候选数: {len(candidates)}, 测试 db: {db_list}")

    for i, key_hex in enumerate(candidates):
        key_hex = (key_hex or "").strip().replace(" ", "")
        if len(key_hex) < 64:
            continue
        to_try = []
        if len(key_hex) >= 64:
            to_try.append((key_hex[:64], "64"))
        if len(key_hex) >= 96:
            to_try.append((key_hex[:96], "96"))
        for k, label in to_try:
            for d in db_list:
                if not os.path.isfile(d):
                    continue
                r = verify_wechat_db_key(k, d)
                if r.get("valid"):
                    print(f"\n[OK] 第 {i+1} 个候选有效 (key_len={len(k)}): {k[:32]}...")
                    print(f"  对 db: {d}")
                    print("请将该 key 填入 wechat_db_key.json 的 key_hex")
                    return 0
    # 再试：每个候选前 64 位 + 各 db 的 salt 组成 96 位
    for i, key_hex in enumerate(candidates):
        key_hex = (key_hex or "").strip().replace(" ", "")
        if len(key_hex) < 64:
            continue
        enc64 = key_hex[:64]
        for d in db_list:
            if not os.path.isfile(d):
                continue
            salt = _read_salt_hex(d)
            if not salt or len(salt) != 32:
                continue
            k96 = enc64 + salt
            r = verify_wechat_db_key(k96, d)
            if r.get("valid"):
                print(f"\n[OK] 第 {i+1} 个候选(64位)+db_salt 有效: enc={enc64[:24]}... salt={salt[:16]}...")
                print(f"  对 db: {d}")
                print("请将 enc_key+salt(96位) 填入 wechat_db_key.json 的 key_hex")
                return 0
    print(f"\n共尝试 {len(candidates)} 个候选（64/96 位及 64+各db_salt），均无法解密。")
    print("可能原因：1) 请以管理员运行 wechat-decrypt 再提取；2) 新版本微信盐值/dbkey 已加固（见 wechat_db_read.md）。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
