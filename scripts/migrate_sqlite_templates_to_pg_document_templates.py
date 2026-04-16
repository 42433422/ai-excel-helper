#!/usr/bin/env python3
"""
将 SQLite ``templates.db``（``templates`` / ``template_fields``）迁入 PostgreSQL ``document_templates``。

- ``role = excel_export``，``legacy_sqlite_id`` 幂等
- 文件：若路径已在仓库 ``424/`` 或 ``WORKSPACE_ROOT/uploads/`` 下则保留相对路径；否则复制到 ``uploads/document_templates/`` 或 ``424/document_templates/``

用法::

  set DATABASE_URL=postgresql+psycopg://...
  python scripts/migrate_sqlite_templates_to_pg_document_templates.py [--sqlite PATH]

详见 ``backend/document_template_legacy_migration`` 模块说明。
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import sys
import uuid
from pathlib import Path

# 保证可 import backend
_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("migrate_templates")

ROLE = "excel_export"


def _slugify(s: str, max_len: int = 40) -> str:
    x = re.sub(r"[^a-z0-9]+", "-", (s or "").lower().strip(), flags=re.I)
    x = re.sub(r"-{2,}", "-", x).strip("-") or "tpl"
    return x[:max_len].strip("-") or "tpl"


def _repo_root() -> Path:
    return _REPO


def _workspace() -> Path | None:
    w = (os.environ.get("WORKSPACE_ROOT") or "").strip()
    if not w:
        return None
    p = Path(w).expanduser()
    return p if p.is_dir() else None


def _dest_dir() -> tuple[Path, str]:
    ws = _workspace()
    if ws:
        d = ws / "uploads" / "document_templates"
        d.mkdir(parents=True, exist_ok=True)
        return d, "uploads/document_templates"
    d = _repo_root() / "424" / "document_templates"
    d.mkdir(parents=True, exist_ok=True)
    return d, "424/document_templates"


def _resolve_sqlite_file_path(raw: str) -> Path | None:
    p = Path(raw)
    if p.is_file():
        return p.resolve()
    for base in (_repo_root(), Path.cwd(), Path("e:/FHD/424")):
        cand = (base / raw.lstrip("/\\")).resolve()
        if cand.is_file():
            return cand
    return None


def _safe_relpath_for_storage(p: Path) -> str | None:
    repo = _repo_root().resolve()
    try:
        rel = p.resolve().relative_to(repo)
        s = rel.as_posix()
        if s.startswith("424/") or s.startswith("uploads/"):
            return s
    except ValueError:
        pass
    ws = _workspace()
    if ws:
        try:
            rel = p.resolve().relative_to(ws.resolve())
            s = rel.as_posix()
            if s.startswith("uploads/document_templates/"):
                return s
        except ValueError:
            pass
    return None


def _copy_into_storage(src: Path) -> str:
    dest_dir, prefix = _dest_dir()
    ext = src.suffix.lower() or ".bin"
    name = f"migrated-{uuid.uuid4().hex[:12]}{ext}"
    dest = dest_dir / name
    shutil.copy2(src, dest)
    return f"{prefix}/{name}".replace("\\", "/")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sqlite",
        default="",
        help="templates.db 路径；默认使用 backend.template_database.get_db_path()/templates.db",
    )
    args = parser.parse_args()

    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker

    from backend.database import get_sync_engine
    from backend.template_database import Base, Template, TemplateField, get_db_path

    sqlite_path = Path(args.sqlite) if args.sqlite.strip() else (get_db_path() / "templates.db")
    if not sqlite_path.is_file():
        logger.error("SQLite 文件不存在：%s", sqlite_path)
        return 2

    s_url = f"sqlite:///{sqlite_path.as_posix()}"
    s_eng = create_engine(s_url)
    Base.metadata.create_all(s_eng)
    Session = sessionmaker(bind=s_eng)
    sess = Session()

    pg = get_sync_engine()
    migrated = 0
    try:
        templates: list[Template] = sess.query(Template).order_by(Template.created_at).all()
        for t in templates:
            legacy_id = str(t.id)
            fields_rows = sess.query(TemplateField).filter(TemplateField.template_id == t.id).all()
            fields_json = [f.to_dict() for f in fields_rows]
            meta = t.metadata_json if isinstance(t.metadata_json, dict) else {}
            ep = {
                "fields": fields_json,
                "preview_data": {},
                "metadata": meta,
                "description": t.description,
                "status": t.status or "active",
                "version": t.version or 1,
                "file_size": t.file_size,
                "file_size_human": t.file_size_human,
                "mime_type": t.mime_type,
                "original_filename": t.original_filename,
                "thumbnail_path": t.thumbnail_path,
                "created_by": t.created_by,
                "legacy_frontend_id": f"db:{legacy_id}",
                "source": "sqlite-migration",
            }
            if t.type == "logo":
                ep["kind"] = "logo"

            src = _resolve_sqlite_file_path(t.file_path)
            if not src:
                logger.warning("跳过（找不到文件）：id=%s path=%s", legacy_id, t.file_path)
                continue

            rel = _safe_relpath_for_storage(src)
            if not rel:
                rel = _copy_into_storage(src)

            ff = "docx" if t.type == "word" else ("xlsx" if t.type == "excel" else (src.suffix.lstrip(".")[:16] or "png"))
            base_slug = f"excel-legacy-{legacy_id[:8]}-{_slugify(t.name)}"
            slug = base_slug[:63]

            with pg.begin() as conn:
                existing = conn.execute(
                    text("SELECT slug FROM document_templates WHERE legacy_sqlite_id = :lid LIMIT 1"),
                    {"lid": legacy_id},
                ).mappings().first()
                if existing:
                    slug = str(existing["slug"])
                    conn.execute(
                        text(
                            "UPDATE document_templates SET display_name = :dn, storage_relpath = :path, "
                            "file_format = :ff, editor_payload = CAST(:ep AS jsonb), is_active = true, "
                            "updated_at = now() WHERE legacy_sqlite_id = :lid"
                        ),
                        {
                            "dn": t.name,
                            "path": rel,
                            "ff": ff[:16],
                            "ep": json.dumps(ep, ensure_ascii=False),
                            "lid": legacy_id,
                        },
                    )
                else:
                    for n in range(0, 50):
                        cand = slug if n == 0 else f"{base_slug[:50]}-{n}"[:63]
                        taken = conn.execute(
                            text("SELECT 1 FROM document_templates WHERE slug = :s LIMIT 1"), {"s": cand}
                        ).first()
                        if taken is None:
                            slug = cand
                            break
                    conn.execute(
                        text(
                            "INSERT INTO document_templates "
                            "(slug, display_name, role, storage_relpath, is_default, is_active, sort_order, "
                            "file_format, business_scope, editor_payload, legacy_sqlite_id) "
                            "VALUES (:slug, :dn, :role, :path, false, true, 100, :ff, NULL, "
                            "CAST(:ep AS jsonb), :lid)"
                        ),
                        {
                            "slug": slug,
                            "dn": t.name,
                            "role": ROLE,
                            "path": rel,
                            "ff": ff[:16],
                            "ep": json.dumps(ep, ensure_ascii=False),
                            "lid": legacy_id,
                        },
                    )
            migrated += 1
            logger.info("已迁移 %s -> slug=%s", legacy_id, slug)
    finally:
        sess.close()

    logger.info("完成，共处理 %s 条", migrated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
