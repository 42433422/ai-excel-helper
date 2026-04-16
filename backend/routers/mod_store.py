"""
XCAGI「MOD 商店」兼容 API：由主后端提供目录与占位接口，无需单独启动 modstore_server。

目录数据来自壳层 ``list_mod_items()``（与 /api/mods 同源）；安装/上传等仍为占位实现。
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from backend.shell.mods_catalog import list_mod_items

logger = logging.getLogger(__name__)

router = APIRouter(tags=["mod-store"])


def _is_extension_row(d: dict[str, Any]) -> bool:
    mid = str(d.get("id") or "").strip()
    if not mid or mid.lower() == "all":
        return False
    t = str(d.get("type") or "mod").strip().lower()
    if t in ("category", "template", "shell_seed"):
        return False
    return True


def _item_to_mod_info(d: dict[str, Any]) -> dict[str, Any]:
    mid = str(d.get("id") or "").strip()
    name = str(d.get("name") or mid or "未命名").strip() or mid
    ver = str(d.get("version") or "1.0.0").strip() or "1.0.0"
    author = str(d.get("author") or "—").strip() or "—"
    desc = str(d.get("description") or "").strip()
    installed = _is_extension_row(d)
    return {
        "id": mid,
        "name": name,
        "version": ver,
        "author": author,
        "description": desc,
        "package_file": None,
        "is_installed": installed,
        "download_count": 0,
        "total_downloads": 0,
        "avg_rating": 0.0,
        "rating_count": 0,
        "created_at": None,
        "dependencies": {},
    }


def _all_rows() -> list[dict[str, Any]]:
    try:
        items = list_mod_items()
        return [_item_to_mod_info(x.model_dump()) for x in items]
    except Exception as e:
        logger.warning("mod-store catalog: list_mod_items failed: %s", e)
        return []


@router.get("/catalog")
async def mod_store_catalog() -> dict[str, Any]:
    rows = _all_rows()
    installed = [r for r in rows if r.get("is_installed")]
    return {
        "success": True,
        "data": {
            "installed": installed,
            "available": rows,
            "indexed_count": len(rows),
        },
    }


@router.get("/search")
async def mod_store_search(
    q: str | None = Query(None),
    author: str | None = Query(None),
    installed: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> dict[str, Any]:
    rows = _all_rows()
    out = rows
    if q and str(q).strip():
        k = str(q).strip().lower()
        out = [r for r in out if k in (r.get("name") or "").lower() or k in (r.get("id") or "").lower()]
    if author and str(author).strip():
        a = str(author).strip().lower()
        out = [r for r in out if a in (r.get("author") or "").lower()]
    if installed is True:
        out = [r for r in out if r.get("is_installed")]
    return {"success": True, "data": out[:limit]}


@router.get("/popular")
async def mod_store_popular(limit: int = Query(10, ge=1, le=200)) -> dict[str, Any]:
    rows = _all_rows()
    return {"success": True, "data": rows[:limit]}


@router.get("/recent")
async def mod_store_recent(limit: int = Query(10, ge=1, le=200)) -> dict[str, Any]:
    rows = _all_rows()
    return {"success": True, "data": list(reversed(rows))[:limit]}


@router.get("/mod/{mod_id}/details")
async def mod_store_details(mod_id: str) -> dict[str, Any]:
    mid = (mod_id or "").strip()
    for r in _all_rows():
        if str(r.get("id")) == mid:
            return {
                "success": True,
                "data": {
                    "id": r["id"],
                    "name": r["name"],
                    "version": r["version"],
                    "author": r["author"],
                    "description": r["description"],
                    "statistics": None,
                    "ratings": [],
                    "rating_count": 0,
                },
            }
    raise HTTPException(status_code=404, detail="未找到该 MOD")


def _not_implemented(what: str) -> dict[str, Any]:
    return {
        "success": False,
        "detail": f"{what} 尚未在本后端实现；请将 Mod 包放入 XCAGI/mods 或通过 MODstore 工具链。",
    }


@router.post("/upload")
async def mod_store_upload() -> dict[str, Any]:
    return _not_implemented("上传")


@router.post("/install")
async def mod_store_install() -> dict[str, Any]:
    return _not_implemented("安装")


@router.post("/uninstall")
async def mod_store_uninstall() -> dict[str, Any]:
    return _not_implemented("卸载")


@router.post("/update")
async def mod_store_update() -> dict[str, Any]:
    return _not_implemented("更新")


@router.get("/validate")
async def mod_store_validate() -> dict[str, Any]:
    return {"success": False, "message": "未实现", "data": None}


@router.get("/updates")
async def mod_store_updates() -> dict[str, Any]:
    return {"success": True, "data": {"updates_available": [], "count": 0}}


@router.get("/dependencies")
async def mod_store_dependencies() -> dict[str, Any]:
    return {
        "success": True,
        "data": {
            "mod_id": "",
            "dependencies": [],
            "satisfied": [],
            "missing": [],
            "can_install": True,
        },
    }


@router.post("/mod/{mod_id}/rate")
async def mod_store_rate(mod_id: str) -> dict[str, Any]:
    return _not_implemented("评分")


@router.get("/package/{package_file:path}/download")
async def mod_store_download(package_file: str) -> dict[str, Any]:
    raise HTTPException(status_code=404, detail="包下载未实现")


@router.delete("/package/{package_file:path}")
async def mod_store_delete_package(package_file: str) -> dict[str, Any]:
    return _not_implemented("删除包")


@router.post("/index/rebuild")
async def mod_store_rebuild_index() -> dict[str, Any]:
    return {"success": True, "data": {"indexed": 0, "failed": 0}, "message": "索引由磁盘 manifest 实时生成，无需重建。"}
