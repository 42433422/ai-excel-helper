from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.application.ports.shipment_record_store import ShipmentRecordStorePort
from app.db.models import ShipmentRecord
from app.db.session import get_db


class SQLAlchemyShipmentRecordStore(ShipmentRecordStorePort):
    """出货记录写入（SQLAlchemy 实现）。"""

    def record_document_generation(
        self,
        *,
        unit_name: str,
        unit_id: Optional[int],
        products: List[Dict[str, Any]],
        document_result: Dict[str, Any],
        raw_text: str = "",
    ) -> Dict[str, Any]:
        # 现有 schema 是“扁平记录”，历史上也通常只存首个产品 + 汇总
        first = (products or [{}])[0] or {}
        product_name = first.get("name") or first.get("product_name") or ""
        model_number = first.get("model_number") or first.get("型号") or ""
        quantity_tins = first.get("quantity_tins")
        if quantity_tins is None:
            quantity_tins = first.get("quantity", 0)
        tin_spec = first.get("tin_spec") or first.get("spec") or 10.0
        quantity_kg = first.get("quantity_kg")
        if quantity_kg is None:
            try:
                quantity_kg = float(quantity_tins or 0) * float(tin_spec or 0)
            except Exception:
                quantity_kg = 0.0
        unit_price = first.get("unit_price")
        if unit_price is None:
            unit_price = first.get("price", 0.0)
        amount = first.get("amount")
        if amount is None:
            try:
                amount = float(unit_price or 0) * float(quantity_kg or 0)
            except Exception:
                amount = 0.0

        now = datetime.now()
        parsed_data_json = json.dumps(
            {
                "purchase_unit": unit_name,
                "products": products,
                "document": {
                    "doc_name": document_result.get("doc_name"),
                    "file_path": document_result.get("file_path"),
                    "order_number": document_result.get("order_number"),
                    "total_amount": document_result.get("total_amount"),
                    "total_quantity": document_result.get("total_quantity"),
                },
            },
            ensure_ascii=False,
        )

        with get_db() as db:
            record = ShipmentRecord(
                purchase_unit=unit_name,
                unit_id=unit_id,
                product_name=product_name or unit_name,
                model_number=model_number,
                quantity_kg=float(quantity_kg or 0.0),
                quantity_tins=int(quantity_tins or 0),
                tin_spec=float(tin_spec or 10.0),
                unit_price=float(unit_price or 0.0),
                amount=float(amount or 0.0),
                status="pending",
                created_at=now,
                updated_at=now,
                raw_text=raw_text or "",
                parsed_data=parsed_data_json,
            )
            db.add(record)
            db.commit()
            db.refresh(record)

        return {"success": True, "record_id": record.id}

