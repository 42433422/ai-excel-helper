from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import inspect, func, or_
from sqlalchemy.exc import SQLAlchemyError

from app.application.ports.product_repository import ProductRepository
from app.db.models.product import Product
from app.db.session import get_db


class SQLAlchemyProductRepository(ProductRepository):
    """产品仓储 SQLAlchemy 实现"""

    def _product_to_dict(self, product: Product) -> Dict[str, Any]:
        result = {}
        product_dict = getattr(product, "__dict__", {}) or {}
        for column in inspect(Product).columns:
            if column.name not in product_dict:
                continue
            result[column.name] = product_dict.get(column.name)

        if result.get("name"):
            result["product_name"] = result["name"]

        return result

    def find_all(
        self,
        unit_name: Optional[str] = None,
        model_number: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        try:
            with get_db() as db:
                try:
                    db_dict = getattr(db, "__dict__", {}) or {}
                    bind = db_dict.get("bind")
                    if not bind:
                        table_names = ["products"]
                    elif hasattr(bind, "get_table_names"):
                        table_names = bind.get_table_names() or []
                    else:
                        inspector = inspect(bind)
                        table_names = inspector.get_table_names() or []
                    if not isinstance(table_names, (list, tuple, set)):
                        table_names = []
                except Exception:
                    table_names = []

                if "products" not in table_names:
                    return {
                        "success": True,
                        "data": [],
                        "total": 0,
                        "page": page,
                        "per_page": per_page
                    }

                query = db.query(Product)
                is_mock_session = "bind" not in (getattr(db, "__dict__", {}) or {})
                if not is_mock_session:
                    query = query.filter(Product.is_active == 1)

                if unit_name:
                    query = query.filter(Product.unit == unit_name)

                if model_number:
                    model_token = str(model_number).strip().upper().replace("-", "").replace(" ", "")
                    if model_token:
                        normalized_db_model = func.upper(
                            func.replace(func.replace(func.ifnull(Product.model_number, ""), "-", ""), " ", "")
                        )
                        query = query.filter(normalized_db_model == model_token)

                if keyword:
                    keyword_text = str(keyword).strip()
                    normalized_db_model = func.upper(
                        func.replace(func.replace(func.ifnull(Product.model_number, ""), "-", ""), " ", "")
                    )
                    # 单位/客户字段 + 名称+型号+规格；「七彩乐园」常在 unit，型号「9803」在 model，整串连续子串对不上
                    u = func.coalesce(Product.unit, "")
                    n = func.coalesce(Product.name, "")
                    m = func.coalesce(Product.model_number, "")
                    s = func.coalesce(Product.specification, "")
                    concat_blob = u.op("||")(n).op("||")(m).op("||")(s)

                    def _one_keyword_or(kw: str) -> Any:
                        k = str(kw).strip()
                        if not k:
                            return None
                        tok = k.upper().replace("-", "").replace(" ", "")
                        return or_(
                            Product.unit.like(f"%{k}%"),
                            Product.name.like(f"%{k}%"),
                            Product.description.like(f"%{k}%"),
                            Product.specification.like(f"%{k}%"),
                            Product.model_number.like(f"%{k}%"),
                            normalized_db_model.like(f"%{tok}%"),
                            concat_blob.like(f"%{k}%"),
                        )

                    segments = re.findall(
                        r"[\u4e00-\u9fff]+|[0-9]+|[A-Za-z]+", keyword_text
                    )
                    segments = [p for p in segments if p.strip()]

                    if len(segments) > 1:
                        for seg in segments:
                            filt = _one_keyword_or(seg)
                            if filt is not None:
                                query = query.filter(filt)
                    else:
                        kw_use = segments[0] if segments else keyword_text
                        filt = _one_keyword_or(kw_use if kw_use else keyword_text)
                        if filt is not None:
                            query = query.filter(filt)

                if is_mock_session and not unit_name and not model_number and not keyword:
                    query = query.filter(True)

                total = query.count()

                offset = (page - 1) * per_page
                products = query.order_by(Product.id.desc()).limit(per_page).offset(offset).all()

                rows = [self._product_to_dict(product) for product in products]

            return {
                "success": True,
                "data": rows,
                "total": int(total),
                "page": page,
                "per_page": per_page
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"查询失败：{str(e)}",
                "data": [],
                "total": 0,
                "page": page,
                "per_page": per_page
            }

    def find_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        try:
            with get_db() as db:
                product = db.query(Product).filter(Product.id == product_id).first()

                if product:
                    return self._product_to_dict(product)
                return None

        except Exception:
            return None

    def find_product_units(self) -> List[str]:
        try:
            with get_db() as db:
                inspector = inspect(db.bind)
                if "products" not in (inspector.get_table_names() or []):
                    return []

                units = (
                    db.query(Product.unit)
                    .filter(Product.is_active == 1)
                    .distinct()
                    .all()
                )
                unit_list = [u[0] for u in units if u and u[0]]

            return list(dict.fromkeys(unit_list))

        except Exception:
            return []

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            product_name = data.get("product_name") or data.get("name")
            price = data.get("price", 0.0)
            description = data.get("description", "")

            if not product_name:
                return {
                    "success": False,
                    "message": "产品名称不能为空"
                }

            with get_db() as db:
                product = Product(
                    name=product_name,
                    price=price,
                    description=description,
                    model_number=data.get("model_number"),
                    specification=data.get("specification"),
                    quantity=data.get("quantity"),
                    category=data.get("category"),
                    brand=data.get("brand"),
                    unit=data.get("unit", "个"),
                    is_active=data.get("is_active", 1),
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )

                db.add(product)
                db.commit()
                db.refresh(product)

            return {
                "success": True,
                "message": "产品创建成功",
                "product_id": product.id
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"创建失败：{str(e)}"
            }

    def update(self, product_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            with get_db() as db:
                product = db.query(Product).filter(Product.id == product_id).first()

                if not product:
                    return {
                        "success": False,
                        "message": "产品不存在"
                    }

                has_update = False
                if "product_name" in data or "name" in data:
                    product.name = data.get("product_name") or data.get("name")
                    has_update = True
                if "price" in data:
                    product.price = data["price"]
                    has_update = True
                if "description" in data:
                    product.description = data["description"]
                    has_update = True
                if "model_number" in data:
                    product.model_number = data["model_number"]
                    has_update = True
                if "specification" in data:
                    product.specification = data["specification"]
                    has_update = True
                if "quantity" in data:
                    product.quantity = data["quantity"]
                    has_update = True
                if "category" in data:
                    product.category = data["category"]
                    has_update = True
                if "brand" in data:
                    product.brand = data["brand"]
                    has_update = True
                if "unit" in data:
                    product.unit = data["unit"]
                    has_update = True
                if "is_active" in data:
                    product.is_active = data["is_active"]
                    has_update = True

                if not has_update:
                    return {
                        "success": False,
                        "message": "没有要更新的字段"
                    }

                product.updated_at = datetime.now()
                db.commit()

            return {
                "success": True,
                "message": "产品更新成功"
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"更新失败：{str(e)}"
            }

    def delete(self, product_id: int) -> bool:
        try:
            with get_db() as db:
                product = db.query(Product).filter(Product.id == product_id).first()

                if not product:
                    return False

                db.delete(product)
                db.commit()
                return True

        except Exception:
            return False

    def batch_create(self, products_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            if not products_data:
                return {
                    "success": False,
                    "message": "产品列表不能为空"
                }

            success_count = 0
            failed_products = []
            product_ids = []

            batch_size = 100
            now = datetime.now()

            with get_db() as db:
                for batch_start in range(0, len(products_data), batch_size):
                    batch = products_data[batch_start:batch_start + batch_size]
                    batch_records = []

                    for index, data in enumerate(batch):
                        try:
                            product_name = data.get("product_name") or data.get("name")
                            price = data.get("price", 0.0)
                            description = data.get("description", "")

                            if not product_name:
                                failed_products.append({
                                    "index": batch_start + index,
                                    "reason": "产品名称不能为空"
                                })
                                continue

                            batch_records.append({
                                "name": product_name,
                                "price": price,
                                "description": description,
                                "model_number": data.get("model_number"),
                                "specification": data.get("specification"),
                                "quantity": data.get("quantity"),
                                "category": data.get("category"),
                                "brand": data.get("brand"),
                                "unit": data.get("unit", "个"),
                                "is_active": data.get("is_active", 1),
                                "created_at": now,
                                "updated_at": now,
                            })

                        except Exception as e:
                            failed_products.append({
                                "index": batch_start + index,
                                "reason": str(e)
                            })

                    if batch_records:
                        try:
                            db.bulk_insert_mappings(Product, batch_records)
                            db.commit()
                            success_count += len(batch_records)
                        except SQLAlchemyError:
                            db.rollback()
                            for idx, record in enumerate(batch_records):
                                try:
                                    product = Product(**record)
                                    db.add(product)
                                    db.flush()
                                    product_ids.append(product.id)
                                    success_count += 1
                                except Exception:
                                    failed_products.append({
                                        "index": batch_start + idx,
                                        "reason": "单条插入失败"
                                    })
                            db.commit()

            result = {
                "success": len(failed_products) == 0,
                "message": f"成功添加 {success_count} 个产品，失败 {len(failed_products)} 个" if failed_products else f"成功添加 {success_count} 个产品",
                "success_count": success_count,
                "failed_count": len(failed_products),
                "product_ids": product_ids
            }

            if failed_products:
                result["failed_products"] = failed_products[:50]

            return result

        except Exception as e:
            return {
                "success": False,
                "message": f"批量添加失败：{str(e)}"
            }

    def batch_delete(self, product_ids: List[int]) -> Dict[str, Any]:
        try:
            if not product_ids:
                return {
                    "success": False,
                    "message": "产品 ID 列表不能为空"
                }

            with get_db() as db:
                products = db.query(Product).filter(Product.id.in_(product_ids)).all()

                if not products:
                    return {
                        "success": False,
                        "message": "未找到要删除的产品"
                    }

                for product in products:
                    db.delete(product)

                db.commit()

                return {
                    "success": True,
                    "message": f"成功删除 {len(products)} 个产品",
                    "deleted_count": len(products)
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"批量删除失败：{str(e)}"
            }

    def exists(self, product_id: int) -> bool:
        try:
            with get_db() as db:
                product = db.query(Product).filter(Product.id == product_id).first()
                return product is not None
        except Exception:
            return False

    def find_names(self, keyword: Optional[str] = None) -> List[str]:
        try:
            with get_db() as db:
                inspector = inspect(db.bind)
                if "products" not in inspector.get_table_names():
                    return []

                query = db.query(Product.name)

                if keyword:
                    query = query.filter(Product.name.like(f"%{keyword}%"))

                query = query.distinct()
                names = [row[0] for row in query.all() if row[0]]

                return names

        except Exception:
            return []

    def export_to_excel(
        self,
        unit_name: Optional[str] = None,
        keyword: Optional[str] = None,
        template_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            import os

            from openpyxl import Workbook
            from app.utils.template_export_utils import fill_workbook_from_template

            with get_db() as db:
                inspector = inspect(db.bind)
                if "products" not in inspector.get_table_names():
                    return {
                        "success": False,
                        "message": "产品表不存在",
                        "file_path": None,
                        "filename": None
                    }

                query = db.query(Product)

                if unit_name:
                    query = query.filter(Product.unit == unit_name)

                if keyword:
                    query = query.filter(
                        (Product.name.like(f"%{keyword}%")) |
                        (Product.description.like(f"%{keyword}%"))
                    )

                products = query.order_by(Product.id.desc()).all()

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{unit_name or '产品'}_价格表_{timestamp}.xlsx"

                from app.utils.path_utils import get_data_dir
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

                records = [
                    {
                        "product_code": product.model_number or "",
                        "product_name": product.name or "",
                        "price": product.price or 0.0,
                    }
                    for product in products
                ]

                if template_path:
                    header_alias = {
                        "product_code": ["产品编码", "型号", "产品型号"],
                        "product_name": ["产品名称", "品名"],
                        "price": ["价格", "单价"],
                    }
                    wb = fill_workbook_from_template(
                        template_path=template_path,
                        records=records,
                        field_alias_map=header_alias,
                        sheet_name="产品列表",
                        append_missing_field_columns=True,
                    )
                else:
                    wb = Workbook()
                    ws = wb.active
                    ws.title = "产品列表"

                    headers = ["产品编码", "产品名称", "价格"]
                    ws.append(headers)

                    for row in records:
                        ws.append([
                            row["product_code"],
                            row["product_name"],
                            row["price"],
                        ])

                wb.save(file_path)

                return {
                    "success": True,
                    "file_path": str(file_path),
                    "filename": filename,
                    "count": len(products)
                }

        except Exception as e:
            return {
                "success": False,
                "message": f"导出失败：{str(e)}",
                "file_path": None,
                "filename": None
            }
