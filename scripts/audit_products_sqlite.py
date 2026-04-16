# -*- coding: utf-8 -*-
"""Audit SQLite products.db: schema, counts, duplicates, orphan units, FK-like issues."""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Audit products.db (SQLite)")
    ap.add_argument(
        "--db",
        type=Path,
        default=None,
        help="Path to products.db (default: XCAGI/products.db under repo root)",
    )
    args = ap.parse_args()
    repo = Path(__file__).resolve().parents[1]
    db = args.db or (repo / "XCAGI" / "products.db")
    if not db.is_file():
        print("File not found:", db, file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    tables = [
        r[0]
        for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
    ]
    print("== Database ==\n", db.resolve())
    print("\n== Tables & row counts ==")
    for t in tables:
        n = cur.execute(f'SELECT COUNT(*) AS n FROM "{t}"').fetchone()["n"]
        print(f"  {t}: {n}")

    if "products" not in tables:
        print("\n(no products table)")
        conn.close()
        return 0

    print("\n== products columns ==")
    for r in cur.execute("PRAGMA table_info(products)").fetchall():
        print(f"  {r['cid']}\t{r['name']}\t{r['type']}\tnotnull={r['notnull']}")

    if "purchase_units" in tables:
        print("\n== purchase_units columns ==")
        for r in cur.execute("PRAGMA table_info(purchase_units)").fetchall():
            print(f"  {r['cid']}\t{r['name']}\t{r['type']}")

    print("\n== Active products: duplicate model_number ==")
    cur.execute(
        """
        SELECT model_number, COUNT(*) AS n
        FROM products
        WHERE (is_active IS NULL OR is_active = 1)
        GROUP BY model_number
        HAVING n > 1
        ORDER BY n DESC
        LIMIT 25
        """
    )
    dups = cur.fetchall()
    print(f"  duplicate groups: {len(dups)}")
    for r in dups[:15]:
        print(f"    {r['model_number']!r}\tcount={r['n']}")

    print("\n== Active products: empty model_number ==")
    cur.execute(
        """
        SELECT COUNT(*) AS n FROM products
        WHERE (is_active IS NULL OR is_active = 1)
          AND (model_number IS NULL OR TRIM(model_number) = '')
        """
    )
    print("  rows:", cur.fetchone()["n"])

    print("\n== Active products: empty name ==")
    cur.execute(
        """
        SELECT COUNT(*) AS n FROM products
        WHERE (is_active IS NULL OR is_active = 1)
          AND (name IS NULL OR TRIM(name) = '')
        """
    )
    print("  rows:", cur.fetchone()["n"])

    if "purchase_units" in tables and "unit" in [
        r["name"] for r in cur.execute("PRAGMA table_info(products)").fetchall()
    ]:
        print("\n== product.unit values NOT in purchase_units.unit_name (active) ==")
        cur.execute(
            """
            SELECT DISTINCT TRIM(p.unit) AS u
            FROM products p
            WHERE p.unit IS NOT NULL AND TRIM(p.unit) != ''
              AND (p.is_active IS NULL OR p.is_active = 1)
            """
        )
        prod_units = {r["u"] for r in cur.fetchall()}
        cur.execute(
            """
            SELECT DISTINCT TRIM(unit_name) AS u FROM purchase_units
            WHERE (is_active IS NULL OR is_active = 1)
            """
        )
        pu = {r["u"] for r in cur.fetchall()}
        orphan = sorted(prod_units - pu)
        print(f"  count: {len(orphan)}")
        for u in orphan[:40]:
            cur.execute(
                """
                SELECT COUNT(*) AS n FROM products
                WHERE TRIM(unit) = ? AND (is_active IS NULL OR is_active = 1)
                """,
                (u,),
            )
            n = cur.fetchone()["n"]
            print(f"    {u}\t({n} products)")

    if "purchase_units" in tables:
        print("\n== purchase_units: duplicate unit_name (active) ==")
        cur.execute(
            """
            SELECT unit_name, COUNT(*) AS n FROM purchase_units
            WHERE (is_active IS NULL OR is_active = 1)
            GROUP BY unit_name HAVING n > 1
            """
        )
        for r in cur.fetchall():
            print(f"    {r['unit_name']!r}\tcount={r['n']}")

    print("\n== inactive products ==")
    if "is_active" in [r["name"] for r in cur.execute("PRAGMA table_info(products)").fetchall()]:
        cur.execute("SELECT COUNT(*) AS n FROM products WHERE is_active = 0")
        print("  is_active=0:", cur.fetchone()["n"])

    conn.close()
    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
