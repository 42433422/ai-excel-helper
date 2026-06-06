"""
权限/角色管理 API 路由 (RBAC)

提供角色和权限的 CRUD、用户-角色分配，以及权限定义的扩展。
现有用户 CRUD 保留在 legacy_auth.py (/api/users)。

端点前缀：/api/rbac
需要：admin.manage_users 权限（管理员专用）。
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from app.application.rbac_app_service import get_rbac_app_service
from app.errors import AppError
from app.infrastructure.auth.dependencies import require_permission
from app.infrastructure.auth.tenant_context import resolve_tenant_id
from app.schemas.rbac_schema import PermissionCreate, RoleCreate, RoleUpdate, UserRoleAssign

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rbac", tags=["rbac"])

_require_admin = require_permission("admin.manage_users")


def _handle_app_error(err: AppError) -> JSONResponse:
    return JSONResponse(
        {"success": False, "message": err.message, "error_code": err.code.value},
        status_code=err.status_code,
    )


# ── 角色管理 ─────────────────────────────────────────────────────


@router.get("/tenants")
def rbac_tenants_list(_user=Depends(_require_admin)):
    """列出活跃租户（平台管理员）。"""
    return {"success": True, "data": get_rbac_app_service().list_tenants()}


@router.get("/tenants/{tenant_id}/data-scopes")
def rbac_tenant_data_scopes(tenant_id: int, _user=Depends(_require_admin)):
    return {"success": True, "data": get_rbac_app_service().list_data_scopes(tenant_id)}


@router.get("/roles")
def rbac_roles_list(request: Request, _user=Depends(_require_admin)):
    """列出所有角色及其权限列表。"""
    tenant_id = resolve_tenant_id(request)
    return {"success": True, "data": get_rbac_app_service().list_roles(tenant_id=tenant_id)}


@router.get("/roles/{role_id}")
def rbac_role_get(role_id: int, _user=Depends(_require_admin)):
    try:
        return {"success": True, "data": get_rbac_app_service().get_role(role_id)}
    except AppError as exc:
        return _handle_app_error(exc)


@router.post("/roles")
def rbac_role_create(body: RoleCreate, request: Request, _user=Depends(_require_admin)):
    """创建自定义角色。"""
    try:
        data = get_rbac_app_service().create_role(
            body.name,
            body.description,
            body.permissions,
            tenant_id=resolve_tenant_id(request),
        )
        return JSONResponse({"success": True, "data": data}, status_code=201)
    except AppError as exc:
        return _handle_app_error(exc)


@router.put("/roles/{role_id}")
def rbac_role_update(role_id: int, body: RoleUpdate, _user=Depends(_require_admin)):
    """更新角色描述和权限列表。系统角色只允许修改描述。"""
    try:
        data = get_rbac_app_service().update_role(
            role_id, description=body.description, permissions=body.permissions
        )
        return {"success": True, "data": data}
    except AppError as exc:
        return _handle_app_error(exc)


@router.delete("/roles/{role_id}")
def rbac_role_delete(role_id: int, _user=Depends(_require_admin)):
    """删除自定义角色（系统角色不可删除）。"""
    try:
        get_rbac_app_service().delete_role(role_id)
        return {"success": True, "message": "角色已删除"}
    except AppError as exc:
        return _handle_app_error(exc)


# ── 权限管理 ─────────────────────────────────────────────────────


@router.get("/permissions")
def rbac_permissions_list(
    _user=Depends(_require_admin),
    module: str | None = Query(default=None),
):
    """列出所有权限，可按模块过滤。"""
    return {"success": True, "data": get_rbac_app_service().list_permissions(module)}


@router.post("/permissions")
def rbac_permission_create(body: PermissionCreate, _user=Depends(_require_admin)):
    """创建新权限定义（扩展系统权限集）。"""
    try:
        data = get_rbac_app_service().create_permission(
            body.code, body.name, body.description, body.module
        )
        return JSONResponse({"success": True, "data": data}, status_code=201)
    except AppError as exc:
        return _handle_app_error(exc)


@router.delete("/permissions/{perm_id}")
def rbac_permission_delete(perm_id: int, _user=Depends(_require_admin)):
    """删除权限（同时从所有角色中解除绑定）。"""
    try:
        get_rbac_app_service().delete_permission(perm_id)
        return {"success": True, "message": "权限已删除"}
    except AppError as exc:
        return _handle_app_error(exc)


# ── 用户-角色 ────────────────────────────────────────────────────


@router.get("/users/{user_id}/permissions")
def rbac_user_permissions(user_id: int, _user=Depends(_require_admin)):
    """查询指定用户的有效权限（通过 role 字段解析）。"""
    try:
        return {"success": True, "data": get_rbac_app_service().get_user_permissions(user_id)}
    except AppError as exc:
        return _handle_app_error(exc)


@router.put("/users/{user_id}/role")
def rbac_user_assign_role(user_id: int, body: UserRoleAssign, _user=Depends(_require_admin)):
    """将用户分配到指定角色（修改 User.role 字段）。"""
    try:
        data = get_rbac_app_service().assign_user_role(user_id, body.role)
        return {"success": True, "data": data}
    except AppError as exc:
        return _handle_app_error(exc)


# ── 权限种子补全 ─────────────────────────────────────────────────


@router.post("/seed-missing-permissions")
def rbac_seed_permissions(_user=Depends(_require_admin)):
    """补全缺失的系统权限定义（幂等；仅新增不覆盖）。"""
    added = get_rbac_app_service().seed_missing_permissions()
    return {"success": True, "added": added, "message": f"新增 {len(added)} 条权限定义"}
