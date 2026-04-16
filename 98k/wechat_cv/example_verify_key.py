# -*- coding: utf-8 -*-
"""
SQLCipher 密钥验证示例。
重要：必须使用 pysqlcipher3，标准库 sqlite3 无法解密微信的 SQLCipher 数据库！

安装: pip install pysqlcipher3
"""
# 使用 pysqlcipher3 的 sqlite3 兼容接口（不是标准库的 sqlite3）
try:
    from pysqlcipher3 import dbapi2 as sqlite3
    print("使用 pysqlcipher3")
except ImportError:
    import sqlite3
    print("警告：未安装 pysqlcipher3，标准库 sqlite3 无法解密 SQLCipher，验证会失败。请执行: pip install pysqlcipher3")

# 假设提取的 64 位 Hex 密钥为 key_hex_64
key_hex_64 = "你的候选64位Hex密钥"
db_path = r"微信数据库路径\Msg.db"   # 或 message_0.db、contact.db 等

conn = sqlite3.connect(db_path)
c = conn.cursor()
# SQLCipher 密钥格式：x'密钥Hex'，需用双引号包裹
c.execute('PRAGMA key = "x\'%s\'";' % key_hex_64)
c.execute("PRAGMA cipher_page_size = 4096")
try:
    c.execute("SELECT count(*) FROM sqlite_master;")
    print("密钥有效，解密成功！")
except sqlite3.OperationalError as e:
    print("密钥无效：", e)
finally:
    conn.close()
