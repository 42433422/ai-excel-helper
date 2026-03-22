from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.application.ports.material_repository import MaterialRepository
from app.db.models.material import Material
from app.db.session import get_db


class SQLAlchemyMaterialRepository(MaterialRepository):
    """原材料仓储 SQLAlchemy 实现"""

    def _material_to_dict(self, material: Material) -> Dict[str, Any]:
        return {
            "id": material.id,
            "material_code": material.material_code,
            "name": material.name,
            "category": material.category,
            "specification": material.specification,
            "unit": material.unit,
            "quantity": material.quantity,
            "unit_price": material.unit_price,
            "supplier": material.supplier,
            "warehouse_location": material.warehouse_location,
            "min_stock": material.min_stock,
            "max_stock": material.max_stock,
            "description": material.description,
            "is_active": material.is_active,
            "created_at": material.created_at.isoformat() if material.created_at else None,
            "updated_at": material.updated_at.isoformat() if material.updated_at else None
        }

    def find_all(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        try:
            with get_db() as db:
                query = db.query(Material).filter(Material.is_active == 1)

                if search:
                    pattern = f"%{search}%"
                    query = query.filter(
                        (Material.name.like(pattern)) |
                        (Material.material_code.like(pattern)) |
                        (Material.supplier.like(pattern))
                    )

                if category:
                    query = query.filter(Material.category == category)

                total = query.count()
                materials = query.order_by(Material.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

                return {
                    "success": True,
                    "data": [self._material_to_dict(m) for m in materials],
                    "total": total,
                    "page": page,
                    "per_page": per_page
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"获取失败：{str(e)}",
                "data": [],
                "total": 0
            }

    def find_by_id(self, material_id: int) -> Optional[Dict[str, Any]]:
        try:
            with get_db() as db:
                material = db.query(Material).filter(
                    Material.id == material_id,
                    Material.is_active == 1
                ).first()

                if not material:
                    return None

                return self._material_to_dict(material)

        except Exception:
            return None

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            with get_db() as db:
                material = Material(
                    material_code=data.get("material_code"),
                    name=data.get("name"),
                    category=data.get("category"),
                    specification=data.get("specification"),
                    unit=data.get("unit", "个"),
                    quantity=data.get("quantity", 0),
                    unit_price=data.get("unit_price", 0),
                    supplier=data.get("supplier"),
                    warehouse_location=data.get("warehouse_location"),
                    min_stock=data.get("min_stock", 0),
                    max_stock=data.get("max_stock", 0),
                    description=data.get("description"),
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )

                db.add(material)
                db.commit()
                db.refresh(material)

                return {
                    "success": True,
                    "message": "原材料创建成功",
                    "data": self._material_to_dict(material)
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"创建失败：{str(e)}"
            }

    def update(self, material_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            with get_db() as db:
                material = db.query(Material).filter(
                    Material.id == material_id,
                    Material.is_active == 1
                ).first()

                if not material:
                    return {
                        "success": False,
                        "message": "原材料不存在"
                    }

                allowed_fields = [
                    'material_code', 'name', 'category', 'specification',
                    'unit', 'quantity', 'unit_price', 'supplier',
                    'warehouse_location', 'min_stock', 'max_stock',
                    'description'
                ]

                for field, value in data.items():
                    if field in allowed_fields:
                        setattr(material, field, value)

                material.updated_at = datetime.now()

                db.commit()
                db.refresh(material)

                return {
                    "success": True,
                    "message": "原材料更新成功",
                    "data": self._material_to_dict(material)
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"更新失败：{str(e)}"
            }

    def delete(self, material_id: int) -> bool:
        try:
            with get_db() as db:
                material = db.query(Material).filter(
                    Material.id == material_id,
                    Material.is_active == 1
                ).first()

                if not material:
                    return False

                material.is_active = 0
                material.updated_at = datetime.now()
                db.commit()
                return True

        except Exception:
            return False

    def batch_delete(self, ids: List[int]) -> int:
        try:
            with get_db() as db:
                materials = db.query(Material).filter(
                    Material.id.in_(ids),
                    Material.is_active == 1
                ).all()

                deleted_count = 0
                for material in materials:
                    material.is_active = 0
                    material.updated_at = datetime.now()
                    deleted_count += 1

                db.commit()
                return deleted_count

        except Exception:
            return 0

    def find_low_stock(self, threshold: Optional[float] = None) -> List[Dict[str, Any]]:
        try:
            with get_db() as db:
                query = db.query(Material).filter(Material.is_active == 1)

                if threshold is not None:
                    query = query.filter(Material.quantity <= threshold)
                else:
                    query = query.filter(Material.quantity <= Material.min_stock)

                materials = query.order_by(Material.quantity.asc()).all()
                return [self._material_to_dict(m) for m in materials]

        except Exception:
            return []
