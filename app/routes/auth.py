from flask import Blueprint, current_app, g, jsonify, request

from app.application import get_auth_app_service, get_user_app_service
from app.auth_decorators import (
    get_current_session_id,
    get_current_user,
    login_required,
    permission_required,
    role_required,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
users_bp = Blueprint("users", __name__, url_prefix="/api/users")


def _extract_session_id() -> str:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    cookie_name = current_app.config.get("SESSION_COOKIE_NAME", "session_id")
    return (request.cookies.get(cookie_name) or "").strip()


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({
            "success": False,
            "error": {"code": "INVALID_INPUT", "message": "用户名和密码不能为空"}
        }), 400

    auth_app_service = get_auth_app_service()
    result = auth_app_service.login(username, password)

    if not result["success"]:
        return jsonify(result), 401

    response = jsonify(result)
    session_id = result.get("session_id")
    if session_id:
        response.set_cookie(
            current_app.config.get("SESSION_COOKIE_NAME", "session_id"),
            session_id,
            max_age=current_app.config.get("SESSION_COOKIE_MAX_AGE", 86400),
            httponly=bool(current_app.config.get("SESSION_COOKIE_HTTPONLY", True)),
            secure=bool(current_app.config.get("SESSION_COOKIE_SECURE", False)),
            samesite=current_app.config.get("SESSION_COOKIE_SAMESITE", "Lax"),
            path="/",
        )
    return response


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    session_id = get_current_session_id()
    if not session_id:
        return jsonify({
            "success": False,
            "error": {"code": "NO_SESSION", "message": "无有效会话"}
        }), 400

    auth_app_service = get_auth_app_service()
    result = auth_app_service.logout(session_id)

    response = jsonify(result)
    response.delete_cookie(
        current_app.config.get("SESSION_COOKIE_NAME", "session_id"),
        path="/",
    )
    return response


@auth_bp.route("/me", methods=["GET"])
@login_required
def get_me():
    user = get_current_user()
    auth_app_service = get_auth_app_service()
    permissions = auth_app_service.get_user_permissions(user)

    return jsonify({
        "success": True,
        "data": {
            "user": {
                "id": user.id,
                "username": user.username,
                "display_name": user.display_name,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active
            },
            "permissions": permissions
        }
    })


@auth_bp.route("/session/validate", methods=["GET"])
def validate_session():
    session_id = _extract_session_id()
    if not session_id:
        return jsonify({
            "success": False,
            "valid": False,
            "error": {"code": "NO_SESSION", "message": "无会话信息"}
        }), 401

    auth_app_service = get_auth_app_service()
    session_info = auth_app_service.session_manager.get_session_info(session_id)

    if not session_info:
        return jsonify({
            "success": False,
            "valid": False,
            "error": {"code": "INVALID_SESSION", "message": "会话无效或已过期"}
        }), 401

    return jsonify({
        "success": True,
        "valid": True,
        "data": session_info
    })


@auth_bp.route("/password/change", methods=["POST"])
@login_required
def change_password():
    data = request.get_json(silent=True) or {}
    old_password = data.get("old_password", "")
    new_password = data.get("new_password", "")

    if not old_password or not new_password:
        return jsonify({
            "success": False,
            "error": {"code": "INVALID_INPUT", "message": "请填写完整信息"}
        }), 400

    if len(new_password) < 6:
        return jsonify({
            "success": False,
            "error": {"code": "WEAK_PASSWORD", "message": "新密码至少 6 个字符"}
        }), 400

    user = get_current_user()
    auth_app_service = get_auth_app_service()
    result = auth_app_service.change_password(user.id, old_password, new_password)

    if not result["success"]:
        return jsonify(result), 400

    return jsonify(result)


@users_bp.route("", methods=["GET"])
@login_required
@permission_required("admin.manage_users")
def list_users():
    include_inactive = request.args.get("include_inactive", "false").lower() == "true"
    user_service = get_user_app_service()
    users = user_service.list_users(skip=0, limit=100)

    if not include_inactive:
        users = [u for u in users if u.get("is_active", True)]

    return jsonify({
        "success": True,
        "data": {"users": users, "count": len(users)}
    })


@users_bp.route("", methods=["POST"])
@login_required
@permission_required("admin.manage_users")
def create_user():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    display_name = data.get("display_name", "")
    email = data.get("email", "")
    role = data.get("role", "viewer")

    if not username or not password:
        return jsonify({
            "success": False,
            "error": {"code": "INVALID_INPUT", "message": "用户名和密码不能为空"}
        }), 400

    if len(password) < 6:
        return jsonify({
            "success": False,
            "error": {"code": "WEAK_PASSWORD", "message": "密码至少6个字符"}
        }), 400

    if role not in ["viewer", "operator", "admin"]:
        return jsonify({
            "success": False,
            "error": {"code": "INVALID_ROLE", "message": "无效的角色"}
        }), 400

    user_service = get_user_app_service()
    result = user_service.create_user(
        username=username,
        password=password,
        display_name=display_name,
        email=email,
        role=role
    )

    if not result["success"]:
        return jsonify({
            "success": False,
            "error": {"code": "CREATE_FAILED", "message": result["error"]}
        }), 400

    return jsonify({
        "success": True,
        "data": {"user": result["user"]}
    }), 201


@users_bp.route("/<int:user_id>", methods=["GET"])
@login_required
@permission_required("admin.manage_users")
def get_user(user_id: int):
    user_service = get_user_app_service()
    user = user_service.get_user(user_id)

    if not user:
        return jsonify({
            "success": False,
            "error": {"code": "NOT_FOUND", "message": "用户不存在"}
        }), 404

    return jsonify({
        "success": True,
        "data": {"user": user}
    })


@users_bp.route("/<int:user_id>", methods=["PUT"])
@login_required
@permission_required("admin.manage_users")
def update_user(user_id: int):
    data = request.get_json(silent=True) or {}
    display_name = data.get("display_name")
    email = data.get("email")
    role = data.get("role")
    is_active = data.get("is_active")

    if role and role not in ["viewer", "operator", "admin"]:
        return jsonify({
            "success": False,
            "error": {"code": "INVALID_ROLE", "message": "无效的角色"}
        }), 400

    user_service = get_user_app_service()
    result = user_service.update_user(
        user_id=user_id,
        display_name=display_name,
        email=email,
        role=role,
        is_active=is_active
    )

    if not result["success"]:
        return jsonify({
            "success": False,
            "error": {"code": "UPDATE_FAILED", "message": result["error"]}
        }), 400

    return jsonify({
        "success": True,
        "data": {"user": result["user"]}
    })


@users_bp.route("/<int:user_id>", methods=["DELETE"])
@login_required
@permission_required("admin.manage_users")
def delete_user(user_id: int):
    current_user = get_current_user()
    if current_user.id == user_id:
        return jsonify({
            "success": False,
            "error": {"code": "SELF_DELETE", "message": "不能删除自己"}
        }), 400

    user_service = get_user_app_service()
    result = user_service.delete_user(user_id)

    if not result["success"]:
        return jsonify(result), 400

    return jsonify(result)


@users_bp.route("/<int:user_id>/reset-password", methods=["POST"])
@login_required
@permission_required("admin.manage_users")
def reset_user_password(user_id: int):
    data = request.get_json(silent=True) or {}
    new_password = data.get("new_password", "admin123")

    if len(new_password) < 6:
        return jsonify({
            "success": False,
            "error": {"code": "WEAK_PASSWORD", "message": "密码至少6个字符"}
        }), 400

    auth_app_service = get_auth_app_service()
    result = auth_app_service.reset_password(user_id, new_password)

    if not result["success"]:
        return jsonify(result), 400

    return jsonify(result)
