from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import inspect as sa_inspect

from app.application.ports.shipment_record_command import ShipmentRecordCommandPort
from app.db.models import ShipmentRecord
from app.db.session import get_db
from app.infrastructure.lookups import resolve_purchase_unit


class SQLAlchemyShipmentRecordCommand(ShipmentRecordCommandPort):
    """shipment_records 的写操作实现（Command side）。"""

    def clear_all(self) -> Dict[str, Any]:
        try:
            with get_db() as db:
                inspector = sa_inspect(db.bind)
                if "shipment_records" not in inspector.get_table_names():
                    return {"success": False, "message": "数据库表不存在"}

                count = db.query(ShipmentRecord).count()
                db.query(ShipmentRecord).delete()
                db.commit()

            return {
                "success": True,
                "message": f"已清空所有订单，共 {count} 条记录",
            }
        except Exception as e:
            return {"success": False, "message": f"清空失败：{str(e)}"}

    def clear_by_unit(self, purchase_unit: str) -> Dict[str, Any]:
        try:
            if not purchase_unit:
                return {"success": False, "message": "purchase_unit 不能为空"}

            # 统一单位名：清理按规范名执行
            try:
                resolved = resolve_purchase_unit(purchase_unit)
                if resolved:
                    purchase_unit = resolved.unit_name
            except Exception:
                pass

            with get_db() as db:
                inspector = sa_inspect(db.bind)
                if "shipment_records" not in inspector.get_table_names():
                    return {"success": False, "message": "数据库表不存在"}

                count = (
                    db.query(ShipmentRecord)
                    .filter(ShipmentRecord.purchase_unit == purchase_unit)
                    .count()
                )

                if count == 0:
                    # fuzzy fallback：历史数据 purchase_unit 写法不一致时，归一到 customers 规范名再删
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
                    candidate_values: list[str] = []
                    for (v,) in candidates:
                        if not v:
                            continue
                        if norm(v) == purchase_unit:
                            candidate_values.append(v)

                    if candidate_values:
                        count = (
                            db.query(ShipmentRecord)
                            .filter(ShipmentRecord.purchase_unit.in_(candidate_values))
                            .count()
                        )
                        db.query(ShipmentRecord).filter(
                            ShipmentRecord.purchase_unit.in_(candidate_values)
                        ).delete(synchronize_session=False)
                        db.commit()
                else:
                    db.query(ShipmentRecord).filter(
                        ShipmentRecord.purchase_unit == purchase_unit
                    ).delete(synchronize_session=False)
                    db.commit()

            return {
                "success": True,
                "message": f"已清理 {purchase_unit} 的出货记录",
                "deleted_orders": int(count or 0),
            }
        except Exception as e:
            return {"success": False, "message": f"清理失败：{str(e)}"}

    def update_record(
        self,
        record_id: int,
        *,
        unit_name: Optional[str] = None,
        date: Optional[str] = None,
        fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            with get_db() as db:
                inspector = sa_inspect(db.bind)
                if "shipment_records" not in inspector.get_table_names():
                    return {"success": False, "message": "数据库表不存在"}

                record = db.query(ShipmentRecord).filter(ShipmentRecord.id == record_id).first()
                if not record:
                    return {"success": False, "message": f"记录 {record_id} 不存在"}

                if unit_name:
                    record.purchase_unit = unit_name
                if date:
                    record.created_at = datetime.strptime(date, "%Y-%m-%d")

                for key, value in (fields or {}).items():
                    if hasattr(record, key):
                        setattr(record, key, value)

                record.updated_at = datetime.now()
                db.commit()

            return {"success": True, "message": "出货记录已更新"}
        except Exception as e:
            return {"success": False, "message": f"更新失败：{str(e)}"}

    def delete_record(self, record_id: int) -> Dict[str, Any]:
        try:
            with get_db() as db:
                inspector = sa_inspect(db.bind)
                if "shipment_records" not in inspector.get_table_names():
                    return {"success": False, "message": "数据库表不存在"}

                record = db.query(ShipmentRecord).filter(ShipmentRecord.id == record_id).first()
                if not record:
                    return {"success": False, "message": f"记录 {record_id} 不存在"}

                db.delete(record)
                db.commit()

            return {"success": True, "message": "出货记录已删除"}
        except Exception as e:
            return {"success": False, "message": f"删除失败：{str(e)}"}

