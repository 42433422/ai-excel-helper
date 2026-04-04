"""
统一安全中间件

提供组合式安全装饰器，将认证、限流、权限校验、输入验证
合并为单一声明式接口，确保所有 API 端点都有一致的安全策略。
"""

from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Set

from flask import g, jsonify, request

from app.auth_decorators import login_required
from app.utils.rate_limiter import check_rate_limit


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Cache-Control": "no-store",
    "Pragma": "no-cache",
}


def _apply_security_headers(response):
    for header, value in SECURITY_HEADERS.items():
        if header not in response.headers:
            response.headers[header] = value
    return response


def api_security(
    auth: bool = True,
    permissions: Optional[List[str]] = None,
    roles: Optional[List[str]] = None,
    rate_limit: Optional[Dict[str, int]] = None,
    validate_json: bool = False,
) -> Callable:
    """
    统一 API 安全装饰器 — 一站式声明安全策略。

    Args:
        auth: 是否需要登录认证（默认 True）
        permissions: 需要的权限码列表（如 ["product.edit", "shipment.create"]）
        roles: 需要的角色列表（如 ["admin", "operator"]）
        rate_limit: 限流配置 {"max_requests": 60, "window_seconds": 60}，None 表示不限
        validate_json: 是否校验请求体为合法 JSON

    使用示例:

        @api_security(permissions=["product.view"], rate_limit={"max_requests": 30, "window_seconds": 60})
        def get_products():
            ...

        @api_security(auth=False, rate_limit={"max_requests": 10, "window_seconds": 60})
        def public_endpoint():
            ...
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def secured_function(*args: Any, **kwargs: Any):
            if validate_json and request.is_json:
                try:
                    request.get_json(force=True)
                except Exception:
                    return jsonify({
                        "success": False,
                        "error": {"code": "INVALID_JSON", "message": "请求体不是合法 JSON"}
                    }), 400

            if rate_limit:
                user_id = getattr(g, 'current_user', None)
                user_key = str(user_id.id) if user_id else request.remote_addr
                endpoint = f"{request.method}:{request.endpoint}"
                result = check_rate_limit(
                    user_id=user_key,
                    endpoint=endpoint,
                    max_requests=rate_limit.get("max_requests", 100),
                    window_seconds=rate_limit.get("window_seconds", 60),
                )
                if not result["allowed"]:
                    response = jsonify({
                        "success": False,
                        "error": {"code": "RATE_LIMITED", "message": "请求过于频繁，请稍后重试"}
                    })
                    response.status_code = 429
                    if result.get("retry_after"):
                        response.headers["Retry-After"] = str(result["retry_after"])
                    return _apply_security_headers(response)

            if auth:
                def _noop(*a, **k):
                    return None
                auth_check = login_required(_noop)
                auth_result = auth_check()
                if auth_result is not None:
                    if isinstance(auth_result, tuple):
                        return _apply_security_headers(auth_result[0]), auth_result[1]
                    return _apply_security_headers(auth_result)

                actual_login_required = login_required(f)

                if roles:
                    from app.auth_decorators import role_required
                    actual_login_required = role_required(roles)(actual_login_required)

                if permissions:
                    from app.auth_decorators import permission_required
                    for perm in permissions:
                        actual_login_required = permission_required(perm)(actual_login_required)

                result = actual_login_required(*args, **kwargs)
                if isinstance(result, tuple):
                    response = result[0]
                    response = _apply_security_headers(response)
                    return response, result[1]
                return _apply_security_headers(result)

            response = f(*args, **kwargs)
            if isinstance(response, tuple):
                resp_obj = response[0]
                resp_obj = _apply_security_headers(resp_obj)
                return (resp_obj, response[1]) if len(response) > 1 else resp_obj
            return _apply_security_headers(response)

        return secured_function
    return decorator


def require_permissions(*perms: str) -> Callable:
    """快捷装饰器：要求指定权限。等价于 api_security(permissions=list(perms))"""
    return api_security(permissions=list(perms))


def public_api(rate_limit: Optional[Dict[str, int]] = None) -> Callable:
    """快捷装饰器：公开 API（无需认证），可配置限流。"""
    return api_security(auth=False, rate_limit=rate_limit)


def admin_only() -> Callable:
    """快捷装饰器：仅管理员可访问。"""
    return api_security(roles=["admin"], permissions=["admin.system_config"])


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """
    输入清洗：截断超长文本，移除危险字符。

    注意：这不是 XSS 防护的替代品，前端和输出时仍需转义。
    此函数主要防止存储层异常（如超长字符串导致数据库错误）。
    """
    if not isinstance(text, str):
        return str(text)[:max_length]
    text = text[:max_length]
    return text.strip()


class PermissionMatrix:
    """
    权限矩阵：集中管理端点→权限映射。

    用途：
    - 统一查看所有受保护端点及其所需权限
    - 动态生成前端权限控制数据
    - 安全审计时快速定位权限覆盖范围
    """

    _rules: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register(cls, endpoint: str, method: str, permissions: List[str] = None,
                 roles: List[str] = None, auth: bool = True, description: str = ""):
        key = f"{method.upper()}:{endpoint}"
        cls._rules[key] = {
            "endpoint": endpoint,
            "method": method.upper(),
            "permissions": permissions or [],
            "roles": roles or [],
            "auth": auth,
            "description": description,
        }

    @classmethod
    def get_all_rules(cls) -> Dict[str, Dict[str, Any]]:
        return dict(cls._rules)

    @classmethod
    def get_endpoints_for_permission(cls, permission_code: str) -> List[str]:
        return [
            f"{r['method']} {r['endpoint']}"
            for r in cls._rules.values()
            if permission_code in r["permissions"]
        ]

    @classmethod
    def check(cls, endpoint: str, method: str, user_roles: Set[str],
              user_permissions: Set[str]) -> Dict[str, Any]:
        key = f"{method.upper()}:{endpoint}"
        rule = cls._rules.get(key)
        if not rule:
            return {"allowed": True, "reason": "未注册端点，默认放行"}

        if rule["auth"] and not user_roles:
            return {"allowed": False, "reason": "需要认证"}

        required_roles = set(rule["roles"])
        required_perms = set(rule["permissions"])

        if required_roles and not (required_roles & user_roles):
            return {"allowed": False, "reason": f"需要角色: {required_roles}"}

        if required_perms and not (required_perms & user_permissions):
            return {"allowed": False, "reason": f"需要权限: {required_perms}"}

        return {"allowed": True, "reason": "OK"}


def register_default_permissions():
    """注册系统默认端点权限矩阵。"""
    pm = PermissionMatrix

    customer_perms = ["customer.view", "customer.edit"]
    product_perms = ["product.view", "product.edit"]
    shipment_perms = ["shipment.view", "shipment.create", "shipment.edit"]
    material_perms = ["material.view", "material.edit"]
    admin_perms = ["admin.manage_users", "admin.system_config"]

    endpoints = [
        ("GET", "/api/customers", customer_perms[:1], None, "客户列表"),
        ("POST", "/api/customers", [customer_perms[1]], None, "创建客户"),
        ("PUT", "/api/customers/<id>", [customer_perms[1]], None, "编辑客户"),
        ("GET", "/api/products", product_perms[:1], None, "产品列表"),
        ("POST", "/api/products", [product_perms[1]], None, "创建产品"),
        ("PUT", "/api/products/<id>", [product_perms[1]], None, "编辑产品"),
        ("GET", "/api/shipments", shipment_perms[:1], None, "出货单列表"),
        ("POST", "/api/shipments", [shipment_perms[1]], None, "创建出货单"),
        ("PUT", "/api/shipments/<id>", [shipment_perms[2]], None, "编辑出货单"),
        ("POST", "/api/shipments/<id>/approve", shipment_perms[2:] + ["shipment.approve"],
         ["admin"], "审批出货单"),
        ("GET", "/api/materials", material_perms[:1], None, "物料列表"),
        ("POST", "/api/materials", [material_perms[1]], None, "创建物料"),
        ("PUT", "/api/materials/<id>", [material_perms[1]], None, "编辑物料"),
        ("POST", "/api/print/label", ["print.label"], None, "标签打印"),
        ("GET", "/api/users", admin_perms[:1], ["admin"], "用户列表"),
        ("POST", "/api/users", [admin_perms[0]], ["admin"], "创建用户"),
        ("PUT", "/api/users/<id>", [admin_perms[0]], ["admin"], "编辑用户"),
        ("GET", "/api/system/config", [admin_perms[1]], ["admin"], "系统配置"),
        ("POST", "/api/ai/chat", None, None, "AI 对话"),
        ("GET", "/api/intent", None, None, "意图识别"),
    ]

    for method, path, perms, roles, desc in endpoints:
        pm.register(path, method, perms, roles, description=desc)


register_default_permissions()
