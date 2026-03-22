# -*- coding: utf-8 -*-
"""
Database Query Skill Module
"""

from contextlib import contextmanager

from app.application.customer_app_service import get_customers_session
from app.db import SessionLocal
from app.db.models import Material, Product, PurchaseUnit, ShipmentRecord


@contextmanager
def get_customers_db():
    session = get_customers_session()
    try:
        yield session
    finally:
        session.close()


def query_all_products(limit=20):
    with get_db() as db:
        return db.query(Product).limit(limit).all()


def search_products(keyword):
    with get_db() as db:
        return db.query(Product).filter(
            Product.name.like(f'%{keyword}%')
        ).limit(20).all()


def search_products_by_model(model_number):
    with get_db() as db:
        return db.query(Product).filter(
            Product.model_number.like(f'%{model_number}%')
        ).limit(20).all()


def query_all_customers(limit=20):
    with get_customers_db() as db:
        return db.query(PurchaseUnit).filter(PurchaseUnit.is_active == True).limit(limit).all()


def search_customers(keyword):
    with get_customers_db() as db:
        return db.query(PurchaseUnit).filter(
            PurchaseUnit.unit_name.like(f'%{keyword}%'),
            PurchaseUnit.is_active == True
        ).limit(20).all()


def query_recent_shipments(days=7, limit=20):
    from datetime import datetime, timedelta
    with get_db() as db:
        start_date = datetime.now() - timedelta(days=days)
        return db.query(ShipmentRecord).filter(
            ShipmentRecord.created_at >= start_date
        ).order_by(ShipmentRecord.created_at.desc()).limit(limit).all()


def query_product_price(product_name):
    with get_db() as db:
        product = db.query(Product).filter(
            Product.name.like(f'%{product_name}%')
        ).first()
        return product.price if product else None


def query_all_materials(limit=20):
    with get_db() as db:
        return db.query(Material).limit(limit).all()


def search_materials(keyword):
    with get_db() as db:
        return db.query(Material).filter(
            Material.name.like(f'%{keyword}%')
        ).limit(20).all()


def get_db_query_skill():
    return {
        'name': 'db-query',
        'functions': {
            'query_all_products': query_all_products,
            'search_products': search_products,
            'search_products_by_model': search_products_by_model,
            'query_all_customers': query_all_customers,
            'search_customers': search_customers,
            'query_recent_shipments': query_recent_shipments,
            'query_product_price': query_product_price,
            'query_all_materials': query_all_materials,
            'search_materials': search_materials,
        }
    }