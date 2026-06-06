"""
微信小程序：code2Session 与本地用户绑定。

供小程序相关 FastAPI 路由与 ``app.routes.wechat_miniprogram`` 导出符号共用，
避免从 routes 互相导入。
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Any

import requests

from app.db.models import User
from app.db.session import get_db
from app.decorators.mp_auth import generate_jwt_token


class WechatMiniProgramError(Exception):
    """微信小程序 API 或配置错误。"""


def get_wechat_config() -> dict[str, str]:
    return {
        "appid": os.environ.get("WECHAT_MINIPROGRAM_APPID", ""),
        "secret": os.environ.get("WECHAT_MINIPROGRAM_SECRET", ""),
    }


def wechat_login_code2session(code: str) -> dict[str, Any]:
    """
    调用微信 jscode2session。

    Raises:
        WechatMiniProgramError: 配置缺失、HTTP 失败或微信返回 errcode。
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
            raise WechatMiniProgramError(f"微信登录失败：{result.get('errmsg', '未知错误')}")
        return {
            "openid": result.get("openid"),
            "session_key": result.get("session_key"),
            "unionid": result.get("unionid"),
        }
    except requests.RequestException as e:
        raise WechatMiniProgramError(f"请求微信 API 失败：{str(e)}") from e


def miniprogram_login_data_for_wx_username_binding(code: str) -> dict[str, Any]:
    """
    与历史 ``/api/wechat/login`` 行为一致：按 ``wx_{openid}`` 绑定 ``User.username``，
    返回成功时的 data 字段（token / expires_in / user）。
    """
    code = (code or "").strip()
    if not code:
        raise ValueError("missing_code")

    result = wechat_login_code2session(code)
    openid = result.get("openid")
    if not openid:
        raise WechatMiniProgramError("微信登录失败，未获取到 openid")

    with get_db() as db:
        user = db.query(User).filter(User.wx_openid == openid).first()
        if not user:
            user = db.query(User).filter(User.username == f"wx_{openid}").first()
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
        elif not getattr(user, "wx_openid", None):
            user.wx_openid = openid
            if result.get("unionid"):
                user.wx_unionid = result.get("unionid")
            db.commit()

        user.last_login = datetime.now()
        db.commit()

        token = generate_jwt_token(user.id, openid)
        return {
            "token": token,
            "expires_in": 720 * 3600,
            "user": {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name or "微信用户",
                "email": user.email,
                "role": user.role,
                "avatar": getattr(user, "wx_avatar_url", None) or "",
                "created_at": user.created_at.isoformat() if user.created_at else None,
            },
        }
