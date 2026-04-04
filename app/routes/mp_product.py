# -*- coding: utf-8 -*-
"""
小程序商品 API
"""
import logging

from flask import Blueprint, request

from app.db.models import Product
from app.db.session import get_db
from app.decorators.mp_auth import mp_auth_required, get_current_mp_user_id
from app.utils.mp_response import error, paginate, success

logger = logging.getLogger(__name__)

mp_product_bp = Blueprint("mp_product", __name__, url_prefix="/api/mp/v1/product")


@mp_product_bp.route("/list", methods=["GET"])
def product_list():
    page = max(1, request.args.get("page", 1, type=int))
    page_size = min(100, max(1, request.args.get("page_size", 20, type=int)))
    keyword = request.args.get("keyword", "").strip()
    category = request.args.get("category", "").strip()
    sort_by = request.args.get("sort_by", "newest")

    with get_db() as db:
        query = db.query(Product).filter(Product.is_active == 1)

        if keyword:
            query = query.filter(
                (Product.name.ilike(f"%{keyword}%")) |
                (Product.model_number.ilike(f"%{keyword}%")) |
                (Product.description.ilike(f"%{keyword}%"))
            )
        if category:
            query = query.filter(Product.category == category)

        if sort_by == "price_asc":
            query = query.order_by(Product.price.asc())
        elif sort_by == "price_desc":
            query = query.order_by(Product.price.desc())
        else:
            query = query.order_by(Product.created_at.desc())

        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()

        result = []
        for p in items:
            result.append({
                "id": p.id,
                "name": p.name,
                "model_number": p.model_number or "",
                "specification": p.specification or "",
                "price": float(p.price) if p.price else 0,
                "unit": p.unit or "个",
                "brand": p.brand or "",
                "category": p.category or "",
                "description": (p.description or "")[:200],
            })

        return paginate(result, total, page, page_size)


@mp_product_bp.route("/detail/<int:product_id>", methods=["GET"])
def product_detail(product_id):
    user_id = request.headers.get("X-User-ID", type=int)

    with get_db() as db:
        product = db.query(Product).filter(
            Product.id == product_id,
            Product.is_active == 1,
        ).first()

        if not product:
            return error("商品不存在", 404)

        if user_id:
            from app.db.models import MpBrowseHistory
            from sqlalchemy.dialects.postgresql import insert
            stmt = insert(MpBrowseHistory).values(
                user_id=user_id,
                product_id=product_id,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=["user_id", "product_id"],
                set_={"viewed_at": datetime.now()},
            )
            db.execute(stmt)
            db.commit()

        return success({
            "id": product.id,
            "name": product.name,
            "model_number": product.model_number or "",
            "specification": product.specification or "",
            "price": float(product.price) if product.price else 0,
            "unit": product.unit or "个",
            "quantity": product.quantity or 0,
            "brand": product.brand or "",
            "category": product.category or "",
            "description": product.description or "",
            "created_at": product.created_at.isoformat() if product.created_at else None,
        })


@mp_product_bp.route("/categories", methods=["GET"])
def product_categories():
    with get_db() as db:
        categories = db.query(Product.category).filter(
            Product.category.isnot(None),
            Product.category != "",
            Product.is_active == 1,
        ).distinct().all()

        result = [c[0] for c in categories if c[0]]
        return success(result)


@mp_product_bp.route("/search", methods=["GET"])
def product_search():
    keyword = request.args.get("keyword", "").strip()
    page = max(1, request.args.get("page", 1, type=int))
    page_size = min(50, max(1, request.args.get("page_size", 20, type=int)))

    if not keyword:
        return error("搜索关键词不能为空", 400)

    with get_db() as db:
        query = db.query(Product).filter(Product.is_active == 1)
        query = query.filter(
            (Product.name.ilike(f"%{keyword}%")) |
            (Product.model_number.ilike(f"%{keyword}%")) |
            (Product.specification.ilike(f"%{keyword}%"))
        )
        query = query.order_by(Product.created_at.desc())

        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()

        result = []
        for p in items:
            result.append({
                "id": p.id,
                "name": p.name,
                "model_number": p.model_number or "",
                "specification": p.specification or "",
                "price": float(p.price) if p.price else 0,
                "unit": p.unit or "个",
                "category": p.category or "",
            })

        return paginate(result, total, page, page_size)


@mp_product_bp.route("/price/<int:product_id>", methods=["GET"])
@mp_auth_required
def product_price(product_id):
    with get_db() as db:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return error("商品不存在", 404)

        price_info = {
            "product_id": product.id,
            "product_name": product.name,
            "base_price": float(product.price) if product.price else 0,
            "unit": product.unit or "个",
        }

        try:
            from app.domain.services.pricing_engine import PricingEngine
            engine = PricingEngine(db)
            user_id = get_current_mp_user_id()
            final_price = engine.calculate_price(product_id, user_id)
            if final_price is not None:
                price_info["final_price"] = float(final_price)
        except Exception:
            pass

        return success(price_info)
