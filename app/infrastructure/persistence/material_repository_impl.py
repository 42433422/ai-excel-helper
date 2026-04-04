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

    def export_to_excel(
        self,
        search: Optional[str] = None,
        category: Optional[str] = None,
        template_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            import os

            from openpyxl import Workbook

            from app.utils.path_utils import get_data_dir
            from app.utils.template_export_utils import fill_workbook_from_template

            with get_db() as db:
                query = db.query(Material).filter(Material.is_active == 1)
                if search:
                    pattern = f"%{search}%"
                    query = query.filter(
                        (Material.name.like(pattern))
                        | (Material.material_code.like(pattern))
                        | (Material.supplier.like(pattern))
                    )
                if category:
                    query = query.filter(Material.category == category)

                materials = query.order_by(Material.id.desc()).all()

            records = [
                {
                    "material_code": m.material_code or "",
                    "name": m.name or "",
                    "category": m.category or "",
                    "specification": m.specification or "",
                    "unit": m.unit or "",
                    "stock_quantity": m.quantity if m.quantity is not None else 0,
                    "unit_price": m.unit_price if m.unit_price is not None else 0,
                    "supplier": m.supplier or "",
                }
                for m in materials
            ]

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"materials_{timestamp}.xlsx"
            export_dir = os.path.join(get_data_dir(), "exports")
            os.makedirs(export_dir, exist_ok=True)
            file_path = os.path.join(export_dir, filename)

            template_path = None
            if template_id:
                try:
                    from app.application import get_template_app_service

                    templates = (get_template_app_service().get_templates() or {}).get("templates") or []
                    target = next((t for t in templates if str(t.get("id")) == str(template_id)), None)
                    if target:
                        candidate_path = str(target.get("path") or target.get("file_path") or "").strip()
                        if candidate_path and os.path.exists(candidate_path):
                            template_path = candidate_path
                except Exception:
                    template_path = None

            if template_path:
                header_alias = {
                    "material_code": ["原材料编码", "编码"],
                    "name": ["名称", "原材料名称"],
                    "category": ["分类"],
                    "specification": ["规格", "规格型号"],
                    "unit": ["单位"],
                    "stock_quantity": ["库存数量", "数量"],
                    "unit_price": ["单价", "价格"],
                    "supplier": ["供应商"],
                }
                wb = fill_workbook_from_template(
                    template_path=template_path,
                    records=records,
                    field_alias_map=header_alias,
                    sheet_name="原材料列表",
                )
            else:
                wb = Workbook()
                ws = wb.active
                ws.title = "原材料列表"
                ws.append(["原材料编码", "名称", "分类", "规格", "单位", "库存数量", "单价", "供应商"])
                for row in records:
                    ws.append(
                        [
                            row["material_code"],
                            row["name"],
                            row["category"],
                            row["specification"],
                            row["unit"],
                            row["stock_quantity"],
                            row["unit_price"],
                            row["supplier"],
                        ]
                    )

            wb.save(file_path)
            return {
                "success": True,
                "file_path": str(file_path),
                "filename": filename,
                "count": len(records),
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"导出失败：{str(e)}",
                "file_path": None,
                "filename": None,
                "count": 0,
            }
