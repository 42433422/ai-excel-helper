# -*- coding: utf-8 -*-
"""
小程序地址管理 API
"""
import logging

from flask import Blueprint, request

from app.db.models import MpAddress
from app.db.session import get_db
from app.decorators.mp_auth import mp_auth_required, get_current_mp_user_id
from app.utils.mp_response import error, success

logger = logging.getLogger(__name__)

mp_address_bp = Blueprint("mp_address", __name__, url_prefix="/api/mp/v1/address")


@mp_address_bp.route("/list", methods=["GET"])
@mp_auth_required
def address_list():
    user_id = get_current_mp_user_id()
    with get_db() as db:
        addresses = (
            db.query(MpAddress)
            .filter(MpAddress.user_id == user_id)
            .order_by(MpAddress.is_default.desc(), MpAddress.created_at.desc())
            .all()
        )

        result = []
        for addr in addresses:
            result.append({
                "id": addr.id,
                "contact_name": addr.contact_name,
                "contact_phone": addr.contact_phone,
                "province": addr.province,
                "city": addr.city,
                "district": addr.district,
                "detail_address": addr.detail_address,
                "full_address": f"{addr.province}{addr.city}{addr.district}{addr.detail_address}",
                "is_default": addr.is_default,
            })

        return success(result)


@mp_address_bp.route("/create", methods=["POST"])
@mp_auth_required
def address_create():
    user_id = get_current_mp_user_id()
    data = request.get_json(silent=True) or {}

    required_fields = ["contact_name", "contact_phone", "province", "city", "district", "detail_address"]
    for field in required_fields:
        if not data.get(field):
            return error(f"{field} 不能为空", 400)

    with get_db() as db:
        is_default = data.get("is_default", False)

        if is_default:
            db.query(MpAddress).filter(
                MpAddress.user_id == user_id,
            ).update({"is_default": False})

        count = db.query(MpAddress).filter(MpAddress.user_id == user_id).count()
        if count == 0:
            is_default = True

        address = MpAddress(
            user_id=user_id,
            contact_name=data["contact_name"],
            contact_phone=data["contact_phone"],
            province=data["province"],
            city=data["city"],
            district=data["district"],
            detail_address=data["detail_address"],
            is_default=is_default,
        )
        db.add(address)
        db.commit()
        db.refresh(address)

        return success({
            "id": address.id,
            "is_default": address.is_default,
        }, "地址添加成功")


@mp_address_bp.route("/update/<int:address_id>", methods=["PUT"])
@mp_auth_required
def address_update(address_id):
    user_id = get_current_mp_user_id()
    data = request.get_json(silent=True) or {}

    with get_db() as db:
        address = db.query(MpAddress).filter(
            MpAddress.id == address_id,
            MpAddress.user_id == user_id,
        ).first()

        if not address:
            return error("地址不存在", 404)

        updatable = ["contact_name", "contact_phone", "province", "city", "district", "detail_address"]
        for field in updatable:
            if field in data and data[field]:
                setattr(address, field, data[field])

        if data.get("is_default") and not address.is_default:
            db.query(MpAddress).filter(
                MpAddress.user_id == user_id,
                MpAddress.id != address_id,
            ).update({"is_default": False})
            address.is_default = True

        db.commit()
        return success(message="地址更新成功")


@mp_address_bp.route("/delete/<int:address_id>", methods=["DELETE"])
@mp_auth_required
def address_delete(address_id):
    user_id = get_current_mp_user_id()
    with get_db() as db:
        address = db.query(MpAddress).filter(
            MpAddress.id == address_id,
            MpAddress.user_id == user_id,
        ).first()

        if not address:
            return error("地址不存在", 404)

        db.delete(address)
        db.commit()
        return success(message="地址删除成功")


@mp_address_bp.route("/default/<int:address_id>", methods=["PUT"])
@mp_auth_required
def address_set_default(address_id):
    user_id = get_current_mp_user_id()
    with get_db() as db:
        address = db.query(MpAddress).filter(
            MpAddress.id == address_id,
            MpAddress.user_id == user_id,
        ).first()

        if not address:
            return error("地址不存在", 404)

        db.query(MpAddress).filter(
            MpAddress.user_id == user_id,
        ).update({"is_default": False})

        address.is_default = True
        db.commit()

        return success(message="默认地址设置成功")
