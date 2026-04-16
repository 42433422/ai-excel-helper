"""
XCAGI 壳层：mod 列表、加载占位、启动状态、动态路由、代理状态、client_mods_off。

契约字段说明见 ``backend.shell.mods_api_contracts``。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from backend.database import get_db_status
from backend.shell.mods_catalog import list_mod_items
from backend.shell.mods_schemas import (
    ClientModsOffRequest,
    ClientModsOffResponse,
    ModAgentStatusData,
    ModAgentStatusResponse,
    ModsListResponse,
    ModsLoadingPayload,
    ModsLoadingStatusResponse,
    ModsRoutesResponse,
    StartupComponent,
    StartupStatusResponse,
)
from backend.shell.xcagi_mods_discover import loading_status_extras, route_entries

router = APIRouter(tags=["xcagi-shell", "xcagi-mods"])


@router.get(
    "/mods",
    response_model=ModsListResponse,
    summary="Mod / 模板目录列表",
)
@router.get("/mods/", response_model=ModsListResponse, include_in_schema=False)
async def api_list_mods() -> ModsListResponse:
    return ModsListResponse(data=list_mod_items())


@router.get(
    "/mods/loading-status",
    response_model=ModsLoadingStatusResponse,
    summary="模块加载状态（占位，恒为就绪）",
)
@router.get("/mods/loading-status/", response_model=ModsLoadingStatusResponse, include_in_schema=False)
async def api_mods_loading_status() -> ModsLoadingStatusResponse:
    ex = loading_status_extras()
    payload = ModsLoadingPayload.model_validate({"loading": False, "loaded": True, "status": "ready", **ex})
    return ModsLoadingStatusResponse(data=payload)


@router.get(
    "/startup/status",
    response_model=StartupStatusResponse,
    summary="启动进度（占位，恒为就绪）",
)
@router.get("/startup/status/", response_model=StartupStatusResponse, include_in_schema=False)
async def api_startup_status() -> StartupStatusResponse:
    return StartupStatusResponse(
        components=[
            StartupComponent(name="http", status="ready"),
            StartupComponent(name="mods", status="ready"),
        ],
    )


@router.get(
    "/mods/routes",
    response_model=ModsRoutesResponse,
    summary="动态路由表（占位）",
)
@router.get("/mods/routes/", response_model=ModsRoutesResponse, include_in_schema=False)
async def api_mods_routes() -> ModsRoutesResponse:
    return ModsRoutesResponse(data=route_entries())


@router.post(
    "/mods/{mod_id}/publish-to-xcagi",
    summary="Mod 控制台：与 XCAGI 运行时对齐（回显当前库，不热改连接串）",
)
@router.post(
    "/mods/{mod_id}/publish-to-xcagi/",
    include_in_schema=False,
)
async def api_mod_publish_to_xcagi(mod_id: str) -> dict:
    """
    不能在不重启进程的前提下切换 ``DATABASE_URL``；本接口用于确认 Mod 已在壳层目录中，
    并返回当前进程实际使用的 PostgreSQL 摘要，便于与 .env 对照。
    """
    mid = (mod_id or "").strip()
    if not mid:
        raise HTTPException(status_code=400, detail="mod_id 不能为空")
    known = {m.id for m in list_mod_items()}
    if mid not in known:
        return {
            "success": False,
            "error": "unknown_mod",
            "message": f"未在壳层 Mod 列表中找到 id={mid!r}。请确认 manifest 已部署并由后端扫描。",
        }
    info = get_db_status()
    if info.get("database_mod_gate_closed"):
        return {
            "success": True,
            "data": {
                "mod_id": mid,
                "database_reachable": False,
                "message": "数据库门禁未通过，当前进程未解析 DATABASE_URL。请部署 FHD_DB_MOD_GATE 要求的 Mod 后重启后端。",
                "mod_database_gate": info.get("mod_database_gate"),
            },
        }
    summ = info.get("postgresql_summary") or {}
    return {
        "success": True,
        "data": {
            "mod_id": mid,
            "database_reachable": True,
            "postgresql_summary": summ,
            "db_mode": info.get("mode"),
            "message": (
                "已记录对齐请求。PostgreSQL 连接串仅在进程启动时读取；若刚修改 DATABASE_URL 或 Mod 附带的数据库配置，"
                "请重启 run.py / 后端服务后再打开「设置」或再次推送以查看新库名。"
            ),
        },
    }


@router.get(
    "/mods/{project_id}/{agent_name}/status",
    response_model=ModAgentStatusResponse,
    summary="项目下代理状态（占位）",
)
@router.get(
    "/mods/{project_id}/{agent_name}/status/",
    response_model=ModAgentStatusResponse,
    include_in_schema=False,
)
async def api_mod_agent_status(project_id: str, agent_name: str) -> ModAgentStatusResponse:
    return ModAgentStatusResponse(
        data=ModAgentStatusData(agent_name=agent_name, project_id=project_id),
    )


@router.post(
    "/state/client-mods-off",
    response_model=ClientModsOffResponse,
    summary="客户端 mod 开关（回显，无持久化）",
)
@router.post(
    "/state/client-mods-off/",
    response_model=ClientModsOffResponse,
    include_in_schema=False,
)
async def api_client_mods_off(request: Request) -> ClientModsOffResponse:
    try:
        raw = await request.json()
    except Exception:
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    body = ClientModsOffRequest.model_validate(raw)
    off = bool(body.client_mods_off)
    return ClientModsOffResponse(client_mods_off=off)
