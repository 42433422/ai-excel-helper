"""
微信小程序：兼容导出（仅符号再导出，无 HTTP 路由）。

HTTP 由 FastAPI 路由（``legacy_gaps_batch1/2``）提供；此处仅保留归档/脚本可用的符号。
"""

from __future__ import annotations

from app.application.facades.wechat_facade import (
    WechatMiniProgramError,
    get_wechat_config,
    miniprogram_login_data_for_wx_username_binding,
    wechat_login_code2session,
)
from app.decorators.mp_auth import (
    get_current_mp_user_id,
    mp_auth_required,
    verify_jwt_token,
)
from app.http.wechat_miniprogram_responses import jsonify_response

miniprogram_auth_required = mp_auth_required

__all__ = [
    "WechatMiniProgramError",
    "get_current_mp_user_id",
    "get_wechat_config",
    "jsonify_response",
    "miniprogram_auth_required",
    "miniprogram_login_data_for_wx_username_binding",
    "mp_auth_required",
    "verify_jwt_token",
    "wechat_login_code2session",
]
