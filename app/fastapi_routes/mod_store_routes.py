"""XCAGI「MOD 商店」兼容 API：本机状态 + 修茈公网 Catalog 适配器。"""

from __future__ import annotations

import dataclasses
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field

from app.application.mod_store_catalog_app import (
    catalog_base_url,
    catalog_download_to,
    catalog_get_json,
    iter_catalog_packages,
    normalize_package_zip_path,
    sync_modstore_library_to_local,
)
from app.shell.mods_catalog import list_mod_items

logger = logging.getLogger(__name__)

router = APIRouter(tags=["mod-store"])


class ModStoreCatalogPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    installed: list[dict[str, Any]]
    available: list[dict[str, Any]]
    indexed_count: int


class ModStoreCatalogResponse(BaseModel):
    success: Literal[True] = True
    data: ModStoreCatalogPayload


class ModStoreListResponse(BaseModel):
    success: Literal[True] = True
    data: list[dict[str, Any]]


class ModStoreDetailData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    version: str
    author: str
    description: str
    statistics: Any | None = None
    ratings: list[Any] = Field(default_factory=list)
    rating_count: int = 0
    source: str
    catalog_base_url: str


class ModStoreDetailResponse(BaseModel):
    success: Literal[True] = True
    data: ModStoreDetailData


class ModStoreInstallResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    success: bool
    message: str
    data: dict[str, Any] | None = None


class ModStoreSimpleResponse(BaseModel):
    success: bool
    message: str | None = None
    data: dict[str, Any] | None = None


class ModStoreUpdatesResponse(BaseModel):
    success: Literal[True] = True
    data: dict[str, Any]


class ModStoreDependenciesResponse(BaseModel):
    success: Literal[True] = True
    data: dict[str, Any]


class ModStoreRebuildResponse(BaseModel):
    success: Literal[True] = True
    data: dict[str, Any]
    message: str | None = None


class ModStoreNotImplementedResponse(BaseModel):
    success: Literal[False] = False
    detail: str


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
        "source": "local",
        "catalog_base_url": catalog_base_url(),
    }


def _all_rows() -> list[dict[str, Any]]:
    try:
        items = list_mod_items()
        return [_item_to_mod_info(x.model_dump()) for x in items]
    except Exception as e:
        logger.warning("mod-store catalog: list_mod_items failed: %s", e)
        return []


def _installed_by_id() -> dict[str, dict[str, Any]]:
    return {str(r.get("id") or ""): r for r in _all_rows() if r.get("is_installed")}


def _remote_to_mod_info(d: dict[str, Any], installed_ids: set[str]) -> dict[str, Any]:
    mid = str(d.get("id") or d.get("pkg_id") or "").strip()
    version = str(d.get("version") or "1.0.0").strip() or "1.0.0"
    name = str(d.get("name") or mid or "未命名").strip() or mid
    commerce = d.get("commerce") if isinstance(d.get("commerce"), dict) else {}
    download_url = str(d.get("download_url") or "").strip()
    from app.mod_sdk.host_foundation import catalog_store_collection

    row_out = {
        "id": mid,
        "pkg_id": mid,
        "name": name,
        "version": version,
        "author": str(
            d.get("author") or d.get("publisher") or commerce.get("seller") or "—"
        ).strip()
        or "—",
        "description": str(d.get("description") or "").strip(),
        "package_file": f"{mid}:{version}",
        "download_url": download_url,
        "is_installed": mid in installed_ids,
        "download_count": int(d.get("download_count") or d.get("total_downloads") or 0),
        "total_downloads": int(d.get("total_downloads") or d.get("download_count") or 0),
        "avg_rating": float(d.get("avg_rating") or 0.0),
        "rating_count": int(d.get("rating_count") or 0),
        "created_at": d.get("created_at") or d.get("updated_at"),
        "dependencies": d.get("dependencies") if isinstance(d.get("dependencies"), dict) else {},
        "artifact": d.get("artifact") or "mod",
        "sha256": d.get("sha256"),
        "commerce": commerce,
        "license": d.get("license"),
        "source": "remote",
        "catalog_base_url": catalog_base_url(),
        "store_collection": str(
            d.get("store_collection") or commerce.get("collection") or ""
        ).strip(),
        "public_listing": bool(d.get("public_listing")),
    }
    if not row_out["store_collection"]:
        row_out["store_collection"] = catalog_store_collection(row_out)
    return row_out


async def _remote_rows() -> list[dict[str, Any]]:
    from app.mod_sdk.host_foundation import is_infrastructure_mod_hidden_from_store

    installed_ids = set(_installed_by_id())
    rows: list[dict[str, Any]] = []
    async for row in iter_catalog_packages():
        info = _remote_to_mod_info(row, installed_ids)
        mid = str(info.get("id") or "").strip()
        if not mid:
            continue
        # 市场上架的工作流单员工 Mod（public_listing）须在能力库展示，与 /api/market/catalog 一致
        if is_infrastructure_mod_hidden_from_store(mid) and not row.get("public_listing"):
            continue
        rows.append(info)
    return rows


def _inject_host_foundation_row(available: list[dict[str, Any]], installed_ids: set[str]) -> None:
    from app.mod_sdk.host_foundation import (
        HOST_FOUNDATION_EMPLOYEE_PACK_ID,
        host_foundation_catalog_row,
        is_host_foundation_pack_installed,
        is_infrastructure_mod_hidden_from_store,
    )

    if any(str(r.get("id") or "") == HOST_FOUNDATION_EMPLOYEE_PACK_ID for r in available):
        return
    installed = (
        HOST_FOUNDATION_EMPLOYEE_PACK_ID in installed_ids or is_host_foundation_pack_installed()
    )
    available.insert(0, host_foundation_catalog_row(installed=installed))
    # 去掉误上架的逐项 bridge（远端若仍有历史条目）
    i = 0
    while i < len(available):
        mid = str(available[i].get("id") or "").strip()
        row = available[i]
        listed = bool(row.get("public_listing")) if isinstance(row, dict) else False
        if (
            mid != HOST_FOUNDATION_EMPLOYEE_PACK_ID
            and is_infrastructure_mod_hidden_from_store(mid)
            and not listed
        ):
            available.pop(i)
            continue
        i += 1


async def _combined_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from app.mod_sdk.host_foundation import is_infrastructure_mod_hidden_from_store

    installed_map = _installed_by_id()
    remote = await _remote_rows()
    seen = {str(r.get("id") or "") for r in remote}
    available = list(remote)
    for mid, local in installed_map.items():
        if mid and mid not in seen and not is_infrastructure_mod_hidden_from_store(mid):
            available.append(local)
    _inject_host_foundation_row(available, set(installed_map.keys()))
    from app.mod_sdk.host_foundation import inject_aux_employee_pack_rows

    inject_aux_employee_pack_rows(available, set(installed_map.keys()))
    installed_visible = [
        r
        for r in installed_map.values()
        if not is_infrastructure_mod_hidden_from_store(str(r.get("id") or ""))
    ]
    return available, installed_visible


def _filter_rows(
    rows: list[dict[str, Any]],
    q: str | None = None,
    author: str | None = None,
    installed: bool | None = None,
) -> list[dict[str, Any]]:
    out = rows
    if q and str(q).strip():
        k = str(q).strip().lower()
        out = [
            r
            for r in out
            if k in (r.get("name") or "").lower()
            or k in (r.get("id") or "").lower()
            or k in (r.get("description") or "").lower()
        ]
    if author and str(author).strip():
        a = str(author).strip().lower()
        out = [r for r in out if a in (r.get("author") or "").lower()]
    if installed is True:
        out = [r for r in out if r.get("is_installed")]
    elif installed is False:
        out = [r for r in out if not r.get("is_installed")]
    return out


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


async def _body_value(request: Request, key: str, default: str = "") -> str:
    content_type = (request.headers.get("content-type") or "").lower()
    try:
        if "application/json" in content_type:
            data = await request.json()
            if isinstance(data, dict):
                return _safe_text(data.get(key) or default)
            return default
        form = await request.form()
        return _safe_text(form.get(key) or default)
    except Exception:
        return default


async def _request_payload(request: Request) -> dict[str, str]:
    content_type = (request.headers.get("content-type") or "").lower()
    try:
        if "application/json" in content_type:
            data = await request.json()
            return (
                {str(k): _safe_text(v) for k, v in data.items()} if isinstance(data, dict) else {}
            )
        form = await request.form()
        return {str(k): _safe_text(v) for k, v in form.items()}
    except Exception:
        return {}


def _split_package_file(package_file: str) -> tuple[str, str]:
    raw = _safe_text(package_file)
    if ":" in raw:
        mid, version = raw.split(":", 1)
        return mid.strip(), version.strip()
    return raw, ""


_normalize_package_zip = normalize_package_zip_path


async def _install_from_catalog(
    pkg_id: str, version: str, activate: bool = True
) -> ModStoreInstallResult:
    from app.mod_sdk.host_foundation import (
        install_aux_employee_pack_from_repo_seed,
        is_aux_employee_pack_mod_id,
        is_host_foundation_employee_pack,
    )

    if is_host_foundation_employee_pack(pkg_id):
        return await _install_host_foundation_internal(edition=None)

    if is_aux_employee_pack_mod_id(pkg_id):
        ok, message = install_aux_employee_pack_from_repo_seed(pkg_id, activate=activate)
        if ok:
            return ModStoreInstallResult(success=True, message=message, data={"id": pkg_id})
        logger.info("aux employee seed install failed for %s: %s; try catalog", pkg_id, message)

    if not pkg_id:
        raise HTTPException(status_code=400, detail="缺少 pkg_id")
    if not version:
        versions = await catalog_get_json(f"/packages/by-id/{quote(pkg_id, safe='')}/versions")
        rows = versions.get("versions") or []
        if isinstance(rows, list) and rows:
            first = rows[0]
            if isinstance(first, dict):
                version = _safe_text(first.get("version"))
            else:
                version = _safe_text(first)
    if not version:
        raise HTTPException(status_code=400, detail="缺少 version")

    tmp = tempfile.NamedTemporaryFile(prefix="xcagi-mod-", suffix=".zip", delete=False)
    tmp_path = tmp.name
    tmp.close()
    normalized_path = tmp_path
    try:
        await catalog_download_to(
            f"/packages/{quote(pkg_id, safe='')}/{quote(version, safe='')}/download",
            Path(tmp_path),
        )
        normalized_path = _normalize_package_zip(tmp_path)
        from app.infrastructure.mods.artifact_constants import ARTIFACT_EMPLOYEE_PACK
        from app.infrastructure.mods.artifact_package import peek_artifact

        if peek_artifact(normalized_path) == ARTIFACT_EMPLOYEE_PACK:
            from app.infrastructure.mods.employee_registry import get_employee_registry

            ok, message = get_employee_registry().install_from_package(
                normalized_path, verify_signature=False
            )
            return ModStoreInstallResult(success=bool(ok), message=message, data=None)

        from app.infrastructure.mods.mod_manager import get_mod_manager

        ok, message, metadata = get_mod_manager().install_mod_package(
            normalized_path,
            verify_signature=False,
            activate=activate,
        )
        data = (
            dataclasses.asdict(metadata)
            if metadata and dataclasses.is_dataclass(metadata)
            else None
        )
        return ModStoreInstallResult(success=bool(ok), message=message, data=data)
    finally:
        for p in {tmp_path, normalized_path}:
            try:
                if p and os.path.exists(p):
                    os.unlink(p)
            except OSError:
                logger.warning("无法删除临时 Mod 包: %s", p)


@router.get("/catalog", response_model=ModStoreCatalogResponse)
async def mod_store_catalog() -> ModStoreCatalogResponse:
    rows, installed = await _combined_rows()
    return ModStoreCatalogResponse(
        data=ModStoreCatalogPayload(installed=installed, available=rows, indexed_count=len(rows))
    )


@router.get("/search", response_model=ModStoreListResponse)
async def mod_store_search(
    q: str | None = Query(None),
    author: str | None = Query(None),
    installed: bool | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> ModStoreListResponse:
    rows, _installed = await _combined_rows()
    out = _filter_rows(rows, q=q, author=author, installed=installed)
    return ModStoreListResponse(data=out[:limit])


@router.get("/popular", response_model=ModStoreListResponse)
async def mod_store_popular(limit: int = Query(10, ge=1, le=200)) -> ModStoreListResponse:
    rows, _installed = await _combined_rows()
    rows.sort(key=lambda r: r.get("total_downloads") or r.get("download_count") or 0, reverse=True)
    return ModStoreListResponse(data=rows[:limit])


@router.get("/recent", response_model=ModStoreListResponse)
async def mod_store_recent(limit: int = Query(10, ge=1, le=200)) -> ModStoreListResponse:
    rows, _installed = await _combined_rows()
    rows.sort(key=lambda r: str(r.get("created_at") or ""), reverse=True)
    return ModStoreListResponse(data=rows[:limit])


@router.get("/mod/{mod_id}/details", response_model=ModStoreDetailResponse)
async def mod_store_details(mod_id: str) -> ModStoreDetailResponse:
    mid = (mod_id or "").strip()
    try:
        versions = await catalog_get_json(f"/packages/by-id/{quote(mid, safe='')}/versions")
        rows = versions.get("versions") or []
        if isinstance(rows, list) and rows:
            latest = rows[0] if isinstance(rows[0], dict) else {"version": rows[0]}
            version = _safe_text(latest.get("version")) or "1.0.0"
            detail = await catalog_get_json(
                f"/packages/{quote(mid, safe='')}/{quote(version, safe='')}"
            )
            return ModStoreDetailResponse(
                data=ModStoreDetailData(
                    id=str(detail.get("id") or mid),
                    name=str(detail.get("name") or mid),
                    version=str(detail.get("version") or version),
                    author=str(detail.get("author") or detail.get("publisher") or "—"),
                    description=str(detail.get("description") or ""),
                    statistics=None,
                    ratings=[],
                    rating_count=0,
                    source="remote",
                    catalog_base_url=catalog_base_url(),
                )
            )
    except HTTPException as exc:
        logger.info("remote catalog detail fallback for %s: %s", mid, exc.detail)
    rows, _installed = await _combined_rows()
    for r in rows:
        if str(r.get("id")) == mid:
            return ModStoreDetailResponse(
                data=ModStoreDetailData(
                    id=str(r["id"]),
                    name=str(r["name"]),
                    version=str(r["version"]),
                    author=str(r["author"]),
                    description=str(r["description"]),
                    statistics=None,
                    ratings=[],
                    rating_count=0,
                    source=str(r.get("source") or "local"),
                    catalog_base_url=str(r.get("catalog_base_url") or catalog_base_url()),
                )
            )
    raise HTTPException(status_code=404, detail="未找到该 MOD")


@router.post("/upload", response_model=ModStoreNotImplementedResponse)
async def mod_store_upload() -> ModStoreNotImplementedResponse:
    return ModStoreNotImplementedResponse(
        detail="上传 尚未在本后端实现；请将 Mod 包放入 XCAGI/mods 或通过 MODstore 工具链。"
    )


@router.post("/install", response_model=ModStoreInstallResult)
async def mod_store_install(request: Request) -> ModStoreInstallResult:
    payload = await _request_payload(request)
    pkg_id = _safe_text(payload.get("pkg_id") or payload.get("mod_id"))
    version = _safe_text(payload.get("version"))
    if not pkg_id:
        pkg_id, parsed_version = _split_package_file(payload.get("package_file") or "")
        version = version or parsed_version
    activate = str(payload.get("activate") or "true").lower() not in {"0", "false", "no"}
    return await _install_from_catalog(pkg_id, version, activate=activate)


@router.post("/uninstall", response_model=ModStoreSimpleResponse)
async def mod_store_uninstall(request: Request) -> ModStoreSimpleResponse:
    mod_id = await _body_value(request, "mod_id")
    if not mod_id:
        raise HTTPException(status_code=400, detail="缺少 mod_id")
    from app.infrastructure.mods.mod_manager import get_mod_manager

    ok, message = get_mod_manager().uninstall_mod(mod_id, remove_files=True)
    return ModStoreSimpleResponse(success=bool(ok), message=message, data={"id": mod_id})


@router.post("/update", response_model=ModStoreInstallResult)
async def mod_store_update(request: Request) -> ModStoreInstallResult:
    payload = await _request_payload(request)
    pkg_id = _safe_text(payload.get("pkg_id") or payload.get("mod_id"))
    version = _safe_text(payload.get("version"))
    if not pkg_id:
        pkg_id, parsed_version = _split_package_file(payload.get("package_file") or "")
        version = version or parsed_version
    return await _install_from_catalog(pkg_id, version, activate=True)


@router.get("/validate", response_model=ModStoreSimpleResponse)
async def mod_store_validate() -> ModStoreSimpleResponse:
    return ModStoreSimpleResponse(success=False, message="未实现", data=None)


@router.get("/updates", response_model=ModStoreUpdatesResponse)
async def mod_store_updates() -> ModStoreUpdatesResponse:
    return ModStoreUpdatesResponse(data={"updates_available": [], "count": 0})


@router.get("/dependencies", response_model=ModStoreDependenciesResponse)
async def mod_store_dependencies() -> ModStoreDependenciesResponse:
    return ModStoreDependenciesResponse(
        data={
            "mod_id": "",
            "dependencies": [],
            "satisfied": [],
            "missing": [],
            "can_install": True,
        }
    )


@router.post("/mod/{mod_id}/rate", response_model=ModStoreNotImplementedResponse)
async def mod_store_rate(mod_id: str) -> ModStoreNotImplementedResponse:
    return ModStoreNotImplementedResponse(
        detail="评分 尚未在本后端实现；请将 Mod 包放入 XCAGI/mods 或通过 MODstore 工具链。"
    )


@router.get("/package/{package_file:path}/download")
async def mod_store_download(package_file: str) -> None:
    raise HTTPException(status_code=404, detail="包下载未实现")


@router.delete("/package/{package_file:path}", response_model=ModStoreNotImplementedResponse)
async def mod_store_delete_package(package_file: str) -> ModStoreNotImplementedResponse:
    return ModStoreNotImplementedResponse(
        detail="删除包 尚未在本后端实现；请将 Mod 包放入 XCAGI/mods 或通过 MODstore 工具链。"
    )


@router.post("/index/rebuild", response_model=ModStoreRebuildResponse)
async def mod_store_rebuild_index() -> ModStoreRebuildResponse:
    return ModStoreRebuildResponse(
        data={"indexed": 0, "failed": 0}, message="索引由磁盘 manifest 实时生成，无需重建。"
    )


async def _ensure_host_foundation_employee_on_disk() -> tuple[bool, str]:
    """将仓库内置 _employees/xcagi-host-foundation-employee 复制到用户 mods 目录（若尚未存在）。"""
    import shutil

    from app.infrastructure.mods.employee_registry import employees_root, get_employee_registry
    from app.mod_sdk.host_foundation import HOST_FOUNDATION_EMPLOYEE_PACK_ID

    mm_root = get_employee_registry().mods_root
    dest = os.path.join(employees_root(mm_root), HOST_FOUNDATION_EMPLOYEE_PACK_ID)
    if os.path.isdir(dest):
        return True, "employee pack present"
    src = os.path.join(mm_root, "_employees", HOST_FOUNDATION_EMPLOYEE_PACK_ID)
    if not os.path.isdir(src):
        return False, f"内置员工包目录缺失：{src}"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copytree(src, dest)
    return True, "employee pack seeded"


async def _install_host_foundation_internal(edition: str | None) -> ModStoreInstallResult:
    from app.mod_sdk.edition_policy import resolve_edition
    from app.mod_sdk.host_foundation import materialize_host_foundation_bridges

    ok, msg = await _ensure_host_foundation_employee_on_disk()
    if not ok:
        return ModStoreInstallResult(success=False, message=msg, data=None)
    ed = (edition or resolve_edition() or "generic").strip().lower()
    if ed not in ("minimal", "generic", "full"):
        ed = "generic"
    try:
        data = materialize_host_foundation_bridges(ed)  # type: ignore[arg-type]
    except Exception as exc:
        logger.exception("materialize_host_foundation_bridges failed (edition=%s)", ed)
        return ModStoreInstallResult(
            success=False,
            message=f"展开宿主 bridge 失败：{exc}",
            data={"edition": ed, "missing_mod_ids": [], "ready": False},
        )
    if data.get("ready"):
        message = f"宿主基础能力员工包已就绪（bridge {data.get('installed_count')}/{data.get('expected_count')}）"
        success = True
    else:
        missing = data.get("missing_mod_ids") or []
        message = f"宿主 bridge 未齐（{data.get('installed_count')}/{data.get('expected_count')}）：{'、'.join(missing[:8])}"
        success = False
    return ModStoreInstallResult(success=success, message=message, data=data)


@router.post("/install-host-foundation", response_model=ModStoreSimpleResponse)
async def mod_store_install_host_foundation(
    edition: str | None = Query(None, description="minimal | generic | full"),
) -> ModStoreSimpleResponse:
    """安装「宿主基础能力·预装员工」并 materialize 全部 bridge（非逐项 Mod 上架）。"""
    try:
        result = await _install_host_foundation_internal(edition)
        return ModStoreSimpleResponse(
            success=result.success, message=result.message, data=result.data
        )
    except Exception as exc:
        logger.exception("install-host-foundation failed")
        return ModStoreSimpleResponse(
            success=False,
            message=f"装包失败：{exc}",
            data=None,
        )


@router.post("/bootstrap-edition-pack", response_model=ModStoreSimpleResponse)
async def mod_store_bootstrap_edition_pack(
    edition: str | None = Query(None, description="minimal | generic | full"),
) -> ModStoreSimpleResponse:
    """装齐当前 edition 所需 Mod：先复制安装包内置 mods/，再对缺失项尝试 Catalog。"""
    from app.mod_sdk.edition_bootstrap import bootstrap_edition_pack
    from app.mod_sdk.edition_policy import resolve_edition

    ed = (edition or resolve_edition() or "generic").strip().lower()
    if ed not in ("minimal", "generic", "full"):
        raise HTTPException(status_code=400, detail="edition 须为 minimal、generic 或 full")
    try:
        from app.mod_sdk.product_skus import assert_bootstrap_edition_allowed

        assert_bootstrap_edition_allowed(edition)
    except PermissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    data = await bootstrap_edition_pack(ed)  # type: ignore[arg-type]
    if data.get("ready"):
        msg = "通用宿主包已装齐"
    else:
        installed = int(data.get("installed_count") or 0)
        expected = int(data.get("expected_count") or 0)
        failed_ids: list[str] = []
        for row in data.get("catalog") or []:
            if not isinstance(row, dict):
                continue
            if row.get("status") in ("catalog_failed", "missing"):
                mid = str(row.get("mod_id") or "").strip()
                if mid:
                    failed_ids.append(mid)
        for row in data.get("seed") or []:
            if not isinstance(row, dict):
                continue
            if row.get("status") in ("missing", "error"):
                mid = str(row.get("mod_id") or "").strip()
                if mid and mid not in failed_ids:
                    failed_ids.append(mid)
        hint = "、".join(failed_ids[:8])
        msg = f"宿主包未装齐（{installed}/{expected}）"
        if hint:
            msg += f"：{hint}"
    return ModStoreSimpleResponse(
        success=bool(data.get("ready")),
        message=msg,
        data=data,
    )


@router.post("/sync-modstore-library", response_model=ModStoreSimpleResponse)
async def mod_store_sync_modstore_library(request: Request) -> ModStoreSimpleResponse:
    """使用修茈 PAT（须含 ``mod:sync``）从线上 ``/v1/mod-sync`` 拉 zip 并安装到本机 ``mods/``。"""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="需要 JSON 请求体") from None
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON 须为对象")

    base = (
        str(body.get("base_url") or body.get("baseUrl") or "").strip().rstrip("/")
        or "https://xiu-ci.com"
    )
    token = str(body.get("token") or "").strip()
    if not token:
        raise HTTPException(
            status_code=400, detail="缺少 token（修茈 Developer PAT，需含 mod:sync）"
        )

    sync_all = bool(body.get("all"))
    raw_ids = body.get("mod_ids")
    mod_ids: list[str] | None = None
    if isinstance(raw_ids, list):
        mod_ids = [str(x).strip() for x in raw_ids if str(x).strip()]
    elif isinstance(raw_ids, str) and raw_ids.strip():
        mod_ids = [x.strip() for x in raw_ids.split(",") if x.strip()]

    if not sync_all and (not mod_ids or len(mod_ids) == 0):
        raise HTTPException(
            status_code=400, detail="请指定 mod_ids（数组或逗号分隔字符串）或设置 all: true"
        )

    try:
        raw = await sync_modstore_library_to_local(
            base_url=base,
            token=token,
            mod_ids=mod_ids,
            sync_all_ok=sync_all,
        )
        return ModStoreSimpleResponse(
            success=bool(raw.get("success")),
            message=str(raw.get("message") or ""),
            data=raw.get("data") if isinstance(raw.get("data"), dict) else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e)) from e
