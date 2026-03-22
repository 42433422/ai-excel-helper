import sqlite3


def main() -> None:
    db_path = r"E:\FHD\XCAGI\resources\wechat-decrypt\decrypted\message\message_0.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    rows = cur.execute("SELECT name, type FROM sqlite_master").fetchall()
    tables = [name for name, typ in rows if typ == "table" and name]

    print("tables_count", len(tables))
    print("tables_first_50", tables[:50])

    # Typical WeChat variants: either "MSG"/"Message", or many "Msg_<hash>" tables.
    msg_tables = [t for t in tables if t == "MSG" or t == "Message" or t.startswith("Msg_")]
    print("msg_tables_count", len(msg_tables))
    print("msg_tables_first_10", msg_tables[:10])

    for candidate in msg_tables[:3]:
        cols = [r[1] for r in cur.execute(f"PRAGMA table_info({candidate})").fetchall()]
        print(f"{candidate}_columns", cols)
        one = cur.execute(f"SELECT * FROM {candidate} LIMIT 1").fetchone()
        colnames = [d[0] for d in cur.description] if cur.description else []
        print(f"{candidate}_row_first", dict(zip(colnames, one)) if one else None)


if __name__ == "__main__":
    main()

