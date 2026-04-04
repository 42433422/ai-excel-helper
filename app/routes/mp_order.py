# -*- coding: utf-8 -*-
"""
小程序订单 API
"""
import logging
import random
import string
from datetime import datetime

from flask import Blueprint, request

from app.db.models import MpOrder, MpOrderItem, MpCart, Product, User, MpAddress
from app.db.session import get_db
from app.decorators.mp_auth import mp_auth_required, get_current_mp_user_id
from app.utils.mp_response import error, paginate, success

logger = logging.getLogger(__name__)

mp_order_bp = Blueprint("mp_order", __name__, url_prefix="/api/mp/v1/order")


def generate_order_no():
    prefix = datetime.now().strftime("%Y%m%d%H%M%S")
    suffix = "".join(random.choices(string.digits, k=6))
    return f"MP{prefix}{suffix}"


@mp_order_bp.route("/create", methods=["POST"])
@mp_auth_required
def order_create():
    user_id = get_current_mp_user_id()
    data = request.get_json(silent=True) or {}

    address_id = data.get("address_id")
    remark = data.get("remark", "")
    cart_item_ids = data.get("cart_item_ids", [])

    if not address_id:
        return error("请选择收货地址", 400)

    with get_db() as db:
        address = db.query(MpAddress).filter(
            MpAddress.id == address_id,
            MpAddress.user_id == user_id,
        ).first()
        if not address:
            return error("收货地址不存在", 404)

        if cart_item_ids:
            carts = db.query(MpCart).filter(
                MpCart.id.in_(cart_item_ids),
                MpCart.user_id == user_id,
                MpCart.selected == True,
            ).all()
        else:
            carts = db.query(MpCart).filter(
                MpCart.user_id == user_id,
                MpCart.selected == True,
            ).all()

        if not carts:
            return error("请选择要结算的商品", 400)

        order_items_data = []
        total_amount = 0.0

        for cart in carts:
            product = db.query(Product).filter(Product.id == cart.product_id).first()
            if not product or product.is_active != 1:
                continue

            unit_price = float(product.price) if product.price else 0
            subtotal = round(unit_price * cart.quantity, 2)
            total_amount += subtotal

            order_items_data.append({
                "product_id": product.id,
                "product_name": product.name,
                "product_sku": product.model_number or "",
                "quantity": cart.quantity,
                "unit_price": unit_price,
                "subtotal": subtotal,
            })

        if not order_items_data:
            return error("没有有效的商品", 400)

        order = MpOrder(
            order_no=generate_order_no(),
            user_id=user_id,
            status="pending",
            total_amount=round(total_amount, 2),
            pay_status="unpaid",
            delivery_name=address.contact_name,
            delivery_phone=address.contact_phone,
            delivery_address=f"{address.province}{address.city}{address.district}{address.detail_address}",
            delivery_province=address.province,
            delivery_city=address.city,
            delivery_district=address.district,
            remark=remark,
        )
        db.add(order)
        db.flush()

        for item_data in order_items_data:
            item = MpOrderItem(
                order_id=order.id,
                **item_data,
            )
            db.add(item)

        db.query(MpCart).filter(MpCart.id.in_([c.id for c in carts])).delete()
        db.commit()
        db.refresh(order)

        return success({
            "order_id": order.id,
            "order_no": order.order_no,
            "total_amount": float(order.total_amount),
            "status": order.status,
        }, "订单创建成功")


@mp_order_bp.route("/list", methods=["GET"])
@mp_auth_required
def order_list():
    user_id = get_current_mp_user_id()
    page = max(1, request.args.get("page", 1, type=int))
    page_size = min(50, max(1, request.args.get("page_size", 20, type=int)))
    status_filter = request.args.get("status", "").strip()

    with get_db() as db:
        query = db.query(MpOrder).filter(MpOrder.user_id == user_id)

        if status_filter and status_filter != "all":
            query = query.filter(MpOrder.status == status_filter)

        query = query.order_by(MpOrder.created_at.desc())
        total = query.count()
        orders = query.offset((page - 1) * page_size).limit(page_size).all()

        result = []
        for o in orders:
            first_item = o.items[0] if o.items else None
            result.append({
                "id": o.id,
                "order_no": o.order_no,
                "status": o.status,
                "pay_status": o.pay_status,
                "total_amount": float(o.total_amount),
                "pay_amount": float(o.pay_amount) if o.pay_amount else None,
                "item_count": len(o.items),
                "first_item_name": first_item.product_name if first_item else "",
                "created_at": o.created_at.isoformat() if o.created_at else None,
            })

        return paginate(result, total, page, page_size)


@mp_order_bp.route("/detail/<int:order_id>", methods=["GET"])
@mp_auth_required
def order_detail(order_id):
    user_id = get_current_mp_user_id()
    with get_db() as db:
        order = db.query(MpOrder).filter(
            MpOrder.id == order_id,
            MpOrder.user_id == user_id,
        ).first()

        if not order:
            return error("订单不存在", 404)

        items = []
        for item in order.items:
            items.append({
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product_name,
                "product_sku": item.product_sku or "",
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "subtotal": float(item.subtotal),
            })

        return success({
            "id": order.id,
            "order_no": order.order_no,
            "status": order.status,
            "pay_status": order.pay_status,
            "total_amount": float(order.total_amount),
            "pay_amount": float(order.pay_amount) if order.pay_amount else None,
            "pay_time": order.pay_time.isoformat() if order.pay_time else None,
            "delivery_name": order.delivery_name or "",
            "delivery_phone": order.delivery_phone or "",
            "delivery_address": order.delivery_address or "",
            "remark": order.remark or "",
            "items": items,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "updated_at": order.updated_at.isoformat() if order.updated_at else None,
        })


@mp_order_bp.route("/cancel/<int:order_id>", methods=["PUT"])
@mp_auth_required
def order_cancel(order_id):
    user_id = get_current_mp_user_id()
    with get_db() as db:
        order = db.query(MpOrder).filter(
            MpOrder.id == order_id,
            MpOrder.user_id == user_id,
        ).first()

        if not order:
            return error("订单不存在", 404)

        if order.status not in ("pending", "paid"):
            return error("当前状态不允许取消", 400)

        order.status = "cancelled"
        db.commit()

        return success({"order_id": order.id, "status": order.status}, "订单已取消")


@mp_order_bp.route("/confirm/<int:order_id>", methods=["PUT"])
@mp_auth_required
def order_confirm(order_id):
    user_id = get_current_mp_user_id()
    with get_db() as db:
        order = db.query(MpOrder).filter(
            MpOrder.id == order_id,
            MpOrder.user_id == user_id,
        ).first()

        if not order:
            return error("订单不存在", 404)

        if order.status != "shipped":
            return error("当前状态无法确认收货", 400)

        order.status = "completed"
        db.commit()

        return success({"order_id": order.id, "status": order.status}, "确认收货成功")


@mp_order_bp.route("/rebuy/<int:order_id>", methods=["POST"])
@mp_auth_required
def order_rebuy(order_id):
    user_id = get_current_mp_user_id()
    with get_db() as db:
        order = db.query(MpOrder).filter(
            MpOrder.id == order_id,
            MpOrder.user_id == user_id,
        ).first()

        if not order:
            return error("订单不存在", 404)

        for item in order.items:
            existing = db.query(MpCart).filter(
                MpCart.user_id == user_id,
                MpCart.product_id == item.product_id,
            ).first()

            if existing:
                existing.quantity += item.quantity
                existing.selected = True
            else:
                new_cart = MpCart(
                    user_id=user_id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    selected=True,
                )
                db.add(new_cart)

        db.commit()
        return success(message="已加入购物车")
