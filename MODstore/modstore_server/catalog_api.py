"""公网 Catalog 只读/上传 API（挂载在 XC AGI 服务 /v1）。"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, File, Form, Header, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from modstore_server.catalog_store import (
    append_package,
    get_package,
    list_packages,
    list_versions,
    load_store,
    packages_path,
    promote_draft_to_stable,
)
from modstore_server.catalog_sync import upsert_catalog_item_from_xc_package_dict
from modstore_server.employee_config_v2 import extract_or_upgrade_v2_config, validate_v2_config
from modstore_server.industry_taxonomy import get_industry_tree
from modstore_server.models import get_session_factory
from modstore_server.vector_store import insert_embedding, query_similar

router = APIRouter(prefix="/v1", tags=["catalog"])


def _invalidate_catalog_list_caches(pkg_id: Any = None, version: Any = None) -> None:
    """Best-effort cache invalidation after a write.

    List/index caches use parameter-hashed keys that cannot be enumerated, so
    we rely on their short TTL (300 s / 60 s) to expire naturally.  The only
    key we can reliably delete is the per-package detail key.
    """
    from modstore_server import cache
    from modstore_server.catalog_store import packages_path

    if pkg_id and version:
        cache.delete(f"catalog:v1:pkg:{pkg_id}:{version}")
    p = packages_path()
    mtime = int(p.stat().st_mtime) if p.is_file() else 0
    cache.delete(f"catalog:v1:index:{mtime}")


def _upload_token() -> str:
    return (os.environ.get("MODSTORE_CATALOG_UPLOAD_TOKEN") or "").strip()


def _require_upload(authorization: Optional[str]) -> None:
    tok = _upload_token()
    if not tok:
        raise HTTPException(503, "未配置 MODSTORE_CATALOG_UPLOAD_TOKEN，拒绝写入")
    if (authorization or "").strip() != f"Bearer {tok}":
        raise HTTPException(401, "无效的上传凭证")


def _params_hash(*args: Any) -> str:
    """Stable short hash of query parameter values for use in cache keys."""
    return hashlib.sha1(json.dumps(args, sort_keys=True).encode()).hexdigest()[:12]


@router.get("/packages", summary="分页列出包")
def api_list_packages(
    artifact: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    from modstore_server import cache

    ck = f"catalog:v1:packages:list:{_params_hash(artifact, q, limit, offset)}"
    cached = cache.get_json(ck)
    if cached is not None:
        return cached
    rows, total = list_packages(artifact=artifact, q=q, limit=limit, offset=offset)
    result = {"packages": rows, "total": total, "limit": limit, "offset": offset}
    cache.set_json(ck, result, ttl_seconds=300)
    return result


@router.get("/packages/{pkg_id}/{version}", summary="包详情")
def api_get_package(pkg_id: str, version: str):
    from modstore_server import cache

    ck = f"catalog:v1:pkg:{pkg_id}:{version}"
    cached = cache.get_json(ck)
    if cached is not None:
        return cached
    r = get_package(pkg_id, version)
    if not r:
        raise HTTPException(404, "未找到该版本")
    cache.set_json(ck, r, ttl_seconds=600)
    return r


@router.get("/packages/by-id/{pkg_id}/versions", summary="同 id 下所有版本（含 draft/stable）")
def api_package_versions(pkg_id: str):
    pid = (pkg_id or "").strip()
    if not pid:
        raise HTTPException(400, "pkg_id 无效")
    return {"pkg_id": pid, "versions": list_versions(pid)}


class PromoteBody(BaseModel):
    from_version: str = Field(..., min_length=1, description="要晋升的 draft 版本号")


@router.post("/packages/{pkg_id}/promote", summary="将 draft 版本复制为新的 stable（semver patch+1）")
def api_promote_package(
    pkg_id: str,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    body: PromoteBody = Body(...),
):
    _require_upload(authorization)
    pid = (pkg_id or "").strip()
    if not pid:
        raise HTTPException(400, "pkg_id 无效")
    try:
        saved = promote_draft_to_stable(pid, body.from_version.strip())
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    if str(saved.get("artifact") or "").strip().lower() == "employee_pack":
        sf = get_session_factory()
        with sf() as db:
            upsert_catalog_item_from_xc_package_dict(db, saved, author_id=None)
            db.commit()
    _invalidate_catalog_list_caches(saved.get("id"), saved.get("version"))
    return {"ok": True, "package": saved}


@router.get("/index.json", summary="轻量全量索引")
def api_index_json():
    from modstore_server import cache
    from modstore_server.catalog_public_index import build_public_index_packages

    p = packages_path()
    # Key includes file mtime so a new upload naturally produces a new cache key;
    # old key expires in 60 s, effectively rate-limiting filesystem reads.
    mtime = int(p.stat().st_mtime) if p.is_file() else 0
    # When the market DB is available, visibility follows ``catalog_items.is_public``;
    # do not serve a stale cached index across listing changes.
    from modstore_server.catalog_public_index import _public_pkg_ids_from_db

    if _public_pkg_ids_from_db() is not None:
        return {"packages": build_public_index_packages()}

    ck = f"catalog:v1:index:{mtime}"
    cached = cache.get_json(ck)
    if cached is not None:
        return cached
    result = {"packages": build_public_index_packages()}
    cache.set_json(ck, result, ttl_seconds=60)
    return result


@router.get("/packages/{pkg_id}/{version}/download", summary="下载已上传包文件")
def api_download(pkg_id: str, version: str):
    from modstore_server.catalog_store import files_dir

    r = get_package(pkg_id, version)
    if not r:
        raise HTTPException(404, "未找到")
    name = r.get("stored_filename")
    if not name:
        raise HTTPException(404, "该记录无本地文件")
    path = files_dir() / str(name)
    if not path.is_file():
        raise HTTPException(404, "文件缺失")
    from fastapi.responses import FileResponse

    return FileResponse(path, filename=path.name, media_type="application/zip")


@router.post("/packages", summary="登记新包（multipart：metadata JSON + file）")
async def api_upload_package(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    metadata: str = Form(..., description="JSON 字符串，字段与 PackageRecord 一致"),
    file: UploadFile = File(...),
):
    _require_upload(authorization)
    import json

    try:
        meta = json.loads(metadata)
    except json.JSONDecodeError:
        raise HTTPException(400, "metadata 须为 JSON")
    if not isinstance(meta, dict):
        raise HTTPException(400, "metadata 须为对象")
    if not (str(meta.get("id") or "").strip() and str(meta.get("version") or "").strip()):
        raise HTTPException(400, "metadata 须含 id 与 version")
    rec: Dict[str, Any] = dict(meta)
    artifact = str(rec.get("artifact") or "").strip().lower()
    has_explicit_v2 = isinstance(rec.get("employee_config_v2"), dict)
    is_employee_upload = artifact == "employee_pack" or has_explicit_v2
    v2cfg = extract_or_upgrade_v2_config(rec) if is_employee_upload else {}
    sf = get_session_factory()
    if is_employee_upload:
        with sf() as db:
            errs = validate_v2_config(
                v2cfg,
                db=db,
                user_id=None,
                require_workflow_heart=True,
                require_workflow_sandbox=True,
            )
        if errs:
            raise HTTPException(400, "V2 配置校验失败: " + "; ".join(errs))
        rec["employee_config_v2"] = v2cfg
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".xcmod", ".xcemp", ".zip"}:
        raise HTTPException(400, "file 须为 .xcmod / .xcemp / .zip")

    raw_bytes = await file.read()

    from modman.artifact_constants import ARTIFACT_MOD, normalize_artifact
    from modman.employee_sandbox import (
        assert_employee_sandbox_passes_for_catalog_zip,
        catalog_require_employee_sandbox,
        catalog_sandbox_probe_http,
    )

    if catalog_require_employee_sandbox() and normalize_artifact(rec) == ARTIFACT_MOD:
        fd, gate_tmp = tempfile.mkstemp(suffix=".zip")
        os.close(fd)
        gate_path = Path(gate_tmp)
        try:
            gate_path.write_bytes(raw_bytes)
            backend_base = None
            if catalog_sandbox_probe_http():
                try:
                    from modman.repo_config import load_config, resolved_xcagi_backend_url

                    backend_base = resolved_xcagi_backend_url(load_config()).strip() or None
                except Exception:
                    backend_base = None
            assert_employee_sandbox_passes_for_catalog_zip(
                gate_path,
                probe_http=catalog_sandbox_probe_http() and bool(backend_base),
                backend_base=backend_base,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        finally:
            gate_path.unlink(missing_ok=True)

    audit_meta: Dict[str, Any] = {}
    art = str(rec.get("artifact") or "").strip().lower()
    if art in ("mod", "employee_pack"):
        audit_meta["artifact"] = art
    if is_employee_upload and v2cfg:
        audit_meta["employee_config_v2"] = v2cfg
    probe = str(rec.get("probe_mod_id") or "").strip()
    if probe:
        audit_meta["probe_mod_id"] = probe

    from modstore_server.package_sandbox_audit import run_package_audit_async

    rep = await run_package_audit_async(raw_bytes, audit_meta if audit_meta else None)
    if not rep.get("ok"):
        raise HTTPException(400, str(rep.get("error") or "包审核失败"))
    summary = rep.get("summary") or {}
    if not summary.get("pass"):
        raise HTTPException(400, "五维审核未通过，禁止上架")

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td) / (file.filename or "upload.bin")
        tmp.write_bytes(raw_bytes)
        if str(rec.get("artifact") or "").strip().lower() == "employee_pack":
            from modstore_server.catalog_store import package_manifest_alignment_errors

            align_errs = package_manifest_alignment_errors(rec, tmp)
            if align_errs:
                raise HTTPException(400, "员工包 metadata 与包内 manifest 不一致: " + "; ".join(align_errs))
        saved = append_package(rec, tmp)

    sf2 = get_session_factory()
    with sf2() as db:
        upsert_catalog_item_from_xc_package_dict(db, saved, author_id=None)
        db.commit()

    # Invalidate all list/index caches; individual detail keys expire on their own TTL.
    _invalidate_catalog_list_caches(saved.get("id"), saved.get("version"))

    embedding_text = f"{saved.get('name', '')} {saved.get('description', '')}"
    if embedding_text.strip():
        item_id = f"{saved.get('id')}:{saved.get('version')}"
        insert_embedding(
            item_id=item_id,
            text=embedding_text,
            metadata={
                "pkg_id": saved.get("id"),
                "version": saved.get("version"),
                "artifact": saved.get("artifact", "mod"),
                "industry": saved.get("industry", "通用"),
            },
        )

    return {"ok": True, "package": saved}


@router.get("/catalog/industries", summary="获取标准化行业分类树")
def api_get_industries():
    return {"industries": get_industry_tree()}


@router.get("/catalog/search-semantic", summary="语义搜索商品")
def api_search_semantic(
    q: str = Query(..., description="搜索查询文本"),
    artifact: Optional[str] = Query(None, description="按类型过滤"),
    industry: Optional[str] = Query(None, description="按行业过滤"),
    limit: int = Query(20, ge=1, le=100),
):
    filter_meta = {}
    if artifact:
        filter_meta["artifact"] = artifact
    if industry:
        filter_meta["industry"] = industry

    results = query_similar(q, limit=limit, filter_meta=filter_meta if filter_meta else None)
    return {"results": results, "total": len(results)}


@router.get("/catalog/recommend-similar", summary="相似商品推荐")
def api_recommend_similar(
    id: str = Query(..., description="商品 ID"),
    limit: int = Query(10, ge=1, le=50),
):
    item_id = (id or "").strip()
    if not item_id:
        raise HTTPException(400, "id 参数不能为空")

    pkg = get_package(item_id, "")
    if not pkg:
        rows, _ = list_packages(limit=500, offset=0)
        pkg = next((r for r in rows if r.get("id") == item_id), None)

    if not pkg:
        raise HTTPException(404, "未找到商品")

    text = f"{pkg.get('name', '')} {pkg.get('description', '')}"
    results = query_similar(text, limit=limit + 1)

    current_id = pkg.get("id")
    filtered = [r for r in results if r.get("metadata", {}).get("pkg_id") != current_id]
    return {"results": filtered[:limit], "total": len(filtered[:limit])}
