# -*- coding: utf-8 -*-
"""
读微信本地数据库：支持「已解密」的 SQLite 或「用本地配置文件中的 key 解开加密库」。
微信 PC 4.x+ 使用 SQLCipher 加密，dbkey 为 64 位 Hex，在微信启动后存在于 WeChat.exe 进程内存中；
获取思路：定位 WeChat.exe → 扫描进程内存中符合 dbkey 特征区域 → 解析出 64 位 Hex 并写入配置。
本模块不负责从内存提取 key，仅从 wechat_db_key.json 读取 key_hex 后解密。配置示例：
  wechat_cv/wechat_db_key.json  {"key_hex": "64位十六进制密钥"}
"""
import os
import sqlite3
import json

_here = os.path.dirname(os.path.abspath(__file__))
DEFAULT_KEY_CONFIG = os.path.join(_here, "wechat_db_key.json")


def load_key_from_config(config_path=None):
    """
    从本地配置文件读取密钥。返回 key_hex 或 None。
    配置文件格式（JSON）: {"key_hex": "80或96位hex"} 或 {"key": "同上"}
    """
    path = config_path or DEFAULT_KEY_CONFIG
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        key = (data.get("key_hex") or data.get("key") or "").strip()
        if not key:
            return None
        key = key.replace(" ", "").replace("x'", "").replace("'", "")
        if len(key) >= 64 and all(c in "0123456789abcdefABCDEF" for c in key):
            return key
        return None
    except Exception:
        return None


def get_default_wechat_data_dir(config_path=None):
    """
    从配置文件读取默认微信数据目录（如 C:\\xwechat_files），未配置则返回 None。
    配置格式：wechat_db_key.json 中增加 "wechat_data_dir": "C:\\\\xwechat_files"
    """
    path = config_path or DEFAULT_KEY_CONFIG
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        dir_path = (data.get("wechat_data_dir") or data.get("wechat_data_path") or "").strip()
        if dir_path and os.path.isdir(dir_path):
            return dir_path
    except Exception:
        pass
    return None


def _connect_encrypted(db_path: str, key_hex: str):
    """
    用 key_hex（十六进制字符串）打开 SQLCipher 加密的 db。
    微信内存中格式多为 64 位加密钥 + 32 位盐 = 96 位 hex，整体作为 PRAGMA key。
    返回 connection 或 None，调用方负责 close。
    """
    try:
        import sqlcipher3
        conn = sqlcipher3.connect(db_path)
    except ImportError:
        try:
            from pysqlcipher3 import dbapi2 as sqlcipher3
            conn = sqlcipher3.connect(db_path)
        except ImportError:
            return None
    try:
        # SQLCipher: PRAGMA key = "x'<hex>'"
        key_hex = key_hex.replace(" ", "").strip()
        conn.execute("PRAGMA key = \"x'%s'\"" % key_hex)
        conn.execute("PRAGMA cipher_page_size = 4096")
        conn.execute("SELECT count(*) FROM sqlite_master")
        return conn
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        return None


def verify_wechat_db_key(key_hex: str, db_path: str):
    """
    用候选 64/96 位 Hex 密钥验证是否可解密指定微信数据库。
    必须使用 sqlcipher3 或 pysqlcipher3（标准库 sqlite3 无法解密 SQLCipher 库）。
    返回 {"valid": True/False, "message": "..."}。
    """
    if not key_hex or not db_path or not os.path.isfile(db_path):
        return {"valid": False, "message": "key_hex 或 db_path 无效"}
    key_hex = key_hex.replace(" ", "").replace("x'", "").replace("'", "").strip()
    if len(key_hex) < 64 or not all(c in "0123456789abcdefABCDEF" for c in key_hex):
        return {"valid": False, "message": "key_hex 需为 64 或 96 位十六进制"}
    conn = _connect_encrypted(db_path, key_hex)
    if not conn:
        return {"valid": False, "message": "密钥无效或无法打开（请安装 sqlcipher3 或 pysqlcipher3: pip install sqlcipher3）"}
    try:
        conn.execute("SELECT count(*) FROM sqlite_master")
        conn.close()
        return {"valid": True, "message": "密钥有效，解密成功"}
    except Exception as e:
        try:
            conn.close()
        except Exception:
            pass
        return {"valid": False, "message": str(e)}


def query_encrypted_db(db_path: str, sql: str, params=None, key_hex=None, config_path=None):
    """
    用配置文件中的 key 或传入的 key_hex 解开加密库并执行 SQL。
    若 key 无效或未配置，返回 success=False；否则与 query_decrypted_db 格式一致。
    """
    if not os.path.isfile(db_path):
        return {"success": False, "message": f"文件不存在: {db_path}", "rows": []}
    key = key_hex or load_key_from_config(config_path)
    if not key:
        return {"success": False, "message": "未配置密钥，请在 wechat_db_key.json 中填写 key_hex（可从 wechat-decrypt 等工具提取后写入）", "rows": []}
    conn = _connect_encrypted(db_path, key)
    if not conn:
        return {"success": False, "message": "无法用密钥打开（pip install sqlcipher3，且 key_hex 格式正确）", "rows": []}
    try:
        cur = conn.cursor()
        cur.execute(sql, params or [])
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        conn.close()
        return {"success": True, "rows": rows, "count": len(rows)}
    except Exception as e:
        try:
            conn.close()
        except Exception:
            pass
        return {"success": False, "message": str(e), "rows": []}


def query_decrypted_or_encrypted(db_path: str, sql: str, params=None, key_hex=None, config_path=None):
    """
    先尝试当普通 SQLite 打开；若失败且配置了 key，再用 key 解密的方式打开。
    """
    out = query_decrypted_db(db_path, sql, params)
    if out.get("success"):
        return out
    if "encrypted" in (out.get("message") or "").lower() or "file is not a database" in (out.get("message") or "").lower():
        return query_encrypted_db(db_path, sql, params, key_hex=key_hex, config_path=config_path)
    return out


def get_wechat_data_dirs():
    """常见微信数据目录（不一定存在或可读）。"""
    dirs = []
    docs = os.path.join(os.environ.get("USERPROFILE", ""), "Documents", "WeChat Files")
    if docs:
        dirs.append(docs)
    try:
        if os.path.isdir(docs):
            for name in os.listdir(docs):
                p = os.path.join(docs, name)
                if os.path.isdir(p) and not name.startswith("All Users"):
                    dirs.append(p)
    except Exception:
        pass
    return dirs


def list_db_files(wechat_data_dir=None):
    """列出目录下的 .db 文件。若未传则用第一个找到的 WeChat Files 子目录。"""
    if wechat_data_dir and os.path.isdir(wechat_data_dir):
        root = wechat_data_dir
    else:
        dirs = get_wechat_data_dirs()
        root = dirs[0] if dirs else None
    if not root:
        return []
    out = []
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            if f.endswith(".db"):
                out.append(os.path.join(dirpath, f))
    return out[:100]


def query_decrypted_db(db_path: str, sql: str, params=None):
    """
    对「已解密」的 SQLite 文件执行一条 SQL，返回 list[dict]。
    若文件仍为 SQLCipher 加密，会报错或乱码，需先用解密工具处理。
    """
    if not os.path.isfile(db_path):
        return {"success": False, "message": f"文件不存在: {db_path}", "rows": []}
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(sql, params or [])
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return {"success": True, "rows": rows, "count": len(rows)}
    except sqlite3.OperationalError as e:
        if "encrypted" in str(e).lower() or "file is not a database" in str(e).lower():
            return {"success": False, "message": "该 db 可能仍为加密状态，请先用解密工具处理", "rows": []}
        return {"success": False, "message": str(e), "rows": []}
    except Exception as e:
        return {"success": False, "message": str(e), "rows": []}


def get_tables(db_path: str, key_hex=None, config_path=None):
    """列出 SQLite 中的表名；若为加密库且配置了 key，会先解密再查。"""
    return query_decrypted_or_encrypted(
        db_path, "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
        key_hex=key_hex, config_path=config_path
    )


def get_recent_messages(db_path: str, limit: int = 50, table_name: str = "MSG", key_hex=None, config_path=None):
    """
    从聊天库中读取最近消息；若为加密库且配置了 key，会先解密再查。
    表名因版本可能为 MSG 或类似，若表结构不同请先用 get_tables 查看后自行写 SQL。
    """
    try:
        r = query_decrypted_or_encrypted(
            db_path,
            f"SELECT * FROM [{table_name}] ORDER BY createTime DESC LIMIT ?",
            [limit], key_hex=key_hex, config_path=config_path,
        )
        return r
    except Exception:
        return query_decrypted_or_encrypted(
            db_path, f"SELECT * FROM [{table_name}] LIMIT ?", [limit],
            key_hex=key_hex, config_path=config_path,
        )


# ---------- 用本地 DB 替代 OCR：联系人名 + 对方消息 ----------
# 微信 PC 常见：Msg/MSG0.db、MSG1.db 为消息库（表 MSG：talker, isSend, content, createTime）；
# MicroMsg.db 为联系人等（表 Contact：UserName, NickName, Remark）。
# 新版目录（如 C:\xwechat_files）：wxid_xxx_xxx/db_storage/contact/contact.db、db_storage/message/message_0.db。

def _get_wechat_user_root(wechat_data_dir=None):
    """
    返回「当前账号」的 DB 根目录：若根下已有 MicroMsg.db 或 Msg，则返回根；
    否则返回第一个子目录 wxid_*_* 且其下存在 db_storage 的路径。
    wechat_data_dir 未传时先读配置文件中的 wechat_data_dir，再回退到 get_wechat_data_dirs()。
    """
    root = wechat_data_dir
    if not root or not os.path.isdir(root):
        root = get_default_wechat_data_dir()
    if not root or not os.path.isdir(root):
        dirs = get_wechat_data_dirs()
        root = dirs[0] if dirs else None
    if not root:
        return None
    if os.path.isfile(os.path.join(root, "MicroMsg.db")) or os.path.isdir(os.path.join(root, "Msg")):
        return root
    try:
        for name in os.listdir(root):
            if name.startswith("wxid_") and os.path.isdir(os.path.join(root, name)):
                sub = os.path.join(root, name)
                if os.path.isdir(os.path.join(sub, "db_storage")):
                    return sub
    except Exception:
        pass
    return None


def get_wechat_msg_db_paths(wechat_data_dir=None):
    """返回消息库路径列表：优先 Msg/MSG*.db，否则 db_storage/message/message_*.db。"""
    user_root = _get_wechat_user_root(wechat_data_dir)
    if not user_root:
        return []
    msg_dir = os.path.join(user_root, "Msg")
    if os.path.isdir(msg_dir):
        out = [os.path.join(msg_dir, f) for f in os.listdir(msg_dir)
               if f.endswith(".db") and "MSG" in f.upper()]
        if out:
            return sorted(out)
    msg_dir2 = os.path.join(user_root, "db_storage", "message")
    if os.path.isdir(msg_dir2):
        out = [os.path.join(msg_dir2, f) for f in os.listdir(msg_dir2)
               if f.endswith(".db") and "message" in f.lower() and "fts" not in f.lower() and "resource" not in f.lower()]
        if out:
            return sorted(out)
    return []


def get_wechat_contact_db_path(wechat_data_dir=None):
    """返回联系人库路径：优先 MicroMsg.db（根或 Msg 下），否则 db_storage/contact/contact.db。"""
    user_root = _get_wechat_user_root(wechat_data_dir)
    if not user_root:
        return None
    for p in (os.path.join(user_root, "MicroMsg.db"), os.path.join(user_root, "Msg", "MicroMsg.db")):
        if os.path.isfile(p):
            return p
    p = os.path.join(user_root, "db_storage", "contact", "contact.db")
    return p if os.path.isfile(p) else None


def get_contact_list_from_db(contact_db_path=None, wechat_data_dir=None, key_hex=None, config_path=None):
    """
    从本地库读取联系人列表。返回 { "success", "rows": [ {"userName","nickName","remark"}, ... ], "message" }。
    表/字段按常见：Contact 表，UserName / NickName / Remark；若无则尝试其它常见名。
    """
    path = contact_db_path or get_wechat_contact_db_path(wechat_data_dir)
    if not path or not os.path.isfile(path):
        return {"success": False, "message": "未找到 MicroMsg.db 或路径无效", "rows": []}
    for table in ("Contact", "Contacts"):
        for sql in (
            f'SELECT UserName as userName, NickName as nickName, Remark as remark FROM [{table}] WHERE UserName IS NOT NULL AND UserName != ""',
            f'SELECT userName, nickName, remark FROM [{table}] WHERE userName IS NOT NULL AND userName != ""',
        ):
            r = query_decrypted_or_encrypted(path, sql, key_hex=key_hex, config_path=config_path)
            if r.get("success") and r.get("rows"):
                return r
    return {"success": False, "message": "未找到 Contact/Contacts 表或字段", "rows": []}


def get_contact_display_name(contact_db_path, talker, key_hex=None, config_path=None):
    """
    根据 talker（微信 id / userName）查显示名：优先 Remark，否则 NickName。
    返回字符串或 None。
    """
    if not contact_db_path or not os.path.isfile(contact_db_path) or not talker:
        return None
    for table in ("Contact", "Contacts"):
        for sql in (
            f'SELECT Remark, NickName FROM [{table}] WHERE UserName = ?',
            f'SELECT remark, nickName FROM [{table}] WHERE userName = ?',
        ):
            r = query_decrypted_or_encrypted(contact_db_path, sql, [talker], key_hex=key_hex, config_path=config_path)
            if r.get("success") and r.get("rows"):
                row = r["rows"][0]
                remark = (row.get("Remark") or row.get("remark") or "").strip()
                nick = (row.get("NickName") or row.get("nickName") or "").strip()
                return remark or nick or talker
    return talker


def get_messages_for_contact(msg_db_path, talker, limit=50, only_other=True, key_hex=None, config_path=None):
    """
    从消息库查与某联系人的聊天记录。only_other=True 时只返回对方消息（isSend=0）。
    返回格式与 get_current_chat_messages 一致：{"success", "rows": [{"role":"other"/"self","text":"..."}], "message"}。
    """
    if not msg_db_path or not os.path.isfile(msg_db_path) or not talker:
        return {"success": False, "message": "msg_db_path 或 talker 无效", "rows": []}
    where = "talker = ?"
    if only_other:
        where += " AND isSend = 0"
    for table in ("MSG", "Message"):
        sql = f"SELECT content, isSend, createTime FROM [{table}] WHERE {where} ORDER BY createTime DESC LIMIT ?"
        r = query_decrypted_or_encrypted(msg_db_path, sql, [talker, limit], key_hex=key_hex, config_path=config_path)
        if r.get("success"):
            rows = []
            for row in (r.get("rows") or []):
                content = (row.get("content") or "").strip()
                if not content:
                    continue
                role = "other" if (row.get("isSend") == 0) else "self"
                rows.append({"role": role, "text": content})
            return {"success": True, "rows": rows, "count": len(rows)}
        # 可能表名或字段不同，尝试下一张表
    return {"success": False, "message": "未找到 MSG/Message 表或 talker 无记录", "rows": []}


def get_contact_and_messages_from_db(
    contact_identifier,
    wechat_data_dir=None,
    msg_db_path=None,
    contact_db_path=None,
    limit=50,
    only_other=True,
    key_hex=None,
    config_path=None,
):
    """
    用本地 DB 替代 OCR：根据联系人标识（微信 id 或备注/昵称）返回「联系人名 + 对方消息」。
    返回格式与 wechat_cv 的完整流程一致：{"contact_name": "...", "messages": [{"role":"other","text":"..."}, ...], "success", "message"}。
    """
    contact_path = contact_db_path or get_wechat_contact_db_path(wechat_data_dir)
    msg_paths = [msg_db_path] if msg_db_path and os.path.isfile(msg_db_path) else get_wechat_msg_db_paths(wechat_data_dir)
    if not contact_path and not msg_paths:
        return {"success": False, "message": "未找到微信数据目录或 MicroMsg.db / Msg 库", "contact_name": "", "messages": []}

    # 解析 contact_identifier -> talker (userName)
    talker = None
    if contact_path:
        cl = get_contact_list_from_db(contact_path, key_hex=key_hex, config_path=config_path)
        if cl.get("success") and cl.get("rows"):
            ident_lower = (contact_identifier or "").strip().lower()
            for row in cl["rows"]:
                u = (row.get("userName") or "").strip()
                n = (row.get("nickName") or "").strip()
                r = (row.get("remark") or "").strip()
                if ident_lower in (u.lower(), n.lower(), r.lower()):
                    talker = u
                    break
            if not talker and ident_lower:
                for row in cl["rows"]:
                    u = (row.get("userName") or "").strip()
                    if u and ident_lower in u.lower():
                        talker = u
                        break
    if not talker:
        talker = contact_identifier.strip()

    contact_name = get_contact_display_name(contact_path, talker, key_hex=key_hex, config_path=config_path) if contact_path else talker

    messages = []
    for mp in msg_paths:
        out = get_messages_for_contact(mp, talker, limit=limit, only_other=only_other, key_hex=key_hex, config_path=config_path)
        if out.get("success") and out.get("rows"):
            messages = out["rows"]
            break
    if not messages and msg_paths:
        out = get_messages_for_contact(msg_paths[0], talker, limit=limit, only_other=False, key_hex=key_hex, config_path=config_path)
        if out.get("success") and out.get("rows"):
            messages = out["rows"]

    return {"success": True, "contact_name": contact_name or talker, "messages": messages, "talker": talker}


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python wechat_db_read.py <.db路径> [SQL]")
        print("  或: python wechat_db_read.py list   # 列出常见目录下的 .db 文件")
        print("  若 db 为加密且已配置 wechat_db_key.json，会自动用 key 解密后执行 SQL。")
        sys.exit(0)
    if sys.argv[1].lower() == "list":
        dirs = get_wechat_data_dirs()
        print("WeChat 数据目录:", dirs)
        for d in dirs:
            if os.path.isdir(d):
                for p in list_db_files(d)[:20]:
                    print(" ", p)
        sys.exit(0)
    db_path = sys.argv[1]
    sql = sys.argv[2] if len(sys.argv) > 2 else "SELECT name FROM sqlite_master WHERE type='table'"
    out = query_decrypted_or_encrypted(db_path, sql)
    print(json.dumps(out, ensure_ascii=False, indent=2))
