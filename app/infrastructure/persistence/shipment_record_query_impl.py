from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import inspect as sa_inspect

from app.application.ports.shipment_record_query import ShipmentRecordQueryPort
from app.db.models import ShipmentRecord
from app.db.session import get_db
from app.infrastructure.lookups import resolve_purchase_unit


class SQLAlchemyShipmentRecordQuery(ShipmentRecordQueryPort):
    """shipment_records 表的只读查询实现（Read side）。"""

    def query_shipments(
        self,
        *,
        unit_name: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> Dict[str, Any]:
        try:
            query_unit = unit_name

            # 兼容：unit 可能是简称/模糊名，统一归一到 customers 的规范名
            if query_unit:
                resolved = resolve_purchase_unit(query_unit)
                if resolved:
                    query_unit = resolved.unit_name

            with get_db() as db:
                inspector = sa_inspect(db.bind)
                if "shipment_records" not in inspector.get_table_names():
                    return {
                        "success": True,
                        "data": [],
                        "total": 0,
                        "page": page,
                        "per_page": per_page,
                    }

                query = db.query(ShipmentRecord)

                if query_unit:
                    query = query.filter(ShipmentRecord.purchase_unit == query_unit)

                if start_date:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    query = query.filter(ShipmentRecord.created_at >= start_dt)

                if end_date:
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(
                        hour=23, minute=59, second=59
                    )
                    query = query.filter(ShipmentRecord.created_at <= end_dt)

                total = query.count()

                offset = (page - 1) * per_page
                records = (
                    query.order_by(ShipmentRecord.created_at.desc(), ShipmentRecord.id.desc())
                    .limit(per_page)
                    .offset(offset)
                    .all()
                )

                rows: List[Dict[str, Any]] = []
                shipment_inspect = sa_inspect(ShipmentRecord)
                for record in records:
                    row_dict: Dict[str, Any] = {}
                    for column in shipment_inspect.columns:
                        row_dict[column.name] = getattr(record, column.name)
                    rows.append(row_dict)

            return {
                "success": True,
                "data": rows,
                "total": int(total),
                "page": page,
                "per_page": per_page,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"查询失败：{str(e)}",
                "data": [],
                "total": 0,
                "page": page,
                "per_page": per_page,
            }

    def search_shipments(self, query: str) -> List[Dict[str, Any]]:
        try:
            query_str = (query or "").strip()
            if not query_str:
                return []

            with get_db() as db:
                inspector = sa_inspect(db.bind)
                if "shipment_records" not in inspector.get_table_names():
                    return []

                records = (
                    db.query(ShipmentRecord)
                    .filter(
                        (ShipmentRecord.purchase_unit.like(f"%{query_str}%"))
                        | (ShipmentRecord.product_name.like(f"%{query_str}%"))
                        | (ShipmentRecord.model_number.like(f"%{query_str}%"))
                    )
                    .order_by(ShipmentRecord.created_at.desc())
                    .limit(50)
                    .all()
                )

                rows: List[Dict[str, Any]] = []
                shipment_inspect = sa_inspect(ShipmentRecord)
                for record in records:
                    row_dict: Dict[str, Any] = {}
                    for column in shipment_inspect.columns:
                        row_dict[column.name] = getattr(record, column.name)
                    rows.append(row_dict)

                return rows
        except Exception:
            return []

    def get_shipment_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        try:
            if order_id is None:
                return None

            order_id_str = str(order_id).strip()
            if not order_id_str:
                return None

            shipment_id = int(order_id_str)

            with get_db() as db:
                inspector = sa_inspect(db.bind)
                if "shipment_records" not in inspector.get_table_names():
                    return None

                record = db.query(ShipmentRecord).filter(ShipmentRecord.id == shipment_id).first()
                if not record:
                    return None

                shipment_inspect = sa_inspect(ShipmentRecord)
                row_dict: Dict[str, Any] = {}
                for column in shipment_inspect.columns:
                    row_dict[column.name] = getattr(record, column.name)
                return row_dict
        except Exception:
            return None

    def get_latest_shipments(self, limit: int) -> List[Dict[str, Any]]:
        try:
            safe_limit = int(limit or 0)
            if safe_limit <= 0:
                return []

            with get_db() as db:
                inspector = sa_inspect(db.bind)
                if "shipment_records" not in inspector.get_table_names():
                    return []

                records = (
                    db.query(ShipmentRecord)
                    .order_by(ShipmentRecord.created_at.desc(), ShipmentRecord.id.desc())
                    .limit(safe_limit)
                    .all()
                )

                shipment_inspect = sa_inspect(ShipmentRecord)
                rows: List[Dict[str, Any]] = []
                for record in records:
                    row_dict: Dict[str, Any] = {}
                    for column in shipment_inspect.columns:
                        row_dict[column.name] = getattr(record, column.name)
                    rows.append(row_dict)

                return rows
        except Exception:
            return []

    def get_shipment_records(
        self,
        unit_name: Optional[str] = None,
        *,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        后台管理接口使用的列表查询：
        - unit_name: 可选，支持 resolve_purchase_unit 归一 + fuzzy fallback。
        - limit: 默认 100（与旧实现一致）。
        """
        try:
            safe_limit = int(limit or 0)
            if safe_limit <= 0:
                safe_limit = 100

            with get_db() as db:
                inspector = sa_inspect(db.bind)
                if "shipment_records" not in inspector.get_table_names():
                    return []

                query = db.query(ShipmentRecord)

                if unit_name:
                    canonical_unit = unit_name
                    try:
                        resolved = resolve_purchase_unit(unit_name)
                        if resolved:
                            canonical_unit = resolved.unit_name
                    except Exception:
                        pass

                    records_exact = (
                        query.filter(ShipmentRecord.purchase_unit == canonical_unit)
                        .order_by(ShipmentRecord.created_at.desc())
                        .limit(safe_limit)
                        .all()
                    )

                    if records_exact:
                        records = records_exact
                    else:
                        # fuzzy fallback：把历史上不一致的 purchase_unit 归一再匹配
                        memo: dict[str, Optional[str]] = {}

                        def norm(val: str) -> Optional[str]:
                            if val in memo:
                                return memo[val]
                            try:
                                r = resolve_purchase_unit(val)
                                memo[val] = r.unit_name if r else None
                            except Exception:
                                memo[val] = None
                            return memo[val]

                        candidates = db.query(ShipmentRecord.purchase_unit).distinct().all()
                        candidate_values: List[str] = []
                        for (v,) in candidates:
                            if not v:
                                continue
                            if norm(v) == canonical_unit:
                                candidate_values.append(v)

                        if candidate_values:
                            records = (
                                query.filter(ShipmentRecord.purchase_unit.in_(candidate_values))
                                .order_by(ShipmentRecord.created_at.desc())
                                .limit(safe_limit)
                                .all()
                            )
                        else:
                            records = []
                else:
                    records = (
                        query.order_by(ShipmentRecord.created_at.desc()).limit(safe_limit).all()
                    )

                shipment_inspect = sa_inspect(ShipmentRecord)
                rows: List[Dict[str, Any]] = []
                for record in records:
                    row_dict: Dict[str, Any] = {}
                    for column in shipment_inspect.columns:
                        row_dict[column.name] = getattr(record, column.name)
                    rows.append(row_dict)

                return rows
        except Exception:
            return []

