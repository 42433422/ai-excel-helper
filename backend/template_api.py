"""
模板预览 API：元数据与文件在 PostgreSQL ``document_templates``（``role=excel_export``）。
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.document_templates_store import (
    count_preview_templates,
    create_preview_from_editor_payload,
    get_preview_template,
    list_preview_templates,
    replace_preview_editor_payload,
    resolve_preview_file_path,
    save_binary_under_document_templates,
    slim_preview_row,
    soft_delete_preview_template,
    update_preview_metadata,
    upsert_preview_template,
)
from backend.excel_template_parser import parse_excel_template
from backend.template_upload import (
    generate_logo_thumbnail,
    get_file_info,
    validate_upload_file,
)
from backend.word_template_parser import parse_word_template

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/templates", tags=["templates"])


class TemplateCreateRequest(BaseModel):
    name: str
    type: str = ""
    category: str = ""
    template_type: str = ""
    business_scope: str = ""
    fields: list[dict[str, Any]] = Field(default_factory=list)
    source: str = "template-preview"


class TemplateUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    metadata: dict[str, Any] | None = None


class TemplateFieldUpdateRequest(BaseModel):
    field_name: str
    field_type: str
    display_name: str | None = None
    required: bool = False
    default_value: str | None = None
    validation_rules: dict[str, Any] | None = None
    mapping_config: dict[str, Any] | None = None
    sort_order: int = 0


class TemplateReplacePayload(BaseModel):
    template_id: str
    name: str | None = None
    fields: list[dict[str, Any]] | None = None
    preview_data: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    template_type: str | None = None
    business_scope: str | None = None
    replace_mode: bool = False


def _field_dict_from_request(f: TemplateFieldUpdateRequest, template_slug: str) -> dict[str, Any]:
    d = f.model_dump()
    d["id"] = str(uuid.uuid4())
    d["template_id"] = f"db:{template_slug}"
    return d


def _fields_from_editor_payload(fields: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for x in fields or []:
        if isinstance(x, dict):
            out.append(dict(x))
    return out


def _compat_detail(d: dict[str, Any]) -> dict[str, Any]:
    """兼容旧 ``Template.to_dict`` + 前端 ``success`` / ``template``。"""
    if not d:
        return {}
    slug = d.get("slug") or ""
    base = dict(d)
    base["success"] = True
    base["template"] = d
    # 旧字段名
    base["id"] = d.get("id") or f"db:{slug}"
    return base


@router.on_event("startup")
async def startup_event():
    """模板预览已用 PostgreSQL，不再初始化 SQLite ``templates.db``。"""
    return


@router.get("/list")
async def list_templates_compat_alias(
    type: str | None = Query(None, description="Filter by template type"),
    status: str | None = Query(None, description="Filter by template status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """兼容旧路径 ``GET /api/templates/list``（与 ``GET /api/templates`` 相同）。"""
    return await list_templates_endpoint(type=type, status=status, limit=limit, offset=offset)


@router.get("")
async def list_templates_endpoint(
    type: str | None = Query(None, description="Filter by template type"),
    status: str | None = Query(None, description="Filter by template status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    total = count_preview_templates(template_type=type, status=status)
    rows = list_preview_templates(template_type=type, status=status, limit=limit, offset=offset)
    slim = [slim_preview_row(r) for r in rows]
    return {
        "success": True,
        "templates": slim,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{template_id}")
async def get_template_endpoint(template_id: str):
    if template_id in ("list",):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="请使用 GET /api/templates 列表")
    d = get_preview_template(template_id)
    if not d:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"模板不存在：{template_id}")
    return _compat_detail(d)


@router.put("/{template_id}")
async def update_template_endpoint(template_id: str, request: TemplateUpdateRequest):
    d = get_preview_template(template_id)
    if not d:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"模板不存在：{template_id}")
    upd = request.model_dump(exclude_unset=True)
    merged = {**upd, "name": upd.get("name") or d.get("name")}
    if "metadata" in upd and upd["metadata"] is not None:
        meta = dict(d.get("metadata") or {})
        meta.update(upd["metadata"])
        merged["metadata"] = meta
    out = update_preview_metadata(template_id, merged)
    if not out:
        raise HTTPException(status_code=500, detail="更新失败")
    return _compat_detail(out)


@router.delete("/{template_id}")
async def delete_template_endpoint(template_id: str):
    if not get_preview_template(template_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"模板不存在：{template_id}")
    ok = soft_delete_preview_template(template_id)
    if ok:
        return {"success": True, "message": "模板已成功删除", "template_id": template_id}
    raise HTTPException(status_code=500, detail="删除模板失败")


@router.post("/create")
async def create_template_post(body: TemplateCreateRequest):
    d = create_preview_from_editor_payload(
        name=body.name,
        category=body.category or "excel",
        template_type=body.template_type or body.type or "export",
        business_scope=body.business_scope or "",
        fields=body.fields,
        source=body.source,
    )
    return {"success": True, "template": d, **_compat_detail(d)}


@router.post("/update")
async def update_template_post(body: TemplateReplacePayload):
    tid = body.template_id
    if body.replace_mode:
        d = replace_preview_editor_payload(
            tid,
            {
                "name": body.name,
                "fields": body.fields,
                "preview_data": body.preview_data,
                "metadata": body.metadata,
                "template_type": body.template_type,
                "business_scope": body.business_scope,
            },
        )
    else:
        d = update_preview_metadata(
            tid,
            {
                "name": body.name,
                "template_type": body.template_type,
                "business_scope": body.business_scope,
                "metadata": body.metadata,
            },
        )
    if not d:
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"success": True, "template": d, **_compat_detail(d)}


@router.post("/delete")
async def delete_template_post(payload: dict[str, Any]):
    tid = (payload.get("template_id") or payload.get("id") or "").strip()
    if not tid:
        raise HTTPException(status_code=400, detail="缺少 template_id")
    return await delete_template_endpoint(tid)


@router.put("/{template_id}/fields")
async def update_template_fields_endpoint(template_id: str, fields: list[TemplateFieldUpdateRequest]):
    d = get_preview_template(template_id)
    if not d:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"模板不存在：{template_id}")
    slug = str(d.get("slug") or "")
    new_fields = [_field_dict_from_request(f, slug) for f in fields]
    out = replace_preview_editor_payload(
        template_id,
        {
            "name": d.get("name"),
            "fields": new_fields,
            "preview_data": d.get("preview_data") or {},
            "metadata": d.get("metadata") or {},
            "template_type": d.get("template_type"),
            "business_scope": d.get("business_scope"),
        },
    )
    if not out:
        raise HTTPException(status_code=500, detail="更新字段失败")
    return {"success": True, "template_id": d.get("id"), "fields": out.get("fields") or []}


@router.post("/{template_id}/preview")
async def preview_template_endpoint(template_id: str):
    d = get_preview_template(template_id)
    if not d:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"模板不存在：{template_id}")
    fp = resolve_preview_file_path(d.get("file_path") or d.get("path") or "")
    if not fp or not fp.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"模板文件不存在：{d.get('file_path')}")
    typ = (d.get("type") or "").lower()
    if typ == "excel":
        preview_data = parse_excel_template(fp)
    elif typ == "word":
        preview_data = parse_word_template(fp)
    else:
        preview_data = {
            "file_name": fp.name,
            "type": "logo",
            "thumbnail_path": d.get("thumbnail_path"),
        }
    return {"success": True, "template_id": d.get("id"), "preview": preview_data}


@router.post("/upload")
async def upload_template(
    file: UploadFile = File(..., description="Template file (Excel, Word, or Logo image)"),
    type: str = Form(..., description="Template type: excel, word, or logo"),
    name: str | None = Form(None, description="Template name"),
    description: str | None = Form(None, description="Template description"),
    created_by: str | None = Form(None, description="Creator identifier"),
):
    if type not in ["excel", "word", "logo"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的模板类型：{type}，支持的类型：excel, word, logo",
        )

    is_valid, error_message = await validate_upload_file(file, type)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_message)

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="空文件")

    ext = Path(file.filename or "").suffix.lower() or (".png" if type == "logo" else ".xlsx")
    fname = f"{uuid.uuid4().hex[:16]}{ext}"
    try:
        relpath = save_binary_under_document_templates(fname, raw)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存文件失败：{e}") from e

    fp = resolve_preview_file_path(relpath)
    if not fp or not fp.is_file():
        raise HTTPException(status_code=500, detail="保存后无法解析文件路径")

    file_info = get_file_info(fp)
    display_name = (name or file.filename or fname).strip()
    legacy_id = str(uuid.uuid4())
    thumbnail_path = None
    if type == "logo":
        thumb = generate_logo_thumbnail(fp)
        if thumb:
            try:
                from backend.document_template_service import fhd_repo_root
                import os

                ws = (os.environ.get("WORKSPACE_ROOT") or "").strip()
                if ws:
                    thumbnail_path = str(thumb.resolve().relative_to(Path(ws).resolve())).replace("\\", "/")
                else:
                    thumbnail_path = str(thumb.resolve().relative_to(fhd_repo_root().resolve())).replace(
                        "\\", "/"
                    )
            except Exception:
                thumbnail_path = str(thumb)

    try:
        if type == "excel":
            parse_result = parse_excel_template(fp)
            fields = []
            for sheet in parse_result.get("sheets", []):
                for header in sheet.get("headers", []):
                    fields.append(
                        {
                            "id": str(uuid.uuid4()),
                            "template_id": f"db:",
                            "field_name": header.get("name"),
                            "field_type": header.get("data_type", "string"),
                            "display_name": header.get("display_name"),
                            "required": header.get("required", False),
                            "mapping_config": {"sheet": sheet.get("name"), "column": header.get("column")},
                            "sort_order": header.get("column", 0),
                        }
                    )
            ep: dict[str, Any] = {
                "fields": fields,
                "preview_data": {},
                "metadata": parse_result,
                "description": description,
                "status": "parsed",
                "file_size": file_info["size"],
                "file_size_human": file_info["size_human"],
                "mime_type": file.content_type,
                "original_filename": file.filename,
                "created_by": created_by,
                "version": 1,
            }
            row = upsert_preview_template(
                slug=None,
                display_name=display_name,
                storage_relpath=relpath,
                file_format="xlsx",
                business_scope=None,
                editor_payload=ep,
                legacy_sqlite_id=legacy_id,
            )
            for i, fld in enumerate(row.get("fields") or []):
                if isinstance(fld, dict):
                    fld["template_id"] = row.get("id")
            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={
                    "success": True,
                    "template_id": row.get("id"),
                    "name": row.get("name"),
                    "type": row.get("type"),
                    "status": row.get("status"),
                    "fields": row.get("fields") or [],
                    "metadata": row.get("metadata"),
                    "created_at": row.get("created_at"),
                },
            )

        if type == "word":
            parse_result = parse_word_template(fp)
            fields = []
            for idx, placeholder in enumerate(parse_result.get("structure", {}).get("placeholders", [])):
                fields.append(
                    {
                        "id": str(uuid.uuid4()),
                        "template_id": f"db:",
                        "field_name": placeholder,
                        "field_type": "string",
                        "display_name": placeholder,
                        "required": False,
                        "sort_order": idx,
                    }
                )
            ep = {
                "fields": fields,
                "preview_data": {},
                "metadata": parse_result,
                "description": description,
                "status": "parsed",
                "file_size": file_info["size"],
                "file_size_human": file_info["size_human"],
                "mime_type": file.content_type,
                "original_filename": file.filename,
                "created_by": created_by,
                "version": 1,
            }
            row = upsert_preview_template(
                slug=None,
                display_name=display_name,
                storage_relpath=relpath,
                file_format="docx",
                business_scope=None,
                editor_payload=ep,
                legacy_sqlite_id=legacy_id,
            )
            for fld in row.get("fields") or []:
                if isinstance(fld, dict):
                    fld["template_id"] = row.get("id")
            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={
                    "success": True,
                    "template_id": row.get("id"),
                    "name": row.get("name"),
                    "type": row.get("type"),
                    "status": row.get("status"),
                    "fields": row.get("fields") or [],
                    "metadata": row.get("metadata"),
                    "created_at": row.get("created_at"),
                },
            )

        # logo
        ep = {
            "fields": [],
            "preview_data": {},
            "metadata": {},
            "description": description,
            "status": "active",
            "kind": "logo",
            "file_size": file_info["size"],
            "file_size_human": file_info["size_human"],
            "mime_type": file.content_type,
            "original_filename": file.filename,
            "created_by": created_by,
            "thumbnail_path": thumbnail_path,
        }
        fmt = ext.lstrip(".")[:16] or "png"
        row = upsert_preview_template(
            slug=None,
            display_name=display_name,
            storage_relpath=relpath,
            file_format=fmt,
            business_scope=None,
            editor_payload=ep,
            legacy_sqlite_id=legacy_id,
        )
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "success": True,
                "template_id": row.get("id"),
                "name": row.get("name"),
                "type": row.get("type"),
                "status": row.get("status"),
                "fields": [],
                "metadata": row.get("metadata"),
                "created_at": row.get("created_at"),
            },
        )
    except Exception as e:
        logger.exception("模板解析失败")
        try:
            fp.unlink(missing_ok=True)
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"模板解析失败：{str(e)}") from e
