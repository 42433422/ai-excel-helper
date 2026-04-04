# -*- coding: utf-8 -*-
"""
小程序认证 API - 微信登录、会话管理
"""
import logging
import os
import uuid

import requests
from datetime import datetime
from flask import Blueprint, current_app, request

from app.db.models import User
from app.db.session import get_db
from app.decorators.mp_auth import generate_jwt_token, mp_auth_required, verify_jwt_token
from app.utils.mp_response import error, success

logger = logging.getLogger(__name__)

mp_auth_bp = Blueprint("mp_auth", __name__, url_prefix="/api/mp/v1/auth")


def get_wechat_config() -> dict:
    return {
        "appid": os.environ.get("WECHAT_MINIPROGRAM_APPID", ""),
        "secret": os.environ.get("WECHAT_MINIPROGRAM_SECRET", ""),
    }


def wechat_login_code2session(code: str) -> dict:
    config = get_wechat_config()
    if not config["appid"] or not config["secret"]:
        raise ValueError("微信小程序配置缺失")

    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": config["appid"],
        "secret": config["secret"],
        "js_code": code,
        "grant_type": "authorization_code",
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    result = response.json()

    if "errcode" in result:
        raise ValueError(f"微信登录失败：{result.get('errmsg', '未知错误')}")

    return {
        "openid": result.get("openid"),
        "session_key": result.get("session_key"),
        "unionid": result.get("unionid"),
    }


@mp_auth_bp.route("/login", methods=["POST"])
def wechat_login():
    data = request.get_json(silent=True) or {}
    code = data.get("code", "").strip()

    if not code:
        return error("code 不能为空", 400, {"error": "missing_code"})

    try:
        result = wechat_login_code2session(code)
        openid = result.get("openid")

        if not openid:
            return error("微信登录失败，未获取到 openid", 500, {"error": "no_openid"})

        with get_db() as db:
            user = db.query(User).filter(User.wx_openid == openid).first()

            if not user:
                user = User(
                    username=f"wx_{openid}",
                    password=uuid.uuid4().hex,
                    display_name="微信用户",
                    email="",
                    role="mp_user",
                    is_active=True,
                    wx_openid=openid,
                    wx_unionid=result.get("unionid"),
                    created_at=datetime.now(),
                )
                db.add(user)
                db.commit()
                db.refresh(user)

            user.last_login = datetime.now()
            db.commit()

            token = generate_jwt_token(user.id, openid)

            return success({
                "token": token,
                "expires_in": 720 * 3600,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "display_name": user.display_name or "微信用户",
                    "avatar": user.wx_avatar_url or "",
                    "role": user.role,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                },
            }, "登录成功")

    except ValueError as e:
        logger.error(f"微信登录失败: {e}")
        return error(str(e), 500, {"error": "wechat_api_error"})
    except Exception as e:
        logger.error(f"登录接口异常: {e}", exc_info=True)
        return error(f"登录失败：{str(e)}", 500, {"error": "internal_error"})


@mp_auth_bp.route("/session/check", methods=["GET"])
@mp_auth_required
def check_session():
    from app.decorators.mp_auth import get_current_mp_user_id, get_current_mp_openid

    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else ""
    payload = verify_jwt_token(token)

    if not payload:
        return error("会话已过期", 401, {"error": "session_expired"})

    return success({
        "user_id": payload.get("user_id"),
        "openid": payload.get("openid"),
        "expires_at": payload.get("exp"),
    })


@mp_auth_bp.route("/logout", methods=["POST"])
@mp_auth_required
def logout():
    return success(message="登出成功")
