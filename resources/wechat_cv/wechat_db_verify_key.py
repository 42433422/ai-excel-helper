# -*- coding: utf-8 -*-
"""
候选密钥验证：用 SQLCipher 验证从内存提取的 64/96 位 Hex 是否可解密微信数据库。
运行方式：
  python wechat_db_verify_key.py <key_hex> <db_path>
  python wechat_db_verify_key.py   # 打印用法与示例代码

注意：必须使用 pysqlcipher3 或 sqlcipher3，标准库 sqlite3 无法解密 SQLCipher 加密库。
"""
import sys
import os

_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

from wechat_db_read import verify_wechat_db_key


def main():
    if len(sys.argv) < 3:
        print("用法: python wechat_db_verify_key.py <64或96位Hex密钥> <微信数据库路径>")
        print("示例: python wechat_db_verify_key.py a1b2c3... C:\\xwechat_files\\...\\message_0.db")
        print()
        print("--- 方式一：用本模块验证（推荐）---")
        print("""
from wechat_db_read import verify_wechat_db_key
key_hex_64 = "你的候选64位Hex密钥"
db_path = r"微信数据库路径\\message_0.db"
result = verify_wechat_db_key(key_hex_64, db_path)
print("密钥有效，解密成功！" if result["valid"] else result["message"])
""")
        print("--- 方式二：直接用 pysqlcipher3（不可用标准库 sqlite3）---")
        print("""
# 必须用 pysqlcipher3，标准库 sqlite3 无法解密 SQLCipher！
try:
    from pysqlcipher3 import dbapi2 as sqlite3
except ImportError:
    import sqlite3  # 会解密失败，仅作对比

key_hex_64 = "你的候选64位Hex密钥"
db_path = r"微信数据库路径\\Msg.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("PRAGMA key = \\"x'%s'\\";" % key_hex_64)
c.execute("PRAGMA cipher_page_size = 4096")
try:
    c.execute("SELECT count(*) FROM sqlite_master;")
    print("密钥有效，解密成功！")
except sqlite3.OperationalError as e:
    print("密钥无效：", e)
finally:
    conn.close()
""")
        return 0 if len(sys.argv) == 1 else 1

    key_hex = sys.argv[1].strip()
    db_path = sys.argv[2].strip()
    if not os.path.isfile(db_path):
        print("错误：数据库文件不存在:", db_path)
        return 1
    result = verify_wechat_db_key(key_hex, db_path)
    if result["valid"]:
        print("密钥有效，解密成功！")
    else:
        print("密钥无效：", result["message"])
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
