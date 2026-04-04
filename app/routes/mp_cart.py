# -*- coding: utf-8 -*-
"""
小程序购物车 API
"""
import logging

from flask import Blueprint, request

from app.db.models import MpCart, Product
from app.db.session import get_db
from app.decorators.mp_auth import mp_auth_required, get_current_mp_user_id
from app.utils.mp_response import error, success

logger = logging.getLogger(__name__)

mp_cart_bp = Blueprint("mp_cart", __name__, url_prefix="/api/mp/v1/cart")


@mp_cart_bp.route("/list", methods=["GET"])
@mp_auth_required
def cart_list():
    user_id = get_current_mp_user_id()
    with get_db() as db:
        carts = (
            db.query(MpCart)
            .filter(MpCart.user_id == user_id)
            .order_by(MpCart.created_at.desc())
            .all()
        )

        items = []
        total_amount = 0.0
        selected_count = 0

        for cart in carts:
            product = db.query(Product).filter(Product.id == cart.product_id).first()
            if not product or product.is_active != 1:
                continue

            unit_price = float(product.price) if product.price else 0
            subtotal = round(unit_price * cart.quantity, 2)
            item = {
                "cart_id": cart.id,
                "product_id": product.id,
                "product_name": product.name,
                "model_number": product.model_number or "",
                "specification": product.specification or "",
                "unit_price": unit_price,
                "quantity": cart.quantity,
                "selected": cart.selected,
                "subtotal": subtotal,
                "unit": product.unit or "个",
            }
            items.append(item)

            if cart.selected:
                total_amount += subtotal
                selected_count += cart.quantity

        return success({
            "items": items,
            "summary": {
                "total_amount": round(total_amount, 2),
                "selected_count": selected_count,
                "total_types": len(items),
            },
        })


@mp_cart_bp.route("/add", methods=["POST"])
@mp_auth_required
def cart_add():
    user_id = get_current_mp_user_id()
    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    quantity = max(1, data.get("quantity", 1))

    if not product_id:
        return error("商品ID不能为空", 400)

    with get_db() as db:
        product = db.query(Product).filter(
            Product.id == product_id,
            Product.is_active == 1,
        ).first()

        if not product:
            return error("商品不存在", 404)

        existing = db.query(MpCart).filter(
            MpCart.user_id == user_id,
            MpCart.product_id == product_id,
        ).first()

        if existing:
            existing.quantity += quantity
        else:
            existing = MpCart(
                user_id=user_id,
                product_id=product_id,
                quantity=quantity,
                selected=True,
            )
            db.add(existing)

        db.commit()

        return success({"cart_id": existing.id}, "添加成功")


@mp_cart_bp.route("/update", methods=["PUT"])
@mp_auth_required
def cart_update():
    user_id = get_current_mp_user_id()
    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    quantity = data.get("quantity")

    if not product_id:
        return error("商品ID不能为空", 400)
    if quantity is None or quantity < 1:
        return error("数量必须大于0", 400)

    with get_db() as db:
        cart = db.query(MpCart).filter(
            MpCart.user_id == user_id,
            MpCart.product_id == product_id,
        ).first()

        if not cart:
            return error("购物车中不存在该商品", 404)

        cart.quantity = quantity
        db.commit()

        return success(message="更新成功")


@mp_cart_bp.route("/remove", methods=["DELETE"])
@mp_auth_required
def cart_remove():
    user_id = get_current_mp_user_id()
    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")

    if not product_id:
        return error("商品ID不能为空", 400)

    with get_db() as db:
        deleted = db.query(MpCart).filter(
            MpCart.user_id == user_id,
            MpCart.product_id == product_id,
        ).delete()

        if deleted == 0:
            return error("购物车中不存在该商品", 404)

        db.commit()
        return success(message="删除成功")


@mp_cart_bp.route("/select", methods=["PUT"])
@mp_auth_required
def cart_select():
    user_id = get_current_mp_user_id()
    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")
    selected = data.get("selected", True)

    if not product_id:
        return error("商品ID不能为空", 400)

    with get_db() as db:
        cart = db.query(MpCart).filter(
            MpCart.user_id == user_id,
            MpCart.product_id == product_id,
        ).first()

        if not cart:
            return error("购物车中不存在该商品", 404)

        cart.selected = bool(selected)
        db.commit()

        return success(message="操作成功")


@mp_cart_bp.route("/clear", methods=["DELETE"])
@mp_auth_required
def cart_clear():
    user_id = get_current_mp_user_id()
    with get_db() as db:
        db.query(MpCart).filter(MpCart.user_id == user_id).delete()
        db.commit()
        return success(message="购物车已清空")
