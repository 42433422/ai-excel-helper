# -*- coding: utf-8 -*-
"""
购买单位产品导入应用服务

从上传的 SQLite .db 文件导入购买单位及其产品列表：
- 读取源数据库的 products 表
- 确保购买单位存在（创建或复用）
- 产品去重处理
- 批量导入产品到主库
"""

import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional

from app.db.models.customer import Customer
from app.db.models.product import Product
from app.db.session import get_db
from app.utils.external_sqlite import sqlite_conn
from app.utils.path_utils import get_upload_dir

logger = logging.getLogger(__name__)


class UnitProductsImportService:
    """
    购买单位产品导入服务

    负责从外部 SQLite 数据库导入指定购买单位的产品列表。
    """

    def __init__(self):
        self.upload_dir = get_upload_dir()

    def import_unit_products(
        self,
        saved_name: str,
        unit_name: str,
        create_purchase_unit: bool = True,
        skip_duplicates: bool = True
    ) -> Dict[str, Any]:
        """
        从上传的 SQLite .db 导入购买单位产品

        Args:
            saved_name: 保存的文件名
            unit_name: 购买单位名称
            create_purchase_unit: 是否创建不存在的购买单位
            skip_duplicates: 是否跳过重复产品

        Returns:
            导入结果字典
        """
        validation_result = self._validate_params(saved_name, unit_name)
        if validation_result:
            return validation_result

        source_db_path = os.path.join(self.upload_dir, saved_name)
        if not os.path.exists(source_db_path):
            return {"success": False, "message": "源数据库文件不存在"}

        try:
            with sqlite_conn(source_db_path) as conn:
                cur = conn.cursor()

                products_rows = self._read_source_products(cur, unit_name)
                if not products_rows:
                    return {
                        "success": True,
                        "message": "源 products 表无可导入数据",
                        "unit_name": unit_name,
                        "created_unit": False,
                        "imported": 0,
                        "skipped_duplicates": 0,
                        "failed_products": [],
                    }

            created_unit = self._ensure_unit_exists(unit_name, create_purchase_unit)

            if skip_duplicates:
                products_rows, skipped_count = self._deduplicate_products(
                    products_rows, unit_name
                )
            else:
                skipped_count = 0

            if not products_rows:
                return {
                    "success": True,
                    "message": "没有新产品需要导入（仅重复项）",
                    "unit_name": unit_name,
                    "created_unit": created_unit,
                    "imported": 0,
                    "skipped_duplicates": skipped_count,
                    "failed_products": [],
                }

            import_result = self._batch_import_products(products_rows)
            imported = import_result.get("imported", 0)
            failed_products = import_result.get("failed_products", [])

            return {
                "success": True,
                "message": import_result.get("message") or "导入完成",
                "unit_name": unit_name,
                "created_unit": created_unit,
                "imported": imported,
                "skipped_duplicates": skipped_count,
                "failed_products": failed_products,
            }

        except Exception as e:
            logger.exception(f"导入购买单位+产品列表失败：{e}")
            return {"success": False, "message": f"导入失败：{str(e)}"}

    def _validate_params(self, saved_name: str, unit_name: str) -> Optional[Dict[str, Any]]:
        """验证输入参数"""
        if not saved_name:
            return {"success": False, "message": "saved_name 不能为空"}
        if not unit_name:
            return {"success": False, "message": "unit_name 不能为空"}

        if saved_name != os.path.basename(saved_name):
            return {"success": False, "message": "saved_name 不合法（疑似路径穿越）"}
        if "/" in saved_name or "\\" in saved_name:
            return {"success": False, "message": "saved_name 不合法（疑似包含路径分隔符）"}

        return None

    def _read_source_products(
        self,
        cur: sqlite3.Cursor,
        unit_name: str
    ) -> List[Dict[str, Any]]:
        """读取源 products 表"""
        tables = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        table_names = [t[0] for t in tables if t and t[0]]
        products_table = next(
            (t for t in table_names if t and t.lower() == "products"),
            None
        )
        if not products_table:
            return []

        cols = cur.execute(f"PRAGMA table_info('{products_table}')").fetchall()
        col_names = [c[1] for c in cols if c and c[1]]
        col_map = {str(c).lower(): str(c) for c in col_names}

        if "name" not in col_map:
            return []

        expected_cols = [
            "model_number", "name", "specification", "price",
            "quantity", "description", "category", "brand",
            "unit", "is_active", "created_at", "updated_at",
        ]
        select_cols = [col_map[c] for c in expected_cols if c in col_map]
        if not select_cols:
            return []

        quoted_cols = ",".join([f'"{c}"' for c in select_cols])
        rows = cur.execute(f'SELECT {quoted_cols} FROM "{products_table}"').fetchall()
        row_dicts = [dict(zip(select_cols, r)) for r in rows]

        products_rows = []
        for rd in row_dicts:
            rd_lc = {str(k).lower(): v for k, v in rd.items()}
            src_name = (rd_lc.get("name") or "").strip()
            if not src_name:
                continue

            src_model = (rd_lc.get("model_number") or "").strip()
            src_spec = (rd_lc.get("specification") or "").strip()
            src_price = rd_lc.get("price")
            price = self._parse_float(src_price)

            src_qty = rd_lc.get("quantity")
            quantity = self._parse_int(src_qty)

            src_desc = (rd_lc.get("description") or "").strip()
            src_category = (rd_lc.get("category") or "").strip()
            src_brand = (rd_lc.get("brand") or "").strip()
            src_is_active = rd_lc.get("is_active")
            is_active = self._parse_int(src_is_active) if src_is_active is not None else 1

            products_rows.append({
                "product_name": src_name,
                "model_number": src_model or None,
                "specification": src_spec or None,
                "price": price,
                "quantity": quantity,
                "description": src_desc,
                "category": src_category,
                "brand": src_brand,
                "unit": unit_name,
                "is_active": is_active,
            })

        return products_rows

    def _parse_float(self, value: Any) -> float:
        """安全解析浮点数"""
        try:
            return float(value) if value is not None and str(value).strip() != "" else 0.0
        except Exception:
            return 0.0

    def _parse_int(self, value: Any) -> Optional[int]:
        """安全解析整数"""
        try:
            return int(value) if value is not None and str(value).strip() != "" else None
        except Exception:
            return None

    def _ensure_unit_exists(
        self,
        unit_name: str,
        create_purchase_unit: bool
    ) -> bool:
        """确保购买单位存在"""
        from app.bootstrap import get_customer_app_service

        with get_db() as db:
            existing_customer = db.query(Customer).filter(
                Customer.customer_name == unit_name
            ).first()

        if not existing_customer and not create_purchase_unit:
            return False

        if not existing_customer:
            customer_service = get_customer_app_service()
            customer_result = customer_service.create({
                "customer_name": unit_name,
                "contact_person": None,
                "contact_phone": None,
                "contact_address": None,
            })
            if customer_result.get("success") is True:
                return True
            msg = str(customer_result.get("message") or "")
            if "客户名称已存在" not in msg:
                return False

        return True

    def _deduplicate_products(
        self,
        products_rows: List[Dict[str, Any]],
        unit_name: str
    ) -> tuple:
        """产品去重"""
        with get_db() as db:
            existing = db.query(
                Product.model_number, Product.name, Product.specification
            ).filter(Product.unit == unit_name).all()

        existing_keys = set()
        for mnum, pname, spec in existing:
            m = (mnum or "").strip() if mnum is not None else ""
            if m:
                existing_keys.add(("model", m))
            else:
                existing_keys.add(("name_spec", (pname or "").strip(), (spec or "").strip()))

        import_keys = set()
        deduped = []
        skipped = 0

        for item in products_rows:
            m = (item.get("model_number") or "").strip()
            if m:
                key = ("model", m)
            else:
                key = (
                    "name_spec",
                    (item.get("product_name") or "").strip(),
                    (item.get("specification") or "").strip()
                )
            if key in existing_keys or key in import_keys:
                skipped += 1
                continue
            import_keys.add(key)
            deduped.append(item)

        return deduped, skipped

    def _batch_import_products(
        self,
        products_rows: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """批量导入产品"""
        from app.bootstrap import get_products_service

        products_service = get_products_service()
        return products_service.batch_add_products(products_rows)


_unit_products_import_app_service_instance = None


def get_unit_products_import_app_service() -> UnitProductsImportService:
    """获取单位产品导入服务单例"""
    global _unit_products_import_app_service_instance
    if _unit_products_import_app_service_instance is None:
        _unit_products_import_app_service_instance = UnitProductsImportService()
    return _unit_products_import_app_service_instance
