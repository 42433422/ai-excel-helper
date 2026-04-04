# -*- coding: utf-8 -*-
"""
采购管理服务模块

提供供应商、采购订单、采购入库等业务逻辑。
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import func

from app.db.models import (
    Product,
    PurchaseInbound,
    PurchaseInboundItem,
    PurchaseOrder,
    PurchaseOrderItem,
    Supplier,
    Warehouse,
)
from app.db.session import get_db
from app.services.inventory_service import InventoryService

logger = logging.getLogger(__name__)


class PurchaseService:
    """采购管理服务类"""

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
            result[col.name] = PurchaseService._decimal_to_float(value)
        return result

    def get_suppliers(self, status: Optional[str] = None, keyword: Optional[str] = None) -> Dict[str, Any]:
        with get_db() as db:
            query = db.query(Supplier)
            if status:
                query = query.filter(Supplier.status == status)
            if keyword:
                query = query.filter(
                    Supplier.name.like(f"%{keyword}%") |
                    Supplier.code.like(f"%{keyword}%") |
                    Supplier.contact_person.like(f"%{keyword}%")
                )
            suppliers = query.order_by(Supplier.code).all()
            return {
                "success": True,
                "data": [self._model_to_dict(s) for s in suppliers],
                "count": len(suppliers)
            }

    def get_supplier(self, supplier_id: int) -> Dict[str, Any]:
        with get_db() as db:
            supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
            if not supplier:
                return {"success": False, "message": "供应商不存在"}
            return {"success": True, "data": self._model_to_dict(supplier)}

    def create_supplier(self, data: Dict[str, Any]) -> Dict[str, Any]:
        with get_db() as db:
            try:
                supplier = Supplier(
                    code=data.get("code"),
                    name=data.get("name"),
                    contact_person=data.get("contact_person"),
                    contact_phone=data.get("contact_phone"),
                    contact_email=data.get("contact_email"),
                    address=data.get("address"),
                    payment_terms=data.get("payment_terms", "月结"),
                    credit_limit=self._decimal_to_float(data.get("credit_limit", 0)),
                    status=data.get("status", "active"),
                    rating=data.get("rating", 3),
                    remark=data.get("remark"),
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(supplier)
                db.commit()
                db.refresh(supplier)
                return {"success": True, "data": self._model_to_dict(supplier)}
            except Exception as e:
                db.rollback()
                logger.error(f"创建供应商失败: {e}")
                return {"success": False, "message": str(e)}

    def update_supplier(self, supplier_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        with get_db() as db:
            try:
                supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
                if not supplier:
                    return {"success": False, "message": "供应商不存在"}

                for key, value in data.items():
                    if hasattr(supplier, key):
                        setattr(supplier, key, value)
                supplier.updated_at = datetime.now()

                db.commit()
                db.refresh(supplier)
                return {"success": True, "data": self._model_to_dict(supplier)}
            except Exception as e:
                db.rollback()
                logger.error(f"更新供应商失败: {e}")
                return {"success": False, "message": str(e)}

    def delete_supplier(self, supplier_id: int) -> Dict[str, Any]:
        with get_db() as db:
            try:
                supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
                if not supplier:
                    return {"success": False, "message": "供应商不存在"}
                supplier.status = "deleted"
                db.commit()
                return {"success": True, "message": "供应商已删除"}
            except Exception as e:
                db.rollback()
                logger.error(f"删除供应商失败: {e}")
                return {"success": False, "message": str(e)}

    def get_purchase_orders(
        self,
        supplier_id: Optional[int] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        with get_db() as db:
            query = db.query(PurchaseOrder).join(Supplier)

            if supplier_id:
                query = query.filter(PurchaseOrder.supplier_id == supplier_id)
            if status:
                query = query.filter(PurchaseOrder.status == status)
            if start_date:
                query = query.filter(PurchaseOrder.order_date >= start_date)
            if end_date:
                query = query.filter(PurchaseOrder.order_date <= end_date)

            total = query.count()
            orders = query.order_by(PurchaseOrder.created_at.desc())\
                .offset((page - 1) * per_page)\
                .limit(per_page)\
                .all()

            result = []
            for order in orders:
                order_dict = self._model_to_dict(order)
                order_dict["supplier_name"] = order.supplier.name if order.supplier else None
                order_dict["items"] = [self._model_to_dict(item) for item in order.items] if order.items else []
                result.append(order_dict)

            return {
                "success": True,
                "data": result,
                "total": total,
                "page": page,
                "per_page": per_page
            }

    def get_purchase_order(self, order_id: int) -> Dict[str, Any]:
        with get_db() as db:
            order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
            if not order:
                return {"success": False, "message": "采购订单不存在"}

            order_dict = self._model_to_dict(order)
            order_dict["supplier_name"] = order.supplier.name if order.supplier else None
            order_dict["warehouse_name"] = order.warehouse.name if order.warehouse else None
            order_dict["items"] = []
            for item in order.items:
                item_dict = self._model_to_dict(item)
                item_dict["product_name"] = item.product.name if item.product else None
                order_dict["items"].append(item_dict)

            return {"success": True, "data": order_dict}

    def create_purchase_order(self, data: Dict[str, Any]) -> Dict[str, Any]:
        with get_db() as db:
            try:
                order_no = data.get("order_no") or self._generate_order_no()
                total_amount = 0

                order = PurchaseOrder(
                    order_no=order_no,
                    supplier_id=data.get("supplier_id"),
                    warehouse_id=data.get("warehouse_id"),
                    order_date=data.get("order_date", datetime.now().date()),
                    delivery_date=data.get("delivery_date"),
                    total_amount=0,
                    status="draft",
                    remark=data.get("remark"),
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(order)
                db.flush()

                items_data = data.get("items", [])
                for item_data in items_data:
                    product = db.query(Product).filter(Product.id == item_data.get("product_id")).first()
                    quantity = float(item_data.get("quantity", 0))
                    unit_price = float(item_data.get("unit_price", 0))
                    amount = quantity * unit_price
                    total_amount += amount

                    item = PurchaseOrderItem(
                        order_id=order.id,
                        product_id=item_data.get("product_id"),
                        product_name=product.name if product else item_data.get("product_name"),
                        specification=item_data.get("specification"),
                        quantity=quantity,
                        unit=item_data.get("unit", "个"),
                        unit_price=unit_price,
                        amount=amount,
                        received_quantity=0,
                        invoiced_quantity=0,
                        status="pending",
                        remark=item_data.get("remark"),
                        created_at=datetime.now()
                    )
                    db.add(item)

                order.total_amount = total_amount
                db.commit()
                db.refresh(order)

                return {
                    "success": True,
                    "data": self._model_to_dict(order),
                    "message": "采购订单创建成功"
                }
            except Exception as e:
                db.rollback()
                logger.error(f"创建采购订单失败: {e}")
                return {"success": False, "message": str(e)}

    def update_purchase_order(self, order_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        with get_db() as db:
            try:
                order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
                if not order:
                    return {"success": False, "message": "采购订单不存在"}

                if order.status not in ("draft", "rejected"):
                    return {"success": False, "message": "只有草稿状态的订单可以修改"}

                for key, value in data.items():
                    if key == "items":
                        continue
                    if hasattr(order, key):
                        setattr(order, key, value)
                order.updated_at = datetime.now()

                if "items" in data:
                    db.query(PurchaseOrderItem).filter(PurchaseOrderItem.order_id == order_id).delete()
                    total_amount = 0

                    for item_data in data["items"]:
                        product = db.query(Product).filter(Product.id == item_data.get("product_id")).first()
                        quantity = float(item_data.get("quantity", 0))
                        unit_price = float(item_data.get("unit_price", 0))
                        amount = quantity * unit_price
                        total_amount += amount

                        item = PurchaseOrderItem(
                            order_id=order.id,
                            product_id=item_data.get("product_id"),
                            product_name=product.name if product else item_data.get("product_name"),
                            specification=item_data.get("specification"),
                            quantity=quantity,
                            unit=item_data.get("unit", "个"),
                            unit_price=unit_price,
                            amount=amount,
                            received_quantity=0,
                            invoiced_quantity=0,
                            status="pending",
                            remark=item_data.get("remark"),
                            created_at=datetime.now()
                        )
                        db.add(item)

                    order.total_amount = total_amount

                db.commit()
                db.refresh(order)
                return {"success": True, "data": self._model_to_dict(order)}
            except Exception as e:
                db.rollback()
                logger.error(f"更新采购订单失败: {e}")
                return {"success": False, "message": str(e)}

    def approve_purchase_order(self, order_id: int, approver: str) -> Dict[str, Any]:
        with get_db() as db:
            try:
                order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
                if not order:
                    return {"success": False, "message": "采购订单不存在"}

                if order.status != "draft":
                    return {"success": False, "message": "只有草稿状态的订单可以审核"}

                order.status = "approved"
                order.approver = approver
                order.approve_date = datetime.now()
                order.updated_at = datetime.now()

                for item in order.items:
                    item.status = "approved"

                db.commit()
                return {"success": True, "message": "审核成功"}
            except Exception as e:
                db.rollback()
                logger.error(f"审核采购订单失败: {e}")
                return {"success": False, "message": str(e)}

    def cancel_purchase_order(self, order_id: int) -> Dict[str, Any]:
        with get_db() as db:
            try:
                order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
                if not order:
                    return {"success": False, "message": "采购订单不存在"}

                if order.status in ("completed", "cancelled"):
                    return {"success": False, "message": "该订单无法取消"}

                order.status = "cancelled"
                order.updated_at = datetime.now()

                for item in order.items:
                    item.status = "cancelled"

                db.commit()
                return {"success": True, "message": "订单已取消"}
            except Exception as e:
                db.rollback()
                logger.error(f"取消采购订单失败: {e}")
                return {"success": False, "message": str(e)}

    def create_purchase_inbound(self, data: Dict[str, Any]) -> Dict[str, Any]:
        with get_db() as db:
            try:
                inbound_no = data.get("inbound_no") or self._generate_inbound_no()
                total_amount = 0
                inventory_service = InventoryService()

                inbound = PurchaseInbound(
                    inbound_no=inbound_no,
                    order_id=data.get("order_id"),
                    supplier_id=data.get("supplier_id"),
                    warehouse_id=data.get("warehouse_id"),
                    inbound_date=data.get("inbound_date", datetime.now().date()),
                    total_amount=0,
                    status="draft",
                    handler=data.get("handler"),
                    remark=data.get("remark"),
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(inbound)
                db.flush()

                items_data = data.get("items", [])
                for item_data in items_data:
                    product = db.query(Product).filter(Product.id == item_data.get("product_id")).first()
                    quantity = float(item_data.get("quantity", 0))
                    unit_price = float(item_data.get("unit_price", 0))
                    amount = quantity * unit_price
                    total_amount += amount

                    item = PurchaseInboundItem(
                        inbound_id=inbound.id,
                        product_id=item_data.get("product_id"),
                        order_item_id=item_data.get("order_item_id"),
                        product_name=product.name if product else item_data.get("product_name"),
                        batch_no=item_data.get("batch_no"),
                        quantity=quantity,
                        unit=item_data.get("unit", "个"),
                        unit_price=unit_price,
                        amount=amount,
                        location_id=item_data.get("location_id"),
                        remark=item_data.get("remark"),
                        created_at=datetime.now()
                    )
                    db.add(item)

                    result = inventory_service.inventory_in(
                        product_id=item_data.get("product_id"),
                        warehouse_id=data.get("warehouse_id"),
                        quantity=quantity,
                        batch_no=item_data.get("batch_no"),
                        location_id=item_data.get("location_id"),
                        unit_price=unit_price,
                        reference_type="purchase_inbound",
                        reference_id=inbound.id,
                        operator=data.get("handler"),
                        remark=f"采购入库单: {inbound_no}"
                    )
                    if not result.get("success"):
                        logger.warning(f"库存入库失败: {result.get('message')}")

                inbound.total_amount = total_amount
                inbound.status = "completed"
                db.commit()
                db.refresh(inbound)

                if data.get("order_id"):
                    self._update_order_received_quantity(db, data.get("order_id"))

                return {
                    "success": True,
                    "data": self._model_to_dict(inbound),
                    "message": "入库成功"
                }
            except Exception as e:
                db.rollback()
                logger.error(f"创建采购入库单失败: {e}")
                return {"success": False, "message": str(e)}

    def _update_order_received_quantity(self, db, order_id: int):
        order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
        if not order:
            return

        for item in order.items:
            inbound_items = db.query(PurchaseInboundItem).filter(
                PurchaseInboundItem.order_item_id == item.id
            ).all()
            received = sum(float(i.quantity) for i in inbound_items)
            item.received_quantity = received

            if float(item.quantity) <= received:
                item.status = "completed"
            elif received > 0:
                item.status = "partial"

        all_completed = all(
            float(item.quantity) <= float(item.received_quantity)
            for item in order.items
        )
        any_received = any(
            float(item.received_quantity) > 0
            for item in order.items
        )

        if all_completed:
            order.status = "completed"
        elif any_received:
            order.status = "partial"

    def get_purchase_inbounds(
        self,
        supplier_id: Optional[int] = None,
        order_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        with get_db() as db:
            query = db.query(PurchaseInbound)

            if supplier_id:
                query = query.filter(PurchaseInbound.supplier_id == supplier_id)
            if order_id:
                query = query.filter(PurchaseInbound.order_id == order_id)
            if start_date:
                query = query.filter(PurchaseInbound.inbound_date >= start_date)
            if end_date:
                query = query.filter(PurchaseInbound.inbound_date <= end_date)

            total = query.count()
            inbounds = query.order_by(PurchaseInbound.created_at.desc())\
                .offset((page - 1) * per_page)\
                .limit(per_page)\
                .all()

            result = []
            for inbound in inbounds:
                inbound_dict = self._model_to_dict(inbound)
                inbound_dict["supplier_name"] = inbound.supplier.name if inbound.supplier else None
                inbound_dict["warehouse_name"] = inbound.warehouse.name if inbound.warehouse else None
                inbound_dict["items"] = [self._model_to_dict(item) for item in inbound.items] if inbound.items else []
                result.append(inbound_dict)

            return {
                "success": True,
                "data": result,
                "total": total,
                "page": page,
                "per_page": per_page
            }

    def _generate_order_no(self) -> str:
        return f"PO{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def _generate_inbound_no(self) -> str:
        return f"PI{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def get_supplier_summary(self) -> Dict[str, Any]:
        with get_db() as db:
            stats = db.query(
                Supplier.status,
                func.count(Supplier.id).label("count")
            ).group_by(Supplier.status).all()

            result = {}
            for status, count in stats:
                result[status or "unknown"] = count

            return {
                "success": True,
                "data": result
            }

    def get_purchase_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        with get_db() as db:
            query = db.query(
                PurchaseOrder.status,
                func.count(PurchaseOrder.id).label("count"),
                func.sum(PurchaseOrder.total_amount).label("amount")
            )

            if start_date:
                query = query.filter(PurchaseOrder.order_date >= start_date)
            if end_date:
                query = query.filter(PurchaseOrder.order_date <= end_date)

            query = query.group_by(PurchaseOrder.status)
            stats = query.all()

            result = {}
            for status, count, amount in stats:
                result[status or "unknown"] = {
                    "count": count,
                    "amount": self._decimal_to_float(amount)
                }

            return {
                "success": True,
                "data": result
            }
