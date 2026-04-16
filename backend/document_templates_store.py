"""
PostgreSQL ``document_templates`` 的模板预览（原 SQLite templates）读写。

- 业务 Word：``price_list_docx`` / ``sales_contract_docx``（与 ``document_template_service`` 一致）
- 网格/导出 Excel·Word：``role = excel_export``，``editor_payload`` 存 fields / preview_data / metadata
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ROLE_EXCEL_EXPORT = "excel_export"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _slugify_token(s: str, max_len: int = 48) -> str:
    x = re.sub(r"[^a-z0-9]+", "-", (s or "").lower().strip(), flags=re.I)
    x = re.sub(r"-{2,}", "-", x).strip("-") or "tpl"
    return x[:max_len].strip("-") or "tpl"


def _make_unique_slug(base: str, reserved: set[str], engine: Any) -> str:
    from sqlalchemy import text

    b = _slugify_token(base, 40) or "tpl"
    cand = b
    n = 0
    while cand in reserved:
        n += 1
        cand = f"{b}-{n}"[:63]
    with engine.connect() as conn:
        for _ in range(80):
            r = conn.execute(text("SELECT 1 FROM document_templates WHERE slug = :s LIMIT 1"), {"s": cand}).first()
            if r is None:
                return cand
            n += 1
            cand = f"{b}-{n}"[:63]
    return f"{b}-{uuid.uuid4().hex[:8]}"[:63]


def _iso(dt: Any) -> Any:
    if dt is None:
        return None
    if hasattr(dt, "isoformat"):
        try:
            return dt.isoformat()
        except Exception:
            return str(dt)
    return dt


def _row_to_preview_dict(r: Any) -> dict[str, Any]:
    ep = r.get("editor_payload") if isinstance(r.get("editor_payload"), dict) else {}
    fmt = str(r.get("file_format") or "docx").lower()
    if ep.get("kind") == "logo" or fmt in ("png", "jpg", "jpeg", "gif", "svg", "webp"):
        category = "label"
        typ = "logo"
    elif fmt in ("xlsx", "xlsm"):
        category = "excel"
        typ = "excel"
    elif fmt == "docx":
        category = "word"
        typ = "word"
    else:
        category = "excel"
        typ = "excel"
    fields = ep.get("fields") if isinstance(ep.get("fields"), list) else []
    preview_data = ep.get("preview_data") if isinstance(ep.get("preview_data"), dict) else {}
    metadata = ep.get("metadata") if isinstance(ep.get("metadata"), dict) else {}
    slug = str(r["slug"])
    return {
        "id": f"db:{slug}",
        "slug": slug,
        "name": str(r.get("display_name") or slug),
        "type": typ,
        "category": category,
        "file_path": str(r.get("storage_relpath") or ""),
        "path": str(r.get("storage_relpath") or ""),
        "description": ep.get("description"),
        "version": ep.get("version", 1),
        "parent_template_id": ep.get("parent_template_id"),
        "status": ep.get("status", "active" if r.get("is_active", True) else "archived"),
        "file_size": ep.get("file_size"),
        "file_size_human": ep.get("file_size_human"),
        "mime_type": ep.get("mime_type"),
        "original_filename": ep.get("original_filename"),
        "thumbnail_path": ep.get("thumbnail_path"),
        "created_at": _iso(r.get("created_at")),
        "updated_at": _iso(r.get("updated_at")),
        "created_by": ep.get("created_by"),
        "metadata": metadata,
        "metadata_json": metadata,
        "fields": fields,
        "preview_data": preview_data,
        "business_scope": str(r.get("business_scope") or ep.get("business_scope") or ""),
        "template_type": ep.get("template_type") or "",
        "source": ep.get("source", "db"),
        "role": str(r.get("role") or ""),
        "is_active": bool(r.get("is_active", True)),
        "uuid_id": str(r.get("id") or ""),
        "storage_relpath": str(r.get("storage_relpath") or ""),
    }


def slim_preview_row(d: dict[str, Any]) -> dict[str, Any]:
    """列表用：省略大体积 fields / preview_data。"""
    x = dict(d)
    x["fields"] = []
    x["preview_data"] = {}
    meta = x.get("metadata")
    if isinstance(meta, dict) and len(json.dumps(meta, ensure_ascii=False)) > 4000:
        x["metadata"] = {"_truncated": True}
        x["metadata_json"] = x["metadata"]
    return x


def _parse_frontend_id(template_id: str) -> str:
    tid = (template_id or "").strip()
    if tid.startswith("db:"):
        return tid[3:].strip()
    return tid


def count_preview_templates(
    *,
    template_type: str | None = None,
    status: str | None = None,
) -> int:
    from sqlalchemy import inspect, text

    from backend.database import get_sync_engine

    eng = get_sync_engine()
    insp = inspect(eng)
    if "document_templates" not in insp.get_table_names():
        return 0
    role = ROLE_EXCEL_EXPORT
    sql = (
        "SELECT COUNT(*)::int AS c FROM document_templates WHERE is_active = true AND role = :role "
    )
    params: dict[str, Any] = {"role": role}
    if template_type in ("excel", "word"):
        if template_type == "excel":
            sql += " AND file_format IN ('xlsx', 'xlsm')"
        else:
            sql += " AND file_format = 'docx'"
    if status:
        sql += (
            " AND (COALESCE(editor_payload->>'status', CASE WHEN is_active THEN 'active' ELSE 'archived' END) = :st)"
        )
        params["st"] = status
    try:
        with eng.connect() as conn:
            r = conn.execute(text(sql), params).mappings().first()
            return int(r["c"]) if r else 0
    except Exception as e:
        logger.warning("document_templates_store.count_preview_templates: %s", e)
        return 0


def list_preview_templates(
    *,
    template_type: str | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]]:
    from sqlalchemy import inspect, text

    from backend.database import get_sync_engine

    eng = get_sync_engine()
    insp = inspect(eng)
    if "document_templates" not in insp.get_table_names():
        return []
    role = ROLE_EXCEL_EXPORT
    sql = (
        "SELECT id::text, slug, display_name, role, storage_relpath, is_default, is_active, sort_order, "
        "file_format, business_scope, editor_payload, legacy_sqlite_id, created_at, updated_at "
        "FROM document_templates WHERE is_active = true AND role = :role "
    )
    params: dict[str, Any] = {"role": role}
    if template_type in ("excel", "word"):
        if template_type == "excel":
            sql += " AND file_format IN ('xlsx', 'xlsm')"
        else:
            sql += " AND file_format = 'docx'"
    if status:
        sql += (
            " AND (COALESCE(editor_payload->>'status', CASE WHEN is_active THEN 'active' ELSE 'archived' END) = :st)"
        )
        params["st"] = status
    sql += " ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST LIMIT :lim OFFSET :off"
    params["lim"] = min(max(limit, 1), 1000)
    params["off"] = max(offset, 0)
    out: list[dict[str, Any]] = []
    try:
        with eng.connect() as conn:
            for row in conn.execute(text(sql), params).mappings().all():
                d = dict(row)
                if isinstance(d.get("editor_payload"), str):
                    try:
                        d["editor_payload"] = json.loads(d["editor_payload"])
                    except Exception:
                        d["editor_payload"] = {}
                ep = d.get("editor_payload") if isinstance(d.get("editor_payload"), dict) else {}
                out.append(_row_to_preview_dict(d))
    except Exception as e:
        logger.warning("document_templates_store.list_preview_templates: %s", e)
    return out


def get_preview_template(template_id: str) -> dict[str, Any] | None:
    from sqlalchemy import inspect, text

    from backend.database import get_sync_engine

    slug = _parse_frontend_id(template_id)
    if not slug:
        return None
    eng = get_sync_engine()
    insp = inspect(eng)
    if "document_templates" not in insp.get_table_names():
        return None
    try:
        with eng.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT id::text, slug, display_name, role, storage_relpath, is_default, is_active, sort_order, "
                    "file_format, business_scope, editor_payload, legacy_sqlite_id, created_at, updated_at "
                    "FROM document_templates WHERE slug = :s OR legacy_sqlite_id = :s2 LIMIT 1"
                ),
                {"s": slug, "s2": slug},
            ).mappings().first()
        if not row:
            return None
        d = dict(row)
        if isinstance(d.get("editor_payload"), str):
            try:
                d["editor_payload"] = json.loads(d["editor_payload"])
            except Exception:
                d["editor_payload"] = {}
        return _row_to_preview_dict(d)
    except Exception as e:
        logger.warning("document_templates_store.get_preview_template: %s", e)
        return None


def upsert_preview_template(
    *,
    slug: str | None,
    display_name: str,
    storage_relpath: str,
    file_format: str,
    business_scope: str | None,
    editor_payload: dict[str, Any] | None,
    legacy_sqlite_id: str | None = None,
) -> dict[str, Any]:
    from sqlalchemy import text

    from backend.database import get_sync_engine

    eng = get_sync_engine()
    reserved: set[str] = set()
    sl = (slug or "").strip() or _make_unique_slug(_slugify_token(display_name), reserved, eng)
    sl = _slugify_token(sl, 62)
    ep = editor_payload if isinstance(editor_payload, dict) else {}
    ff = (file_format or "xlsx").lower()
    bs = (business_scope or "").strip() or None
    leg = (legacy_sqlite_id or "").strip() or None
    sql = text(
        """
        INSERT INTO document_templates
            (slug, display_name, role, storage_relpath, is_default, is_active, sort_order,
             file_format, business_scope, editor_payload, legacy_sqlite_id)
        VALUES
            (:slug, :dn, :role, :path, false, true, 100, :ff, :bs, CAST(:ep AS jsonb), :leg)
        ON CONFLICT (slug) DO UPDATE SET
            display_name = EXCLUDED.display_name,
            storage_relpath = EXCLUDED.storage_relpath,
            file_format = EXCLUDED.file_format,
            business_scope = EXCLUDED.business_scope,
            editor_payload = EXCLUDED.editor_payload,
            legacy_sqlite_id = COALESCE(EXCLUDED.legacy_sqlite_id, document_templates.legacy_sqlite_id),
            is_active = true,
            updated_at = now()
        """
    )
    with eng.begin() as conn:
        conn.execute(
            sql,
            {
                "slug": sl,
                "dn": display_name,
                "role": ROLE_EXCEL_EXPORT,
                "path": storage_relpath,
                "ff": ff[:16],
                "bs": bs,
                "ep": json.dumps(ep, ensure_ascii=False),
                "leg": leg,
            },
        )
    return get_preview_template(sl) or {}


def soft_delete_preview_template(template_id: str) -> bool:
    from sqlalchemy import text

    from backend.database import get_sync_engine

    slug = _parse_frontend_id(template_id)
    if not slug:
        return False
    eng = get_sync_engine()
    try:
        with eng.begin() as conn:
            r = conn.execute(
                text(
                    "UPDATE document_templates SET is_active = false, updated_at = now() "
                    "WHERE role = :r AND (slug = :s OR legacy_sqlite_id = :s)"
                ),
                {"s": slug, "r": ROLE_EXCEL_EXPORT},
            )
            return (getattr(r, "rowcount", None) or 0) > 0
    except Exception as e:
        logger.warning("document_templates_store.soft_delete_preview_template: %s", e)
        return False


def update_preview_metadata(template_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    from sqlalchemy import text

    from backend.database import get_sync_engine

    cur = get_preview_template(template_id)
    if not cur:
        return None
    slug = str(cur.get("slug") or _parse_frontend_id(template_id))
    meta = dict(cur.get("metadata") or cur.get("metadata_json") or {})
    if updates.get("metadata") is not None and isinstance(updates["metadata"], dict):
        meta.update(updates["metadata"])
    full = {
        "fields": cur.get("fields") or [],
        "preview_data": cur.get("preview_data") or {},
        "metadata": meta,
        "description": updates.get("description", cur.get("description")),
        "version": updates.get("version", cur.get("version", 1)),
        "status": updates.get("status", cur.get("status")),
        "template_type": updates.get("template_type", cur.get("template_type")),
        "business_scope": updates.get("business_scope", cur.get("business_scope")),
        "source": updates.get("source", cur.get("source")),
    }
    name = updates.get("name") or cur.get("name")
    with get_sync_engine().begin() as conn:
        conn.execute(
            text(
                "UPDATE document_templates SET display_name = :dn, business_scope = :bs, "
                "editor_payload = CAST(:ep AS jsonb), updated_at = now() WHERE slug = :slug AND role = :role"
            ),
            {
                "dn": name,
                "bs": (full.get("business_scope") or None),
                "ep": json.dumps(full, ensure_ascii=False),
                "slug": slug,
                "role": ROLE_EXCEL_EXPORT,
            },
        )
    return get_preview_template(slug)


def replace_preview_editor_payload(template_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
    """replace_mode：用新 fields / preview_data 覆盖。"""
    from sqlalchemy import text

    from backend.database import get_sync_engine

    cur = get_preview_template(template_id)
    if not cur:
        return None
    slug = str(cur.get("slug") or _parse_frontend_id(template_id))
    fields = payload.get("fields") or cur.get("fields") or []
    preview_data = payload.get("preview_data") or cur.get("preview_data") or {}
    meta = payload.get("metadata") or cur.get("metadata") or {}
    ep = {
        "fields": fields,
        "preview_data": preview_data,
        "metadata": meta,
        "template_type": payload.get("template_type", cur.get("template_type")),
        "business_scope": payload.get("business_scope", cur.get("business_scope")),
        "source": payload.get("source", "template-preview-replace"),
        "status": "active",
    }
    name = payload.get("name") or cur.get("name")
    bs = str(payload.get("business_scope") or cur.get("business_scope") or "").strip() or None
    with get_sync_engine().begin() as conn:
        conn.execute(
            text(
                "UPDATE document_templates SET display_name = :dn, business_scope = :bs, "
                "editor_payload = CAST(:ep AS jsonb), updated_at = now() WHERE slug = :slug AND role = :role"
            ),
            {"dn": name, "bs": bs, "ep": json.dumps(ep, ensure_ascii=False), "slug": slug, "role": ROLE_EXCEL_EXPORT},
        )
    return get_preview_template(slug)


def create_preview_from_editor_payload(
    *,
    name: str,
    category: str,
    template_type: str,
    business_scope: str,
    fields: list[dict[str, Any]],
    source: str,
) -> dict[str, Any]:
    """无文件时写入最小 xlsx 占位路径（WORKSPACE_ROOT/uploads/document_templates）。"""
    import os

    from openpyxl import Workbook

    slug = _make_unique_slug(_slugify_token(name), set(), get_sync_engine())
    ws_root = (os.environ.get("WORKSPACE_ROOT") or "").strip()
    if ws_root:
        base = Path(ws_root).expanduser() / "uploads" / "document_templates"
    else:
        base = _repo_root() / "424" / "document_templates"
    base.mkdir(parents=True, exist_ok=True)
    fname = f"{slug}.xlsx"
    out = base / fname
    wb = Workbook()
    wb.active.title = "Sheet1"
    wb.save(out)
    if ws_root:
        rel = f"uploads/document_templates/{fname}"
    else:
        try:
            rel = str(out.resolve().relative_to(_repo_root().resolve())).replace("\\", "/")
        except ValueError:
            rel = f"424/document_templates/{fname}"
    ep = {
        "fields": fields,
        "preview_data": {},
        "metadata": {},
        "template_type": template_type,
        "business_scope": business_scope,
        "source": source,
        "status": "active",
    }
    return upsert_preview_template(
        slug=slug,
        display_name=name,
        storage_relpath=rel.replace("\\", "/"),
        file_format="xlsx",
        business_scope=business_scope,
        editor_payload=ep,
    )


def resolve_preview_file_path(storage_relpath: str) -> Path | None:
    """解析 ``storage_relpath`` 为可读绝对路径（与 ``document_template_service`` 规则一致）。"""
    from backend.document_template_service import _resolve_storage_to_path

    return _resolve_storage_to_path((storage_relpath or "").strip())


def save_binary_under_document_templates(filename: str, data: bytes) -> str:
    """
    写入 ``424/document_templates`` 或 ``WORKSPACE_ROOT/uploads/document_templates``，
    返回规范化相对路径（供 ``storage_relpath``）。
    """
    import os

    fname = Path(filename).name
    ws_root = (os.environ.get("WORKSPACE_ROOT") or "").strip()
    if ws_root:
        base = Path(ws_root).expanduser() / "uploads" / "document_templates"
        base.mkdir(parents=True, exist_ok=True)
        dest = base / fname
        dest.write_bytes(data)
        return f"uploads/document_templates/{fname}".replace("\\", "/")
    base = _repo_root() / "424" / "document_templates"
    base.mkdir(parents=True, exist_ok=True)
    dest = base / fname
    dest.write_bytes(data)
    return f"424/document_templates/{fname}".replace("\\", "/")
