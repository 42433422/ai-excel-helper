#!/usr/bin/env python3
"""将 lan-gate-ai-employee 登记到 MODstore catalog（material_category=ai_employee）。"""

from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

PACK_ID = "lan-gate-ai-employee"


def _zip_mod_dir(mod_dir: Path) -> bytes:
    mod_dir = mod_dir.resolve()
    mid = mod_dir.name
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for f in mod_dir.rglob("*"):
            if f.is_file():
                arc = f"{mid}/{f.relative_to(mod_dir).as_posix()}"
                zf.write(f, arc)
    buf.seek(0)
    return buf.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mods-dir", type=Path, required=True)
    parser.add_argument("--modstore-root", type=Path, required=True)
    parser.add_argument("--set-public", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    mod_dir = (args.mods_dir / PACK_ID).resolve()
    if not mod_dir.is_dir():
        print(f"mods-dir 缺少 {PACK_ID}: {mod_dir}", file=sys.stderr)
        return 2

    modstore_root = args.modstore_root.resolve()
    sys.path.insert(0, str(modstore_root))
    try:
        from dotenv import load_dotenv
    except ImportError:
        load_dotenv = None  # type: ignore
    if load_dotenv:
        load_dotenv(modstore_root / ".env", override=False)
        load_dotenv(modstore_root / ".env.production", override=True)

    manifest: dict[str, Any] = json.loads((mod_dir / "manifest.json").read_text(encoding="utf-8"))
    raw_zip = _zip_mod_dir(mod_dir)

    from modstore_server.catalog_store import append_package
    from modstore_server.catalog_sync import upsert_catalog_item_from_xc_package_dict
    from modstore_server.employee_asset_pipeline import mirror_catalog_file_to_market_files
    from modstore_server.mod_scaffold_runner import import_zip, modstore_library_path
    from modstore_server.models import CatalogItem, get_session_factory
    from sqlalchemy import text

    session_factory = get_session_factory()
    with session_factory() as db:
        row = db.execute(
            text("SELECT id FROM users WHERE is_admin IS TRUE ORDER BY id ASC LIMIT 1"),
        ).fetchone()
        if not row:
            row = db.execute(text("SELECT id FROM users ORDER BY id ASC LIMIT 1")).fetchone()
        if not row:
            print("No user in DB", file=sys.stderr)
            return 3
        author_id = int(row[0])
        exists = db.query(CatalogItem).filter(CatalogItem.pkg_id == PACK_ID).first()
        if exists and not args.force:
            print(f"[SKIP] {PACK_ID} already in catalog")
            return 0

    lib = modstore_library_path()
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(raw_zip)
        zip_tmp = Path(tmp.name)
    try:
        import_zip(zip_tmp, lib, replace=True)
    finally:
        zip_tmp.unlink(missing_ok=True)

    rec = {
        "id": PACK_ID,
        "name": str(manifest.get("name") or PACK_ID),
        "version": str(manifest.get("version") or "1.0.0"),
        "description": str(manifest.get("description") or "")[:2000],
        "artifact": "employee_pack",
        "material_category": "ai_employee",
        "industry": "企业服务",
        "security_level": "enterprise",
        "is_public": bool(args.set_public),
        "release_channel": "stable",
        "commerce": {"mode": "free", "price": 0},
        "license": {"type": "enterprise", "verify_url": None},
    }
    with tempfile.NamedTemporaryFile(suffix=".xcmod", delete=False) as tmp:
        tmp.write(raw_zip)
        tmp_xcmod = Path(tmp.name)
    try:
        saved = append_package(rec, tmp_xcmod)
        with session_factory() as db:
            upsert_catalog_item_from_xc_package_dict(db, saved, author_id=author_id)
            row = db.query(CatalogItem).filter(CatalogItem.pkg_id == PACK_ID).first()
            if row:
                if args.set_public:
                    row.is_public = True
                row.industry = rec["industry"]
                row.price = 0.0
                row.artifact = "employee_pack"
                row.material_category = "ai_employee"
                row.compliance_status = "approved"
                row.name = str(manifest.get("name") or PACK_ID)[:256]
                row.security_level = "enterprise"
                row.license_scope = "enterprise"
                db.commit()
                try:
                    mirror_catalog_file_to_market_files(row.stored_filename)
                except Exception:
                    pass
        print(f"[SEED] {PACK_ID} ok")
        return 0
    finally:
        tmp_xcmod.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
