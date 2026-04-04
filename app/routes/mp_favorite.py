# -*- coding: utf-8 -*-
"""
小程序收藏 API
"""
import logging

from flask import Blueprint, request

from app.db.models import MpFavorite, Product
from app.db.session import get_db
from app.decorators.mp_auth import mp_auth_required, get_current_mp_user_id
from app.utils.mp_response import error, paginate, success

logger = logging.getLogger(__name__)

mp_favorite_bp = Blueprint("mp_favorite", __name__, url_prefix="/api/mp/v1/favorite")


@mp_favorite_bp.route("/list", methods=["GET"])
@mp_auth_required
def favorite_list():
    user_id = get_current_mp_user_id()
    page = max(1, request.args.get("page", 1, type=int))
    page_size = min(50, max(1, request.args.get("page_size", 20, type=int)))

    with get_db() as db:
        query = (
            db.query(MpFavorite)
            .filter(MpFavorite.user_id == user_id)
            .order_by(MpFavorite.created_at.desc())
        )
        total = query.count()
        favorites = query.offset((page - 1) * page_size).limit(page_size).all()

        items = []
        for fav in favorites:
            product = db.query(Product).filter(Product.id == fav.product_id).first()
            if product and product.is_active == 1:
                items.append({
                    "fav_id": fav.id,
                    "product_id": product.id,
                    "product_name": product.name,
                    "price": float(product.price) if product.price else 0,
                    "unit": product.unit or "个",
                    "created_at": fav.created_at.isoformat() if fav.created_at else None,
                })

        return paginate(items, total, page, page_size)


@mp_favorite_bp.route("/add", methods=["POST"])
@mp_auth_required
def favorite_add():
    user_id = get_current_mp_user_id()
    data = request.get_json(silent=True) or {}
    product_id = data.get("product_id")

    if not product_id:
        return error("商品ID不能为空", 400)

    with get_db() as db:
        product = db.query(Product).filter(
            Product.id == product_id,
            Product.is_active == 1,
        ).first()
        if not product:
            return error("商品不存在", 404)

        existing = db.query(MpFavorite).filter(
            MpFavorite.user_id == user_id,
            MpFavorite.product_id == product_id,
        ).first()

        if existing:
            return success(message="已收藏")

        new_fav = MpFavorite(user_id=user_id, product_id=product_id)
        db.add(new_fav)
        db.commit()

        return success({"fav_id": new_fav.id}, "收藏成功")


@mp_favorite_bp.route("/remove/<int:fav_id>", methods=["DELETE"])
@mp_auth_required
def favorite_remove(fav_id):
    user_id = get_current_mp_user_id()
    with get_db() as db:
        deleted = db.query(MpFavorite).filter(
            MpFavorite.id == fav_id,
            MpFavorite.user_id == user_id,
        ).delete()

        if not deleted:
            return error("收藏记录不存在", 404)

        db.commit()
        return success(message="取消收藏成功")


@mp_favorite_bp.route("/check/<int:product_id>", methods=["GET"])
@mp_auth_required
def favorite_check(product_id):
    user_id = get_current_mp_user_id()
    with get_db() as db:
        fav = db.query(MpFavorite).filter(
            MpFavorite.user_id == user_id,
            MpFavorite.product_id == product_id,
        ).first()

        return success({
            "is_favorited": fav is not None,
            "fav_id": fav.id if fav else None,
        })
