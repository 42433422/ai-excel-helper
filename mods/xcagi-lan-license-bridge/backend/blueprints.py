"""LAN 授权桥接 Mod（里程碑 J）— 全量门面路由，委托宿主 lan_* 实现。"""

import logging

from fastapi import APIRouter, Body, Depends, Path, Query, Request, Response

logger = logging.getLogger(__name__)

HOST_PREFIXES = ["/api/lan"]


def register_fastapi_routes(app, mod_id: str) -> None:
    from app.fastapi_routes.lan_admin_routes import (
        AccessRequestReview,
        IssueKeyRequest,
        approve_access_request_endpoint,
        issue_key_endpoint,
        kick_session_endpoint,
        list_access_requests_endpoint,
        list_allowlist_endpoint,
        list_audit_endpoint,
        list_keys_endpoint,
        list_sessions_endpoint,
        reject_access_request_endpoint,
        require_admin,
        revoke_allowlist_endpoint,
        revoke_key_endpoint,
        whoami,
    )
    from app.fastapi_routes.lan_routes import (
        AccessRequestPayload,
        ActivateRequest,
        activate,
        host_info,
        logout,
        my_access_request,
        request_access,
        status,
    )
    from app.fastapi_routes.lan_settings_routes import (
        LanSettingsUpdate,
        get_settings as get_settings_view,
        update_settings as update_settings_view,
    )

    router = APIRouter(prefix=f"/api/mod/{mod_id}", tags=[f"lan-bridge-{mod_id}"])

    @router.get("/status")
    def mod_status_meta():
        from app.mod_sdk.lan_compat import list_lan_facade_registry

        return {"success": True, "data": {**list_lan_facade_registry(), "mod_id": mod_id, "phase": "J"}}

    @router.get("/registry")
    def mod_registry():
        from app.mod_sdk.lan_compat import list_lan_facade_registry

        return {"success": True, "data": list_lan_facade_registry()}

    @router.get("/lan/host-info")
    async def mod_host_info(request: Request):
        return await host_info(request)

    @router.get("/lan/status")
    async def mod_lan_status(request: Request):
        return await status(request)

    @router.get("/lan/access-requests/mine")
    async def mod_my_access_request(request: Request):
        return await my_access_request(request)

    @router.post("/lan/access-requests")
    async def mod_request_access(payload: AccessRequestPayload, request: Request):
        return await request_access(payload, request)

    @router.post("/lan/activate")
    async def mod_activate(req: ActivateRequest, request: Request, response: Response):
        return await activate(req, request, response)

    @router.post("/lan/logout")
    async def mod_logout(request: Request, response: Response):
        return await logout(request, response)

    @router.get("/lan/admin/whoami")
    async def mod_whoami(actor: dict = Depends(require_admin)):
        return await whoami(actor)

    @router.get("/lan/admin/keys")
    async def mod_list_keys(
        actor: dict = Depends(require_admin),
        include_revoked: bool = True,
    ):
        return await list_keys_endpoint(actor, include_revoked=include_revoked)

    @router.post("/lan/admin/keys")
    async def mod_issue_key(
        payload: IssueKeyRequest,
        actor: dict = Depends(require_admin),
    ):
        return await issue_key_endpoint(payload, actor)

    @router.delete("/lan/admin/keys/{key_id}")
    async def mod_revoke_key(key_id: int = Path(..., ge=1), actor: dict = Depends(require_admin)):
        return await revoke_key_endpoint(key_id, actor)

    @router.get("/lan/admin/sessions")
    async def mod_list_sessions(
        actor: dict = Depends(require_admin),
        active_only: bool = True,
        limit: int = 200,
    ):
        return await list_sessions_endpoint(actor, active_only=active_only, limit=limit)

    @router.delete("/lan/admin/sessions/{jti}")
    async def mod_kick_session(
        jti: str = Path(..., min_length=1, max_length=128),
        actor: dict = Depends(require_admin),
    ):
        return await kick_session_endpoint(jti, actor)

    @router.get("/lan/admin/audit")
    async def mod_list_audit(actor: dict = Depends(require_admin), limit: int = 200):
        return await list_audit_endpoint(actor, limit=limit)

    @router.get("/lan/admin/access-requests")
    async def mod_list_access_requests(
        actor: dict = Depends(require_admin),
        status: str = "pending",
        limit: int = 200,
    ):
        return await list_access_requests_endpoint(actor, status=status, limit=limit)

    @router.post("/lan/admin/access-requests/{request_id}/approve")
    async def mod_approve_access_request(
        request_id: int = Path(..., ge=1),
        payload: AccessRequestReview,
        actor: dict = Depends(require_admin),
    ):
        return await approve_access_request_endpoint(request_id, payload, actor)

    @router.post("/lan/admin/access-requests/{request_id}/reject")
    async def mod_reject_access_request(
        request_id: int = Path(..., ge=1),
        payload: AccessRequestReview,
        actor: dict = Depends(require_admin),
    ):
        return await reject_access_request_endpoint(request_id, payload, actor)

    @router.get("/lan/admin/allowlist")
    async def mod_list_allowlist(
        actor: dict = Depends(require_admin),
        active_only: bool = True,
        limit: int = 200,
    ):
        return await list_allowlist_endpoint(actor, active_only=active_only, limit=limit)

    @router.delete("/lan/admin/allowlist/{client_id}")
    async def mod_revoke_allowlist(
        client_id: int = Path(..., ge=1),
        actor: dict = Depends(require_admin),
    ):
        return await revoke_allowlist_endpoint(client_id, actor)

    @router.get("/lan/admin/settings")
    async def mod_get_settings(request: Request):
        return await get_settings_view(request)

    @router.post("/lan/admin/settings")
    @router.put("/lan/admin/settings")
    async def mod_update_settings(request: Request, payload: LanSettingsUpdate):
        return await update_settings_view(request, payload)

    app.include_router(router)


def mod_init():
    logger.info("xcagi-lan-license-bridge initialized (phase J)")
