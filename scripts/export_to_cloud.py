# -*- coding: utf-8 -*-
"""
数据导出工具 - 将 SQLite 数据导出为 JSON 格式
用于同步到微信云开发数据库

使用方法：
python scripts/export_to_cloud.py

导出文件位置：./temp_excel/cloud_export/
"""

import json
import os
from datetime import datetime

def export_customers():
    """导出客户/购买单位数据"""
    try:
        from app.db.models.purchase_unit import PurchaseUnit
        from app.db.session import get_customers_session

        session = get_customers_session()
        try:
            units = session.query(PurchaseUnit).filter(PurchaseUnit.is_active == True).all()
            data = []
            for unit in units:
                data.append({
                    "_id": f"customer_{unit.id}",
                    "unit_name": unit.unit_name,
                    "contact_person": unit.contact_person or "",
                    "contact_phone": unit.contact_phone or "",
                    "address": unit.address or "",
                    "is_active": bool(unit.is_active),
                    "created_at": unit.created_at.isoformat() if unit.created_at else None,
                    "updated_at": unit.updated_at.isoformat() if unit.updated_at else None,
                    "_source_id": unit.id
                })
            return data
        finally:
            session.close()
    except Exception as e:
        print(f"导出客户数据失败: {e}")
        return []

def export_products():
    """导出产品数据"""
    try:
        from app.db.models.product import Product
        from app.db.session import get_session

        session = get_session()
        try:
            products = session.query(Product).filter(Product.is_active == 1).all()
            data = []
            for p in products:
                data.append({
                    "_id": f"product_{p.id}",
                    "model_number": p.model_number or "",
                    "name": p.name,
                    "specification": p.specification or "",
                    "price": float(p.price) if p.price else 0.0,
                    "quantity": p.quantity or 0,
                    "description": p.description or "",
                    "category": p.category or "",
                    "brand": p.brand or "",
                    "unit": p.unit or "个",
                    "is_active": bool(p.is_active),
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                    "_source_id": p.id
                })
            return data
        finally:
            session.close()
    except Exception as e:
        print(f"导出产品数据失败: {e}")
        return []

def export_shipments():
    """导出发货记录"""
    try:
        from app.db.models.shipment import ShipmentRecord
        from app.db.session import get_session

        session = get_session()
        try:
            records = session.query(ShipmentRecord).all()
            data = []
            for r in records:
                data.append({
                    "_id": f"shipment_{r.id}",
                    "purchase_unit": r.purchase_unit,
                    "unit_id": r.unit_id,
                    "product_name": r.product_name,
                    "model_number": r.model_number or "",
                    "quantity_kg": float(r.quantity_kg) if r.quantity_kg else 0.0,
                    "quantity_tins": r.quantity_tins or 0,
                    "tin_spec": float(r.tin_spec) if r.tin_spec else 0.0,
                    "unit_price": float(r.unit_price) if r.unit_price else 0.0,
                    "amount": float(r.amount) if r.amount else 0.0,
                    "status": r.status or "pending",
                    "printed_at": r.printed_at.isoformat() if r.printed_at else None,
                    "printer_name": r.printer_name or "",
                    "raw_text": r.raw_text or "",
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                    "_source_id": r.id
                })
            return data
        finally:
            session.close()
    except Exception as e:
        print(f"导出发货记录失败: {e}")
        return []

def export_materials():
    """导出素材/原材料数据"""
    try:
        from app.db.models.material import Material
        from app.db.session import get_session

        session = get_session()
        try:
            materials = session.query(Material).filter(Material.is_active == 1).all()
            data = []
            for m in materials:
                data.append({
                    "_id": f"material_{m.id}",
                    "material_code": m.material_code,
                    "name": m.name,
                    "category": m.category or "",
                    "specification": m.specification or "",
                    "unit": m.unit or "个",
                    "quantity": float(m.quantity) if m.quantity else 0.0,
                    "unit_price": float(m.unit_price) if m.unit_price else 0.0,
                    "supplier": m.supplier or "",
                    "warehouse_location": m.warehouse_location or "",
                    "min_stock": float(m.min_stock) if m.min_stock else 0.0,
                    "max_stock": float(m.max_stock) if m.max_stock else 0.0,
                    "description": m.description or "",
                    "is_active": bool(m.is_active),
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                    "updated_at": m.updated_at.isoformat() if m.updated_at else None,
                    "_source_id": m.id
                })
            return data
        finally:
            session.close()
    except Exception as e:
        print(f"导出素材数据失败: {e}")
        return []

def main():
    """主函数 - 导出所有数据"""
    # 创建导出目录
    export_dir = os.path.join(os.path.dirname(__file__), '..', 'temp_excel', 'cloud_export')
    os.makedirs(export_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    print("=" * 50)
    print("开始导出数据到云数据库格式...")
    print("=" * 50)

    # 导出各项数据
    print("\n[1/4] 导出客户数据...")
    customers = export_customers()
    print(f"  客户数据: {len(customers)} 条")

    print("\n[2/4] 导出产品数据...")
    products = export_products()
    print(f"  产品数据: {len(products)} 条")

    print("\n[3/4] 导出发货记录...")
    shipments = export_shipments()
    print(f"  发货记录: {len(shipments)} 条")

    print("\n[4/4] 导出素材数据...")
    materials = export_materials()
    print(f"  素材数据: {len(materials)} 条")

    # 保存为 JSON 文件
    export_data = {
        "customers": customers,
        "products": products,
        "shipments": shipments,
        "materials": materials,
        "export_time": timestamp,
        "version": "1.0"
    }

    json_file = os.path.join(export_dir, f"cloud_export_{timestamp}.json")
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 50)
    print(f"导出完成！")
    print(f"导出文件: {json_file}")
    print("=" * 50)

    # 分别保存各个集合的 JSON 文件（方便逐个导入）
    for name, data in [("customers", customers), ("products", products),
                        ("shipments", shipments), ("materials", materials)]:
        if data:
            file_path = os.path.join(export_dir, f"{name}_{timestamp}.json")
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"  {name}: {file_path}")

    return export_data

if __name__ == '__main__':
    main()
