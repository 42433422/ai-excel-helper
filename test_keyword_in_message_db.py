import re
import sqlite3


def decode_mc(v):
    if v is None:
        return ""
    if isinstance(v, (bytes, bytearray)):
        return v.decode("utf-8", errors="ignore")
    return str(v)


def main() -> None:
    db_path = r"E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db"
    keyword = "骗子"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    tables = [t[0] for t in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    msg_tables = [t for t in tables if str(t).startswith("Msg_")]
    print("msg_tables", msg_tables[:5], "count", len(msg_tables))

    found = 0
    for t in msg_tables[:10]:
        rows = cur.execute(f"SELECT message_content FROM {t} LIMIT 500").fetchall()
        for (mc,) in rows:
            mc_str = decode_mc(mc)
            if keyword in mc_str:
                found += 1
                m = re.search(r"(wxid_[0-9a-zA-Z]+)\\s*:", mc_str)
                wxid = m.group(1) if m else ""
                print("FOUND_IN_TABLE", t, "wxid", wxid)
                # Print a small snippet around the keyword
                idx = mc_str.find(keyword)
                snippet = mc_str[max(0, idx - 40): idx + len(keyword) + 40]
                print("snippet", snippet)
                if found >= 3:
                    conn.close()
                    return
    conn.close()
    print("done, found", found)


if __name__ == "__main__":
    main()

