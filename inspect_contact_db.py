import sqlite3


def main() -> None:
    db_path = r"E:\FHD\XCAGI\wechat-decrypt\decrypted\contact\contact.db"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    rows = cur.execute("SELECT name, type FROM sqlite_master").fetchall()
    tables = [name for name, typ in rows if typ == "table" and name]
    print("tables_count", len(tables))
    print("tables_first_50", tables[:50])

    # Print candidate contact tables/columns
    candidates = [t for t in tables if t.lower() in {"contact", "contacts"} or str(t).lower().startswith("contact") or str(t).startswith("Contact_")]
    print("candidates", candidates[:10])

    # If we have typical tables, dump first columns
    for t in candidates[:3]:
        cols = [r[1] for r in cur.execute(f"PRAGMA table_info({t})").fetchall()]
        print(t, "columns", cols)
        one = cur.execute(f"SELECT * FROM {t} LIMIT 1").fetchone()
        colnames = [d[0] for d in cur.description] if cur.description else []
        if one is not None:
            print(t, "row_first_keys", colnames[:20])

    conn.close()


if __name__ == "__main__":
    main()

