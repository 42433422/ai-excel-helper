
# -*- coding: utf-8 -*-
"""
即使工具显示「0 salts matched」，也可手动验证找到的 Hex 候选是否有效。
必须使用 sqlcipher3 或 pysqlcipher3（标准库 sqlite3 无法解密 SQLCipher）。
安装：Windows 推荐 pip install sqlcipher3；或 pip install pysqlcipher3。

用法一（推荐）：不传参，自动从 hex_candidates.json 和 db_dir 读取
  python verify_candidates_manual.py

用法二：指定候选和 db 路径
  python verify_candidates_manual.py "hex_candidates.json的路径" "某个.db的路径"

用法三：在下方修改 DB_PATH 和 CANDIDATE_KEYS 后直接运行。
"""
import os
import sys
import json

# 可选：直接在这里填写路径与候选（64 位或 96 位 Hex）
DB_PATH = r"C:\xwechat_files\wxid_bommxleja9kq22_22c5\db_storage\message\message_0.db"
CANDIDATE_KEYS = [
    "3a69d5992604cc7bd548bfb33af459cc38099406a82ca11d50cd3d9c9ce84b8b6ed535882ff8cc321b9c718b8464e088",
    "cd3f950326b8f3bfcc04b908aa2090cbddf89e1db806ee415124ba99a50c0649bb78d2cfa0327b95bd950ced05efaaef",
    "7fd0688f7647880faf7237bebd3a98d03372284207dacbb1c76f65210af960d41de1aad2dcb8505b0e61fe4718bafdde",
]

_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

from wechat_db_read import verify_wechat_db_key


def verify_dbkey(db_path, key_hex):
    """验证单个候选密钥。必须用 pysqlcipher3，不能用标准库 sqlite3。"""
    key_hex = (key_hex or "").strip().replace(" ", "")
    if len(key_hex) < 64:
        print(f"[X] 跳过（过短）: {key_hex[:24]}...")
        return False
    if len(key_hex) > 96:
        key_hex = key_hex[:96]
    r = verify_wechat_db_key(key_hex, db_path)
    if r.get("valid"):
        print(f"[OK] 有效密钥: {key_hex[:32]}... (len={len(key_hex)})")
        return True
    print(f"[X] 无效密钥 {key_hex[:24]}...: {(r.get('message') or '')[:60]}")
    return False


def main():
    candidates_file = (sys.argv[1] if len(sys.argv) > 1 else None) or ""
    db_path = (sys.argv[2] if len(sys.argv) > 2 else None) or ""

    if not db_path or not os.path.isfile(db_path):
        db_path = DB_PATH
    if not os.path.isfile(db_path):
        # 从 hex_candidates.json 取 db_dir 下第一个 db
        default_json = os.path.join(os.path.dirname(_here), "wechat-decrypt", "hex_candidates.json")
        json_path = candidates_file or default_json
        if os.path.isfile(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            db_dir = data.get("db_dir") or ""
            if db_dir and os.path.isdir(db_dir):
                db_path = ""
                for root, _, files in os.walk(db_dir):
                    for f in files:
                        if f.endswith(".db") and not f.endswith("-wal") and not f.endswith("-shm"):
                            db_path = os.path.join(root, f)
                            break
                    if db_path:
                        break
        if not db_path or not os.path.isfile(db_path):
            print("请设置 DB_PATH 或传入 db_path 参数。")
            return 1

    if candidates_file and os.path.isfile(candidates_file):
        with open(candidates_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        keys = data.get("candidates") or []
    else:
        keys = CANDIDATE_KEYS

    if not keys:
        print("无候选密钥，请设置 CANDIDATE_KEYS 或传入 hex_candidates.json。")
        return 1

    print(f"DB: {db_path}")
    print(f"候选数: {len(keys)}\n")
    for i, key in enumerate(keys):
        if verify_dbkey(db_path, key):
            print("\n请将上述有效 key 填入 wechat_db_key.json 的 key_hex。")
            return 0
    print("\n所有候选均无效。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
