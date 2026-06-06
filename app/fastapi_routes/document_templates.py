from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from app.infrastructure.documents.template_registry import (
    list_templates as list_builtin_document_templates,
)

public_router = APIRouter(prefix="/api/document-templates", tags=["document-templates"])
admin_router = APIRouter(prefix="/api/admin/document-templates", tags=["admin-document-templates"])


@public_router.get("")
@public_router.get("/", include_in_schema=False)
def list_document_templates(role: str | None = Query(None)) -> dict[str, Any]:
    rows = list_builtin_document_templates(role)
    default_id = next(
        (x.get("slug") for x in rows if x.get("is_default")),
        rows[0].get("slug") if rows else None,
    )
    return {"success": True, "data": rows, "default_id": default_id}


@admin_router.post("")
@admin_router.post("/", include_in_schema=False)
def admin_upload_document_template() -> dict[str, Any]:
    return {"success": False, "message": "admin upload not available in recovery mode"}
