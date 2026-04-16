"""
业务文档模板库：读列表（公开）与上传登记（需写令牌）。
"""

from __future__ import annotations

import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile

from backend.db_write_auth import verify_db_write_token_header
from backend.document_template_service import fhd_repo_root, list_templates

logger = logging.getLogger(__name__)

public_router = APIRouter(prefix="/api/document-templates", tags=["document-templates"])
admin_router = APIRouter(prefix="/api/admin/document-templates", tags=["admin-document-templates"])

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}$", re.I)


@public_router.get("")
@public_router.get("/")
async def list_document_templates(
    role: str | None = Query(
        None,
        description="price_list_docx | sales_contract_docx | excel_export（模板预览 Excel/Word）",
    ),
    kind: str | None = Query(
        None,
        description="当 role=excel_export 时可选：word（仅 .docx）| excel（.xlsx/.xlsm）",
    ),
) -> dict[str, Any]:
    rkey = (role or "").strip() or None
    kind_key = (kind or "").strip().lower() or None
    if kind_key and kind_key not in ("word", "excel"):
        raise HTTPException(status_code=400, detail="kind 须为 word 或 excel")
    rows = list_templates(rkey, kind=kind_key if rkey == "excel_export" else None)
    default_slug: str | None = None
    for r in rows:
        if r.get("is_default"):
            default_slug = r["slug"]
            break
    if default_slug is None and rows:
        default_slug = rows[0]["slug"]
    return {"success": True, "data": rows, "default_id": default_slug}


def _save_uploaded_docx(content: bytes, original_name: str) -> tuple[str, Path]:
    """返回 ``(storage_relpath, 绝对路径)``。"""
    ext = Path(original_name or "").suffix.lower()
    if ext != ".docx":
        raise HTTPException(status_code=400, detail="仅支持 .docx")
    fname = f"{uuid.uuid4().hex}{ext}"

    ws = (os.environ.get("WORKSPACE_ROOT") or "").strip()
    if ws:
        base = Path(ws).expanduser() / "uploads" / "document_templates"
        base.mkdir(parents=True, exist_ok=True)
        dest = base / fname
        dest.write_bytes(content)
        return f"uploads/document_templates/{fname}", dest
    base = fhd_repo_root() / "424" / "document_templates"
    base.mkdir(parents=True, exist_ok=True)
    dest = base / fname
    dest.write_bytes(content)
    return f"424/document_templates/{fname}", dest


@admin_router.post("")
@admin_router.post("/")
async def admin_upload_document_template(
    request: Request,
    file: UploadFile = File(...),
    role: str = Form(...),
    slug: str = Form(...),
    display_name: str = Form(...),
    is_default: str = Form("false"),
) -> dict[str, Any]:
    verify_db_write_token_header(request)
    role = (role or "").strip()
    slug = (slug or "").strip()
    display_name = (display_name or "").strip()
    if role not in ("price_list_docx", "sales_contract_docx"):
        raise HTTPException(status_code=400, detail="role 须为 price_list_docx 或 sales_contract_docx")
    if not _SLUG_RE.match(slug):
        raise HTTPException(
            status_code=400,
            detail="slug 须为 1–63 位字母数字、下划线或连字符，且不以连字符开头",
        )
    if not display_name:
        raise HTTPException(status_code=400, detail="display_name 不能为空")

    raw = await file.read()
    if not raw or len(raw) > 15 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件为空或超过 15MB")

    relpath, _abs = _save_uploaded_docx(raw, file.filename or "template.docx")
    def_flag = str(is_default).strip().lower() in ("1", "true", "yes", "on")

    try:
        from sqlalchemy import text

        from backend.database import get_sync_engine

        eng = get_sync_engine()
        with eng.begin() as conn:
            if def_flag:
                conn.execute(
                    text(
                        "UPDATE document_templates SET is_default = false, updated_at = now() "
                        "WHERE role = :role AND slug <> :slug"
                    ),
                    {"role": role, "slug": slug},
                )
            conn.execute(
                text(
                    """
                    INSERT INTO document_templates
                        (slug, display_name, role, storage_relpath, is_default, is_active, sort_order)
                    VALUES
                        (:slug, :dn, :role, :path, :def, true, 100)
                    ON CONFLICT (slug) DO UPDATE SET
                        display_name = EXCLUDED.display_name,
                        role = EXCLUDED.role,
                        storage_relpath = EXCLUDED.storage_relpath,
                        is_default = EXCLUDED.is_default,
                        is_active = true,
                        updated_at = now()
                    """
                ),
                {"slug": slug, "dn": display_name, "role": role, "path": relpath, "def": def_flag},
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("admin document-templates upload failed")
        raise HTTPException(status_code=500, detail=f"写入数据库失败：{e}") from e

    return {"success": True, "data": {"slug": slug, "role": role, "storage_relpath": relpath}}
