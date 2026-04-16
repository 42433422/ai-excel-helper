# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'e:\FHD\XCAGI')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.init_db import get_db_path
from app.db.models.purchase_unit import PurchaseUnit

customers_engine = create_engine(
    f"sqlite:///{get_db_path('customers.db')}",
    connect_args={"check_same_thread": False},
)
Products_engine = create_engine(
    f"sqlite:///{get_db_path('products.db')}",
    connect_args={"check_same_thread": False},
)
ProductsSession = sessionmaker(autocommit=False, autoflush=False, bind=Products_engine)
CustomersSession = sessionmaker(autocommit=False, autoflush=False, bind=customers_engine)

print('=== 验证购买单位 ===')
with CustomersSession() as session:
    units = session.query(PurchaseUnit).all()
    print(f'购买单位总数: {len(units)}')
    for u in units:
        print(f'  - {u.unit_name} (id={u.id})')

print('\n=== 验证产品 ===')
with ProductsSession() as session:
    from app.db.models.product import Product
    products = session.query(Product).all()
    print(f'产品总数: {len(products)}')

    unit_counts = {}
    for p in products:
        u = p.unit or '未设置'
        unit_counts[u] = unit_counts.get(u, 0) + 1

    print('各购买单位产品数量:')
    for u, c in sorted(unit_counts.items()):
        print(f'  {u}: {c}')