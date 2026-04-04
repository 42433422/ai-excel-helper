from functools import wraps
from typing import Any, Callable, List, Optional

from flask import current_app, g, jsonify, request

from app.db.models import User
from app.services import get_auth_service, get_session_service

_session_service = None
_auth_service = None


def _get_session_service():
    global _session_service
    if _session_service is None:
        _session_service = get_session_service()
    return _session_service


def _get_auth_service():
    global _auth_service
    if _auth_service is None:
        _auth_service = get_auth_service()
    return _auth_service


def get_current_user() -> Optional[User]:
    return getattr(g, 'current_user', None)


def get_current_session_id() -> Optional[str]:
    return getattr(g, 'session_id', None)


def login_required(f: Callable) -> Callable:
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any):
        session_id = _extract_session_id()
        if not session_id:
            return jsonify({
                "success": False,
                "error": {"code": "UNAUTHORIZED", "message": "请先登录"}
            }), 401

        session_service = _get_session_service()
        user = session_service.validate_session(session_id)
        if not user:
            return jsonify({
                "success": False,
                "error": {"code": "SESSION_EXPIRED", "message": "会话已过期，请重新登录"}
            }), 401

        if not user.is_active:
            return jsonify({
                "success": False,
                "error": {"code": "ACCOUNT_DISABLED", "message": "账户已被禁用"}
            }), 403

        g.current_user = user
        g.session_id = session_id
        return f(*args, **kwargs)
    return decorated_function


def role_required(roles: List[str]) -> Callable:
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any):
            user = get_current_user()
            if not user:
                return jsonify({
                    "success": False,
                    "error": {"code": "UNAUTHORIZED", "message": "请先登录"}
                }), 401

            if user.role not in roles and user.role != "admin":
                return jsonify({
                    "success": False,
                    "error": {"code": "FORBIDDEN", "message": "权限不足"}
                }), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def permission_required(permission_code: str) -> Callable:
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any):
            user = get_current_user()
            if not user:
                return jsonify({
                    "success": False,
                    "error": {"code": "UNAUTHORIZED", "message": "请先登录"}
                }), 401

            auth_service = _get_auth_service()
            if not auth_service.has_permission(user, permission_code):
                return jsonify({
                    "success": False,
                    "error": {"code": "FORBIDDEN", "message": "权限不足"}
                }), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def _extract_session_id() -> Optional[str]:
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]

    cookie_name = current_app.config.get("SESSION_COOKIE_NAME", "session_id")
    return request.cookies.get(cookie_name)
