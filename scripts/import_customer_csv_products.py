# -*- coding: utf-8 -*-
"""
将「公司名.csv」导入 purchase_units + products：
- 文件名（不含 .csv）= 购买单位 unit_name
- 列：编号, 产品名称, 规格 (kg), 调价后单价 (元 /kg)
- 编号为 — / 空 时，型号用「产品名_规格」避免同名单价不同冲突

用法:
  python scripts/import_customer_csv_products.py
  python scripts/import_customer_csv_products.py --dry-run
  python scripts/import_customer_csv_products.py path/to/a.csv path/to/b.csv
  # 先删该客户下全部产品再按 CSV 重导（修正与历史 Word 导入的型号不一致重复）
  python scripts/import_customer_csv_products.py --replace "E:\\FHD\\424\\深圳市百木鼎家具有限公司.csv"
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

_NO_CODE_CHARS = frozenset({"—", "-", "－", "–", "\u2014", ""})


def _resolve_db_path() -> Path:
    env = os.environ.get("FHD_PRODUCTS_DB", "").strip()
    if env:
        p = Path(env).expanduser()
        if p.is_file():
            return p.resolve()
    for d in (REPO / "XCAGI", REPO / "xcagi"):
        cand = d / "products.db"
        if cand.is_file():
            return cand.resolve()
    raise FileNotFoundError("未找到 products.db，请设置 FHD_PRODUCTS_DB")


def _norm_model(code: str, name: str, spec: str) -> str:
    c = (code or "").strip()
    if c and c not in _NO_CODE_CHARS:
        return c[:120]
    base = f"{(name or '').strip()}_{(spec or '').strip()}".strip("_")
    return re.sub(r"\s+", "", base)[:120] or "UNKNOWN"


def _spec_display(spec: str) -> str:
    s = (spec or "").strip()
    if re.fullmatch(r"[\d.]+", s):
        return f"{s}KG"
    return s


def _parse_price(s: str) -> float:
    t = (s or "").strip().replace(",", "")
    if not t:
        return 0.0
    try:
        return float(t)
    except ValueError:
        return 0.0


def _ensure_purchase_unit(cur: sqlite3.Cursor, customer: str) -> None:
    cur.execute(
        "SELECT id FROM purchase_units WHERE unit_name = ? AND (is_active IS NULL OR is_active = 1)",
        (customer,),
    )
    if cur.fetchone():
        return
    cur.execute("PRAGMA table_info(purchase_units)")
    cols = {str(r[1]) for r in cur.fetchall()}
    fields = ["unit_name", "contact_person", "contact_phone", "address", "is_active"]
    vals: list = [customer, "", "", "", 1]
    now = datetime.utcnow().isoformat(timespec="seconds")
    if "created_at" in cols:
        fields.append("created_at")
        vals.append(now)
    if "updated_at" in cols:
        fields.append("updated_at")
        vals.append(now)
    ph = ",".join(["?"] * len(vals))
    cur.execute(
        f"INSERT INTO purchase_units ({', '.join(fields)}) VALUES ({ph})",
        vals,
    )


def _import_one_csv(
    conn: sqlite3.Connection, csv_path: Path, dry_run: bool, replace: bool
) -> tuple[int, int, int, int]:
    customer = csv_path.stem.strip()
    if not customer:
        raise ValueError(f"无效文件名: {csv_path}")

    inserted = 0
    skipped = 0
    deleted = 0
    errors = 0
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(products)")
    pcols = {str(r[1]) for r in cur.fetchall()}
    if not {"model_number", "name"}.issubset(pcols):
        raise RuntimeError("products 表缺少 model_number / name")

    if not dry_run:
        _ensure_purchase_unit(cur, customer)

    if replace and not dry_run:
        cur.execute(
            "DELETE FROM products WHERE TRIM(unit) = ?",
            (customer,),
        )
        deleted = cur.rowcount or 0

    text = csv_path.read_text(encoding="utf-8-sig")
    reader = csv.reader(text.splitlines())
    header = next(reader, None)
    if not header:
        return 0, 0, 0, deleted

    for row in reader:
        if not row or len(row) < 4:
            continue
        code, name, spec, price_s = row[0], row[1], row[2], row[3]
        name = (name or "").strip()
        if not name or name == "产品名称":
            continue
        spec = (spec or "").strip()
        model = _norm_model(code, name, spec)
        spec_disp = _spec_display(spec)
        price = _parse_price(price_s)
        cur.execute(
            """
            SELECT id FROM products
            WHERE model_number = ? AND TRIM(unit) = ?
              AND (is_active IS NULL OR is_active = 1)
            LIMIT 1
            """,
            (model, customer),
        )
        if cur.fetchone():
            skipped += 1
            continue
        if dry_run:
            inserted += 1
            continue
        cols = ["model_number", "name"]
        vals: list = [model, name]
        if "specification" in pcols:
            cols.append("specification")
            vals.append(spec_disp)
        if "price" in pcols:
            cols.append("price")
            vals.append(price)
        if "unit" in pcols:
            cols.append("unit")
            vals.append(customer)
        if "quantity" in pcols:
            cols.append("quantity")
            vals.append(0)
        if "description" in pcols:
            cols.append("description")
            vals.append("")
        if "category" in pcols:
            cols.append("category")
            vals.append("")
        if "brand" in pcols:
            cols.append("brand")
            vals.append("")
        if "is_active" in pcols:
            cols.append("is_active")
            vals.append(1)
        ph = ",".join(["?"] * len(vals))
        try:
            cur.execute(
                f"INSERT INTO products ({', '.join(cols)}) VALUES ({ph})",
                vals,
            )
            inserted += 1
        except sqlite3.Error:
            errors += 1

    return inserted, skipped, errors, deleted


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_files", nargs="*", type=Path, help="CSV 路径，默认 424 下三家")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--replace",
        action="store_true",
        help="导入前删除该 CSV 对应购买单位下的全部产品行（用于去掉旧 Word 导入的重复型号）",
    )
    args = ap.parse_args()

    default_names = (
        "惠州市枫驰家具有限公司.csv",
        "惠州市鸿瑞达家具有限公司.csv",
        "深圳市百木鼎家具有限公司.csv",
    )
    if args.csv_files:
        paths = [p.resolve() for p in args.csv_files]
    else:
        paths = [(REPO / "424" / n).resolve() for n in default_names]
    for p in paths:
        if not p.is_file():
            print("文件不存在:", p, file=sys.stderr)
            return 1

    db_path = _resolve_db_path()
    print("DB:", db_path)
    print("dry_run:", args.dry_run)

    conn = sqlite3.connect(str(db_path))
    try:
        for p in paths:
            ins, sk, err, deleted = _import_one_csv(conn, p, args.dry_run, args.replace)
            extra = f" deleted_before={deleted}" if deleted else ""
            print(f"{p.name}: inserted={ins} skipped={sk} errors={err}{extra}")
        if not args.dry_run:
            conn.commit()
    finally:
        conn.close()

    print("完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
