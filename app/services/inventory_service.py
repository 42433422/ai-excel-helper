# -*- coding: utf-8 -*-
"""
库存管理服务模块

提供仓库、库位、库存台账、库存流水等业务逻辑。
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import func

from app.db.models import (
    InventoryLedger,
    InventoryTransaction,
    Product,
    StorageLocation,
    Warehouse,
)
from app.db.session import get_db

logger = logging.getLogger(__name__)


class InventoryService:
    """库存管理服务类"""

    @staticmethod
    def _decimal_to_float(value: Any) -> Any:
        if isinstance(value, Decimal):
            return float(value)
        return value

    @staticmethod
    def _model_to_dict(model: Any) -> Dict[str, Any]:
        if model is None:
            return {}
        result = {}
        for col in model.__table__.columns:
            value = getattr(model, col.name)
            result[col.name] = InventoryService._decimal_to_float(value)
        return result

    def get_warehouses(self, status: Optional[str] = None) -> Dict[str, Any]:
        with get_db() as db:
            query = db.query(Warehouse)
            if status:
                query = query.filter(Warehouse.status == status)
            warehouses = query.order_by(Warehouse.code).all()
            return {
                "success": True,
                "data": [self._model_to_dict(w) for w in warehouses],
                "count": len(warehouses)
            }

    def get_warehouse(self, warehouse_id: int) -> Dict[str, Any]:
        with get_db() as db:
            warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
            if not warehouse:
                return {"success": False, "message": "仓库不存在"}
            return {"success": True, "data": self._model_to_dict(warehouse)}

    def create_warehouse(self, data: Dict[str, Any]) -> Dict[str, Any]:
        with get_db() as db:
            try:
                warehouse = Warehouse(
                    code=data.get("code"),
                    name=data.get("name"),
                    type=data.get("type"),
                    address=data.get("address"),
                    manager=data.get("manager"),
                    status=data.get("status", "active"),
                    created_at=datetime.now()
                )
                db.add(warehouse)
                db.commit()
                db.refresh(warehouse)
                return {"success": True, "data": self._model_to_dict(warehouse)}
            except Exception as e:
                db.rollback()
                logger.error(f"创建仓库失败: {e}")
                return {"success": False, "message": str(e)}

    def update_warehouse(self, warehouse_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        with get_db() as db:
            try:
                warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
                if not warehouse:
                    return {"success": False, "message": "仓库不存在"}

                for key, value in data.items():
                    if hasattr(warehouse, key):
                        setattr(warehouse, key, value)
                warehouse.updated_at = datetime.now()

                db.commit()
                db.refresh(warehouse)
                return {"success": True, "data": self._model_to_dict(warehouse)}
            except Exception as e:
                db.rollback()
                logger.error(f"更新仓库失败: {e}")
                return {"success": False, "message": str(e)}

    def delete_warehouse(self, warehouse_id: int) -> Dict[str, Any]:
        with get_db() as db:
            try:
                warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
                if not warehouse:
                    return {"success": False, "message": "仓库不存在"}
                warehouse.status = "deleted"
                db.commit()
                return {"success": True, "message": "仓库已删除"}
            except Exception as e:
                db.rollback()
                logger.error(f"删除仓库失败: {e}")
                return {"success": False, "message": str(e)}

    def get_storage_locations(self, warehouse_id: int, status: Optional[str] = None) -> Dict[str, Any]:
        with get_db() as db:
            query = db.query(StorageLocation).filter(StorageLocation.warehouse_id == warehouse_id)
            if status:
                query = query.filter(StorageLocation.status == status)
            locations = query.order_by(StorageLocation.code).all()
            return {
                "success": True,
                "data": [self._model_to_dict(loc) for loc in locations],
                "count": len(locations)
            }

    def create_storage_location(self, data: Dict[str, Any]) -> Dict[str, Any]:
        with get_db() as db:
            try:
                location = StorageLocation(
                    warehouse_id=data.get("warehouse_id"),
                    code=data.get("code"),
                    name=data.get("name"),
                    max_capacity=self._decimal_to_float(data.get("max_capacity")),
                    current_capacity=self._decimal_to_float(data.get("current_capacity", 0)),
                    status=data.get("status", "active"),
                    created_at=datetime.now()
                )
                db.add(location)
                db.commit()
                db.refresh(location)
                return {"success": True, "data": self._model_to_dict(location)}
            except Exception as e:
                db.rollback()
                logger.error(f"创建库位失败: {e}")
                return {"success": False, "message": str(e)}

    def get_inventory(
        self,
        warehouse_id: Optional[int] = None,
        product_id: Optional[int] = None,
        batch_no: Optional[str] = None,
        page: int = 1,
        per_page: int = 50
    ) -> Dict[str, Any]:
        with get_db() as db:
            query = db.query(InventoryLedger).join(Product)

            if warehouse_id:
                query = query.filter(InventoryLedger.warehouse_id == warehouse_id)
            if product_id:
                query = query.filter(InventoryLedger.product_id == product_id)
            if batch_no:
                query = query.filter(InventoryLedger.batch_no == batch_no)

            total = query.count()
            items = query.order_by(InventoryLedger.created_at.desc())\
                .offset((page - 1) * per_page)\
                .limit(per_page)\
                .all()

            result = []
            for item in items:
                item_dict = self._model_to_dict(item)
                item_dict["product_name"] = item.product.name if item.product else None
                item_dict["product_code"] = item.product.model_number if item.product else None
                item_dict["warehouse_name"] = item.warehouse.name if item.warehouse else None
                item_dict["location_name"] = item.location.name if item.location else None
                result.append(item_dict)

            return {
                "success": True,
                "data": result,
                "total": total,
                "page": page,
                "per_page": per_page
            }

    def get_inventory_summary(self, warehouse_id: Optional[int] = None) -> Dict[str, Any]:
        with get_db() as db:
            query = db.query(
                InventoryLedger.product_id,
                Product.name.label("product_name"),
                Product.model_number,
                func.sum(InventoryLedger.quantity).label("total_quantity"),
                func.sum(InventoryLedger.available_quantity).label("total_available")
            ).join(Product)

            if warehouse_id:
                query = query.filter(InventoryLedger.warehouse_id == warehouse_id)

            query = query.group_by(
                InventoryLedger.product_id,
                Product.name,
                Product.model_number
            )

            items = query.all()
            return {
                "success": True,
                "data": [
                    {
                        "product_id": item.product_id,
                        "product_name": item.product_name,
                        "model_number": item.model_number,
                        "total_quantity": self._decimal_to_float(item.total_quantity),
                        "total_available": self._decimal_to_float(item.total_available)
                    }
                    for item in items
                ]
            }

    def inventory_in(
        self,
        product_id: int,
        warehouse_id: int,
        quantity: float,
        batch_no: Optional[str] = None,
        location_id: Optional[int] = None,
        unit_price: Optional[float] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None,
        operator: Optional[str] = None,
        remark: Optional[str] = None
    ) -> Dict[str, Any]:
        with get_db() as db:
            try:
                product = db.query(Product).filter(Product.id == product_id).first()
                if not product:
                    return {"success": False, "message": "产品不存在"}

                ledger = db.query(InventoryLedger).filter(
                    InventoryLedger.product_id == product_id,
                    InventoryLedger.warehouse_id == warehouse_id,
                    InventoryLedger.batch_no == batch_no
                ).first()

                now = datetime.now()
                if ledger:
                    ledger.quantity = float(ledger.quantity or 0) + quantity
                    ledger.available_quantity = float(ledger.available_quantity or 0) + quantity
                    ledger.updated_at = now
                else:
                    ledger = InventoryLedger(
                        product_id=product_id,
                        warehouse_id=warehouse_id,
                        location_id=location_id,
                        batch_no=batch_no,
                        quantity=quantity,
                        available_quantity=quantity,
                        reserved_quantity=0,
                        unit=product.unit or "个",
                        in_date=now.date(),
                        created_at=now,
                        updated_at=now
                    )
                    db.add(ledger)

                db.flush()

                transaction = InventoryTransaction(
                    ledger_id=ledger.id,
                    transaction_type="in",
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                    location_id=location_id,
                    batch_no=batch_no,
                    quantity=quantity,
                    before_quantity=float(ledger.quantity) - quantity,
                    after_quantity=float(ledger.quantity),
                    unit_price=unit_price,
                    total_amount=(quantity * unit_price) if unit_price else None,
                    reference_type=reference_type,
                    reference_id=reference_id,
                    transaction_date=now,
                    operator=operator,
                    remark=remark,
                    created_at=now
                )
                db.add(transaction)
                db.commit()

                return {
                    "success": True,
                    "message": "入库成功",
                    "data": {
                        "ledger_id": ledger.id,
                        "quantity": quantity,
                        "total_quantity": float(ledger.quantity)
                    }
                }
            except Exception as e:
                db.rollback()
                logger.error(f"入库失败: {e}")
                return {"success": False, "message": str(e)}

    def inventory_out(
        self,
        product_id: int,
        warehouse_id: int,
        quantity: float,
        batch_no: Optional[str] = None,
        location_id: Optional[int] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None,
        operator: Optional[str] = None,
        remark: Optional[str] = None
    ) -> Dict[str, Any]:
        with get_db() as db:
            try:
                query = db.query(InventoryLedger).filter(
                    InventoryLedger.product_id == product_id,
                    InventoryLedger.warehouse_id == warehouse_id,
                    InventoryLedger.available_quantity >= quantity
                )

                if batch_no:
                    query = query.filter(InventoryLedger.batch_no == batch_no)
                if location_id:
                    query = query.filter(InventoryLedger.location_id == location_id)

                ledger = query.first()
                if not ledger:
                    return {"success": False, "message": "库存不足或库存记录不存在"}

                now = datetime.now()
                ledger.quantity = float(ledger.quantity) - quantity
                ledger.available_quantity = float(ledger.available_quantity) - quantity
                ledger.updated_at = now

                transaction = InventoryTransaction(
                    ledger_id=ledger.id,
                    transaction_type="out",
                    product_id=product_id,
                    warehouse_id=warehouse_id,
                    location_id=location_id,
                    batch_no=batch_no,
                    quantity=-quantity,
                    before_quantity=float(ledger.quantity) + quantity,
                    after_quantity=float(ledger.quantity),
                    reference_type=reference_type,
                    reference_id=reference_id,
                    transaction_date=now,
                    operator=operator,
                    remark=remark,
                    created_at=now
                )
                db.add(transaction)
                db.commit()

                return {
                    "success": True,
                    "message": "出库成功",
                    "data": {
                        "ledger_id": ledger.id,
                        "quantity": quantity,
                        "remaining_quantity": float(ledger.quantity)
                    }
                }
            except Exception as e:
                db.rollback()
                logger.error(f"出库失败: {e}")
                return {"success": False, "message": str(e)}

    def inventory_transfer(
        self,
        product_id: int,
        from_warehouse_id: int,
        to_warehouse_id: int,
        quantity: float,
        from_location_id: Optional[int] = None,
        to_location_id: Optional[int] = None,
        batch_no: Optional[str] = None,
        operator: Optional[str] = None,
        remark: Optional[str] = None
    ) -> Dict[str, Any]:
        with get_db() as db:
            try:
                from_ledger = db.query(InventoryLedger).filter(
                    InventoryLedger.product_id == product_id,
                    InventoryLedger.warehouse_id == from_warehouse_id,
                    InventoryLedger.available_quantity >= quantity
                ).first()

                if not from_ledger:
                    return {"success": False, "message": "源仓库库存不足"}

                now = datetime.now()

                from_ledger.quantity = float(from_ledger.quantity) - quantity
                from_ledger.available_quantity = float(from_ledger.available_quantity) - quantity
                from_ledger.updated_at = now

                out_transaction = InventoryTransaction(
                    ledger_id=from_ledger.id,
                    transaction_type="transfer_out",
                    product_id=product_id,
                    warehouse_id=from_warehouse_id,
                    location_id=from_location_id,
                    batch_no=batch_no,
                    quantity=-quantity,
                    before_quantity=float(from_ledger.quantity) + quantity,
                    after_quantity=float(from_ledger.quantity),
                    reference_type="transfer",
                    transaction_date=now,
                    operator=operator,
                    remark=f"调出至仓库{to_warehouse_id}",
                    created_at=now
                )
                db.add(out_transaction)

                to_ledger = db.query(InventoryLedger).filter(
                    InventoryLedger.product_id == product_id,
                    InventoryLedger.warehouse_id == to_warehouse_id,
                    (InventoryLedger.batch_no == batch_no) | (InventoryLedger.batch_no.is_(None))
                ).first()

                if to_ledger:
                    to_ledger.quantity = float(to_ledger.quantity) + quantity
                    to_ledger.available_quantity = float(to_ledger.available_quantity) + quantity
                    to_ledger.updated_at = now
                else:
                    to_ledger = InventoryLedger(
                        product_id=product_id,
                        warehouse_id=to_warehouse_id,
                        location_id=to_location_id,
                        batch_no=batch_no,
                        quantity=quantity,
                        available_quantity=quantity,
                        reserved_quantity=0,
                        unit=from_ledger.unit,
                        in_date=now.date(),
                        created_at=now,
                        updated_at=now
                    )
                    db.add(to_ledger)

                db.flush()

                in_transaction = InventoryTransaction(
                    ledger_id=to_ledger.id,
                    transaction_type="transfer_in",
                    product_id=product_id,
                    warehouse_id=to_warehouse_id,
                    location_id=to_location_id,
                    batch_no=batch_no,
                    quantity=quantity,
                    before_quantity=float(to_ledger.quantity) - quantity,
                    after_quantity=float(to_ledger.quantity),
                    reference_type="transfer",
                    transaction_date=now,
                    operator=operator,
                    remark=f"从仓库{from_warehouse_id}调入",
                    created_at=now
                )
                db.add(in_transaction)
                db.commit()

                return {
                    "success": True,
                    "message": "调拨成功",
                    "data": {
                        "from_ledger_id": from_ledger.id,
                        "to_ledger_id": to_ledger.id,
                        "quantity": quantity
                    }
                }
            except Exception as e:
                db.rollback()
                logger.error(f"调拨失败: {e}")
                return {"success": False, "message": str(e)}

    def get_inventory_transactions(
        self,
        product_id: Optional[int] = None,
        warehouse_id: Optional[int] = None,
        transaction_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 50
    ) -> Dict[str, Any]:
        with get_db() as db:
            query = db.query(InventoryTransaction)

            if product_id:
                query = query.filter(InventoryTransaction.product_id == product_id)
            if warehouse_id:
                query = query.filter(InventoryTransaction.warehouse_id == warehouse_id)
            if transaction_type:
                query = query.filter(InventoryTransaction.transaction_type == transaction_type)
            if start_date:
                query = query.filter(InventoryTransaction.transaction_date >= start_date)
            if end_date:
                query = query.filter(InventoryTransaction.transaction_date <= end_date)

            total = query.count()
            items = query.order_by(InventoryTransaction.transaction_date.desc())\
                .offset((page - 1) * per_page)\
                .limit(per_page)\
                .all()

            result = []
            for item in items:
                item_dict = self._model_to_dict(item)
                item_dict["product_name"] = item.product.name if item.product else None
                item_dict["warehouse_name"] = item.warehouse.name if item.warehouse else None
                item_dict["location_name"] = item.location.name if item.location else None
                result.append(item_dict)

            return {
                "success": True,
                "data": result,
                "total": total,
                "page": page,
                "per_page": per_page
            }

    def get_inventory_alert(self) -> Dict[str, Any]:
        with get_db() as db:
            query = db.query(InventoryLedger).join(Product).filter(
                InventoryLedger.available_quantity <= 0
            )
            items = query.all()

            result = []
            for item in items:
                item_dict = self._model_to_dict(item)
                item_dict["product_name"] = item.product.name if item.product else None
                item_dict["product_code"] = item.product.model_number if item.product else None
                result.append(item_dict)

            return {
                "success": True,
                "data": result,
                "count": len(result)
            }
