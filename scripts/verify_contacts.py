# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'e:\FHD\XCAGI')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.init_db import get_db_path
from app.db.models.purchase_unit import PurchaseUnit

engine = create_engine(
    f"sqlite:///{get_db_path('customers.db')}",
    connect_args={"check_same_thread": False},
)
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

with Session() as session:
    units = session.query(PurchaseUnit).all()
    print(f'购买单位总数: {len(units)}')
    for u in units:
        has_contact = u.contact_person or u.contact_phone or u.address
        status = '✓ 有联系人' if has_contact else '✗ 无联系人'
        print(f'  {u.unit_name}: {u.contact_person or "-"} | {u.contact_phone or "-"} | {u.address or "-"} [{status}]')