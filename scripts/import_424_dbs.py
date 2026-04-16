# -*- coding: utf-8 -*-
"""
从 e:\FHD\424\ 目录下的多个 .db 文件批量导入购买单位和产品数据

每个 .db 文件名代表一个购买单位，文件内的 products 表存储该单位的产品。
"""
import os
import sys
import sqlite3
from datetime import datetime

sys.path.insert(0, r'e:\FHD\XCAGI')

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from app.db.init_db import get_db_path
from app.db.models.product import Product

CUSTOMERS_ENGINE = create_engine(
    f"sqlite:///{get_db_path('customers.db')}",
    connect_args={"check_same_thread": False},
)
CustomersSession = sessionmaker(autocommit=False, autoflush=False, bind=CUSTOMERS_ENGINE)

PRODUCTS_ENGINE = create_engine(
    f"sqlite:///{get_db_path('products.db')}",
    connect_args={"check_same_thread": False},
)
ProductsSession = sessionmaker(autocommit=False, autoflush=False, bind=PRODUCTS_ENGINE)


DB_DIR = r'e:\FHD\424'

DB_FILES = [
    '半岛风情.db',
    '半岛风情外.db',
    '奔奔熊鞋柜.db',
    '博旺家私.db',
    '陈鑫强.db',
    '杜克旗.db',
    '国邦_钟志勇.db',
    '侯雪梅.db',
    '杰妮熊.db',
    '金汉武_宾驰_.db',
    '金汉武.db',
    '金汉武鼎丰_国邦.db',
    '金汉武三江源.db',
    '澜宇.db',
    '名品_晶美鑫_.db',
    '七彩乐园.db',
    '蕊芯家私.db',
    '蕊芯家私1.db',
    '温总.db',
    '小火洋.db',
    '鑫顺.db',
    '宜榢.db',
    '迎扬电视墙.db',
    '志泓家私.db',
    '中江博郡家私.db',
    '宗南家私.db',
]


def normalize_unit_name(filename):
    name = filename.replace('.db', '').strip()
    return name


def ensure_purchase_unit(session, unit_name):
    from app.db.models.purchase_unit import PurchaseUnit
    existing = session.query(PurchaseUnit).filter(PurchaseUnit.unit_name == unit_name).first()
    if existing:
        return existing
    new_unit = PurchaseUnit(
        unit_name=unit_name,
        contact_person='',
        contact_phone='',
        address='',
        is_active=True,
    )
    session.add(new_unit)
    session.commit()
    session.refresh(new_unit)
    print(f'  [新建购买单位] {unit_name}')
    return new_unit


def read_products_from_db(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [t[0] for t in cursor.fetchall()]
    if 'products' not in tables:
        conn.close()
        return []
    cursor.execute('PRAGMA table_info(products)')
    columns = [c[1] for c in cursor.fetchall()]
    cursor.execute('SELECT * FROM products WHERE is_active = 1 OR is_active IS NULL')
    rows = cursor.fetchall()
    conn.close()
    return columns, rows


def add_products_to_main_db(session, unit_name, columns, rows):
    if not rows:
        return 0
    col_map = {c: i for i, c in enumerate(columns)}
    added = 0
    for row in rows:
        try:
            model_number = row[col_map['model_number']] if 'model_number' in col_map else None
            name = row[col_map['name']] if 'name' in col_map else None
            specification = row[col_map['specification']] if 'specification' in col_map else None
            price = row[col_map['price']] if 'price' in col_map else 0.0
            quantity = row[col_map['quantity']] if 'quantity' in col_map else 0
            description = row[col_map['description']] if 'description' in col_map else ''
            category = row[col_map['category']] if 'category' in col_map else None
            brand = row[col_map['brand']] if 'brand' in col_map else None
            unit = row[col_map['unit']] if 'unit' in col_map else unit_name
            is_active = row[col_map['is_active']] if 'is_active' in col_map else 1
            created_at = row[col_map['created_at']] if 'created_at' in col_map else None
            updated_at = row[col_map['updated_at']] if 'updated_at' in col_map else None

            if not name:
                continue

            if unit in (None, '', '个'):
                unit = unit_name

            product = Product(
                model_number=model_number,
                name=name,
                specification=specification,
                price=price or 0.0,
                quantity=quantity or 0,
                description=description or '',
                category=category,
                brand=brand,
                unit=unit,
                is_active=is_active if is_active is not None else 1,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            session.add(product)
            added += 1
        except Exception as e:
            print(f'    [跳过产品] 错误: {e}')
    session.commit()
    return added


def main():
    total_units = 0
    total_products = 0
    skipped_units = 0

    for db_file in DB_FILES:
        db_path = os.path.join(DB_DIR, db_file)
        if not os.path.exists(db_path):
            print(f'[跳过] 文件不存在: {db_path}')
            skipped_units += 1
            continue

        unit_name = normalize_unit_name(db_file)
        print(f'\n处理: {db_file}')
        print(f'  购买单位: {unit_name}')

        columns, rows = read_products_from_db(db_path)
        if not columns:
            print(f'  [跳过] 无 products 表')
            skipped_units += 1
            continue

        print(f'  产品数量: {len(rows)}')

        with CustomersSession() as cust_session:
            ensure_purchase_unit(cust_session, unit_name)

        with ProductsSession() as prod_session:
            added = add_products_to_main_db(prod_session, unit_name, columns, rows)
            print(f'  成功导入产品: {added}')
            total_products += added
            total_units += 1

    print(f'\n========== 导入完成 ==========')
    print(f'处理购买单位: {total_units}')
    print(f'导入产品总数: {total_products}')
    print(f'跳过: {skipped_units}')


if __name__ == '__main__':
    main()