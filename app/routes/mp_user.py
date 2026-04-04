# -*- coding: utf-8 -*-
"""
小程序用户信息 API
"""
import logging

from flask import Blueprint, request
from datetime import datetime

from app.db.models import User
from app.db.session import get_db
from app.decorators.mp_auth import mp_auth_required, get_current_mp_user_id
from app.utils.mp_response import error, success

logger = logging.getLogger(__name__)

mp_user_bp = Blueprint("mp_user", __name__, url_prefix="/api/mp/v1/user")


@mp_user_bp.route("/info", methods=["GET"])
@mp_auth_required
def get_user_info():
    user_id = get_current_mp_user_id()
    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return error("用户不存在", 404, {"error": "user_not_found"})

        return success({
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name or "微信用户",
            "nickname": user.mp_nickname or "",
            "avatar": user.wx_avatar_url or "",
            "phone": user.mp_phone or "",
            "email": user.email or "",
            "role": user.role,
            "created_at": user.created_at.isoformat() if user.created_at else None,
        })


@mp_user_bp.route("/info", methods=["PUT"])
@mp_auth_required
def update_user_info():
    user_id = get_current_mp_user_id()
    data = request.get_json(silent=True) or {}

    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return error("用户不存在", 404, {"error": "user_not_found"})

        if "display_name" in data and data["display_name"]:
            user.display_name = data["display_name"]
        if "nickname" in data:
            user.mp_nickname = data["nickname"]
        if "avatar" in data:
            user.wx_avatar_url = data["avatar"]

        db.commit()
        db.refresh(user)

        return success({
            "id": user.id,
            "display_name": user.display_name,
            "nickname": user.mp_nickname,
            "avatar": user.wx_avatar_url or "",
        }, "更新成功")


@mp_user_bp.route("/phone", methods=["POST"])
@mp_auth_required
def update_phone():
    user_id = get_current_mp_user_id()
    data = request.get_json(silent=True) or {}
    phone = data.get("phone", "").strip()

    if not phone:
        return error("手机号不能为空", 400)

    with get_db() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return error("用户不存在", 404)

        user.mp_phone = phone
        db.commit()

        return success({"phone": phone}, "绑定成功")
