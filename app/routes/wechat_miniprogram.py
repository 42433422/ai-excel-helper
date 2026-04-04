# -*- coding: utf-8 -*-
"""
微信小程序 API 路由模块

提供微信小程序相关接口，包括：
- /api/wechat/login: 小程序登录
- /api/wechat/session: 会话管理
"""

import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from functools import wraps
from typing import Any, Dict, Optional

import requests
from flask import Blueprint, current_app, g, jsonify, request
from sqlalchemy import and_

from app.db.models import User
from app.db.session import get_db
from app.auth_decorators import get_current_user, login_required

logger = logging.getLogger(__name__)

wechat_miniprogram_bp = Blueprint("wechat_miniprogram", __name__, url_prefix="/api/wechat")


class WechatMiniProgramError(Exception):
    """微信小程序 API 异常"""
    pass


def get_wechat_config() -> Dict[str, str]:
    """获取微信小程序配置"""
    return {
        "appid": os.environ.get("WECHAT_MINIPROGRAM_APPID", ""),
        "secret": os.environ.get("WECHAT_MINIPROGRAM_SECRET", ""),
    }


def wechat_login_code2session(code: str) -> Dict[str, Any]:
    """
    调用微信 code2Session 接口
    
    Args:
        code: 小程序登录 code
        
    Returns:
        dict: 包含 openid, session_key, unionid 等信息
        
    Raises:
        WechatMiniProgramError: 当微信 API 调用失败时
    """
    config = get_wechat_config()
    
    if not config["appid"] or not config["secret"]:
        raise WechatMiniProgramError("微信小程序配置缺失")
    
    url = "https://api.weixin.qq.com/sns/jscode2session"
    params = {
        "appid": config["appid"],
        "secret": config["secret"],
        "js_code": code,
        "grant_type": "authorization_code",
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        result = response.json()
        
        if "errcode" in result:
            raise WechatMiniProgramError(
                f"微信登录失败：{result.get('errmsg', '未知错误')}"
            )
        
        return {
            "openid": result.get("openid"),
            "session_key": result.get("session_key"),
            "unionid": result.get("unionid"),
        }
    except requests.RequestException as e:
        raise WechatMiniProgramError(f"请求微信 API 失败：{str(e)}")


def generate_jwt_token(user_id: int, openid: str, expires_hours: int = 720) -> str:
    """
    生成 JWT token（简化版，使用 HMAC-SHA256）
    
    Args:
        user_id: 用户 ID
        openid: 微信 openid
        expires_hours: 过期时间（小时），默认 30 天
        
    Returns:
        str: JWT token
    """
    secret_key = current_app.config.get("SECRET_KEY", "default-secret-key")
    
    header = {
        "alg": "HS256",
        "typ": "JWT"
    }
    
    payload = {
        "user_id": user_id,
        "openid": openid,
        "iat": int(time.time()),
        "exp": int(time.time()) + (expires_hours * 3600),
        "jti": uuid.uuid4().hex
    }
    
    def base64url_encode(data: bytes) -> str:
        import base64
        return base64.urlsafe_b64encode(data).rstrip(b'=').decode('utf-8')
    
    header_encoded = base64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    payload_encoded = base64url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
    
    message = f"{header_encoded}.{payload_encoded}"
    signature = hmac.new(
        secret_key.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()
    signature_encoded = base64url_encode(signature)
    
    return f"{header_encoded}.{payload_encoded}.{signature_encoded}"


def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """
    验证 JWT token
    
    Args:
        token: JWT token
        
    Returns:
        dict: payload if valid, None otherwise
    """
    try:
        secret_key = current_app.config.get("SECRET_KEY", "default-secret-key")
        
        parts = token.split('.')
        if len(parts) != 3:
            return None
        
        def base64url_decode(data: str) -> bytes:
            import base64
            padding = '=' * (4 - len(data) % 4)
            return base64.urlsafe_b64decode(data + padding)
        
        header = json.loads(base64url_decode(parts[0]))
        payload = json.loads(base64url_decode(parts[1]))
        signature = base64url_decode(parts[2])
        
        message = f"{parts[0]}.{parts[1]}"
        expected_signature = hmac.new(
            secret_key.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        if not hmac.compare_digest(signature, expected_signature):
            return None
        
        if payload.get("exp", 0) < int(time.time()):
            return None
        
        return payload
    except Exception:
        return None


def miniprogram_auth_required(f):
    """小程序登录验证装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        
        if not auth_header.startswith("Bearer "):
            return jsonify_response(401, "未授权", {"error": "缺少 token"})
        
        token = auth_header[7:].strip()
        payload = verify_jwt_token(token)
        
        if not payload:
            return jsonify_response(401, "token 无效或已过期", {"error": "invalid_token"})
        
        g.current_user_id = payload.get("user_id")
        g.current_openid = payload.get("openid")
        
        return f(*args, **kwargs)
    return decorated_function


def jsonify_response(code: int, message: str, data: Any = None, success: bool = True) -> tuple:
    """
    统一 JSON 响应格式
    
    Args:
        code: 状态码
        message: 消息
        data: 数据
        success: 是否成功
        
    Returns:
        tuple: (response, status_code)
    """
    response_data = {
        "code": code,
        "message": message,
        "success": success,
    }
    
    if data is not None:
        response_data["data"] = data
    
    return jsonify(response_data), code


@wechat_miniprogram_bp.route("/login", methods=["POST"])
def wechat_login():
    """
    微信小程序登录接口
    
    Request Body:
        {
            "code": "微信登录 code"
        }
        
    Response:
        {
            "code": 200,
            "message": "登录成功",
            "success": true,
            "data": {
                "token": "JWT token",
                "user": {
                    "id": 1,
                    "username": "wx_openid_xxx",
                    "display_name": "微信用户",
                    "avatar": "",
                    "created_at": "2024-01-01T00:00:00"
                }
            }
        }
    """
    try:
        data = request.get_json(silent=True) or {}
        code = data.get("code", "").strip()
        
        if not code:
            return jsonify_response(400, "code 不能为空", {"error": "missing_code"})
        
        result = wechat_login_code2session(code)
        openid = result.get("openid")
        
        if not openid:
            return jsonify_response(500, "微信登录失败，未获取到 openid", {"error": "no_openid"})
        
        with get_db() as db:
            user = db.query(User).filter(
                User.username == f"wx_{openid}"
            ).first()
            
            if not user:
                user = User(
                    username=f"wx_{openid}",
                    password=uuid.uuid4().hex,
                    display_name="微信用户",
                    email="",
                    role="user",
                    is_active=True,
                    created_at=datetime.now(),
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            
            user.last_login = datetime.now()
            db.commit()
            
            token = generate_jwt_token(user.id, openid)
            
            return jsonify_response(200, "登录成功", {
                "token": token,
                "expires_in": 720 * 3600,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "display_name": user.display_name,
                    "email": user.email,
                    "role": user.role,
                    "avatar": "",
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                }
            })
            
    except WechatMiniProgramError as e:
        logger.error(f"微信小程序登录失败：{e}")
        return jsonify_response(500, str(e), {"error": "wechat_api_error"})
    except Exception as e:
        logger.error(f"登录接口异常：{e}", exc_info=True)
        return jsonify_response(500, f"登录失败：{str(e)}", {"error": "internal_error"})


@wechat_miniprogram_bp.route("/session/check", methods=["GET"])
@miniprogram_auth_required
def check_session():
    """
    检查会话有效性
    
    Response:
        {
            "code": 200,
            "message": "会话有效",
            "success": true,
            "data": {
                "user_id": 1,
                "openid": "xxx",
                "expires_at": 1234567890
            }
        }
    """
    try:
        auth_header = request.headers.get("Authorization", "")
        token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else ""
        payload = verify_jwt_token(token)
        
        if not payload:
            return jsonify_response(401, "会话已过期", {"error": "session_expired"})
        
        return jsonify_response(200, "会话有效", {
            "user_id": payload.get("user_id"),
            "openid": payload.get("openid"),
            "expires_at": payload.get("exp"),
        })
        
    except Exception as e:
        logger.error(f"检查会话失败：{e}")
        return jsonify_response(500, f"检查失败：{str(e)}", {"error": "internal_error"})


@wechat_miniprogram_bp.route("/user/info", methods=["GET"])
@miniprogram_auth_required
def get_user_info():
    """
    获取用户信息
    
    Response:
        {
            "code": 200,
            "message": "获取成功",
            "success": true,
            "data": {
                "id": 1,
                "username": "wx_openid_xxx",
                "display_name": "微信用户",
                "email": "",
                "role": "user",
                "avatar": "",
                "created_at": "2024-01-01T00:00:00"
            }
        }
    """
    try:
        with get_db() as db:
            user = db.query(User).filter(User.id == g.current_user_id).first()
            
            if not user:
                return jsonify_response(404, "用户不存在", {"error": "user_not_found"})
            
            return jsonify_response(200, "获取成功", {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "email": user.email,
                "role": user.role,
                "avatar": "",
                "created_at": user.created_at.isoformat() if user.created_at else None,
            })
            
    except Exception as e:
        logger.error(f"获取用户信息失败：{e}")
        return jsonify_response(500, f"获取失败：{str(e)}", {"error": "internal_error"})


@wechat_miniprogram_bp.route("/user/info", methods=["PUT"])
@miniprogram_auth_required
def update_user_info():
    """
    更新用户信息
    
    Request Body:
        {
            "display_name": "昵称",
            "avatar": "头像 URL"
        }
        
    Response:
        {
            "code": 200,
            "message": "更新成功",
            "success": true,
            "data": {
                "id": 1,
                "username": "wx_openid_xxx",
                "display_name": "新昵称",
                ...
            }
        }
    """
    try:
        data = request.get_json(silent=True) or {}
        
        with get_db() as db:
            user = db.query(User).filter(User.id == g.current_user_id).first()
            
            if not user:
                return jsonify_response(404, "用户不存在", {"error": "user_not_found"})
            
            if "display_name" in data:
                user.display_name = data["display_name"]
            if "avatar" in data:
                pass
            
            db.commit()
            db.refresh(user)
            
            return jsonify_response(200, "更新成功", {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "email": user.email,
                "role": user.role,
                "avatar": "",
                "created_at": user.created_at.isoformat() if user.created_at else None,
            })
            
    except Exception as e:
        logger.error(f"更新用户信息失败：{e}")
        return jsonify_response(500, f"更新失败：{str(e)}", {"error": "internal_error"})
