# -*- coding: utf-8 -*-
import sys
import sqlite3
sys.path.insert(0, r'e:\FHD\XCAGI')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.init_db import get_db_path
from app.db.models.purchase_unit import PurchaseUnit

SOURCE_DB = r'e:\FHD\424\customer_products_final_corrected.db'

customers_engine = create_engine(
    f"sqlite:///{get_db_path('customers.db')}",
    connect_args={"check_same_thread": False},
)
Session = sessionmaker(autocommit=False, autoflush=False, bind=customers_engine)


def fuzzy_match(unit_name, target_name):
    u = unit_name.lower()
    t = target_name.lower()
    return u == t or u in t or t in u


def main():
    conn = sqlite3.connect(SOURCE_DB)
    cursor = conn.cursor()
    cursor.execute('SELECT customer_id, 客户名称, 联系人, 电话, 地址 FROM customers')
    rows = cursor.fetchall()
    conn.close()

    print(f'找到 {len(rows)} 条客户记录')
    updated = 0

    with Session() as session:
        all_units = session.query(PurchaseUnit).all()
        unit_names = {u.unit_name: u for u in all_units}

        for row in rows:
            cid, name, contact, phone, address = row
            if not name:
                continue

            matched_unit = None
            for uname, unit in unit_names.items():
                if fuzzy_match(uname, name):
                    matched_unit = unit
                    break

            if matched_unit:
                if contact:
                    matched_unit.contact_person = contact
                if phone:
                    matched_unit.contact_phone = phone
                if address:
                    matched_unit.address = address
                print(f'更新: {name} -> {matched_unit.unit_name} | 联系人:{contact}, 电话:{phone}, 地址:{address}')
                updated += 1
            else:
                print(f'未匹配到购买单位: {name}')

        session.commit()

    print(f'\n共更新了 {updated} 条购买单位记录')


if __name__ == '__main__':
    main()