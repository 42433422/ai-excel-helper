"""XC ``packages.json``（Catalog API ``/v1``）与 SQLite ``catalog_items``（市场）的关系与同步。

**市场展示与购买**以 ``catalog_items`` 为准（``market_api``）。**XC 包仓库**使用
``catalog_store`` 的 ``packages.json`` 与 ``catalog_data/files/``。

管理员可调用 ``POST /api/admin/catalog/sync-from-xc-packages``，将 JSON 中的每条包
**按 pkg_id upsert** 到 ``catalog_items``（与 ``/v1/packages`` 登记一致），并可选将
二进制复制到 ``market_files/``。``stored_filename`` 始终保留 XC ``catalog_data/files/``
下的 basename，以便 ``employee_runtime.load_employee_pack`` 能打开 zip。
新建 ``catalog_items`` 行默认 ``is_public=False``（不上架 AI 市场）；已存在的 ``pkg_id``
同步时**不再改写** ``is_public``，以免覆盖管理员上架状态。
响应字段 ``inserted`` / ``skipped_existing`` 分别表示本次同步前是否已存在该 ``pkg_id``
（后者包含对已存在行的更新）。
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from modstore_server.catalog_store import files_dir as xc_catalog_files_dir, load_store
from modstore_server.models import CatalogItem


def market_catalog_files_dir() -> Path:
    d = Path(__file__).resolve().parent / "market_files"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _commerce_price(commerce: Any) -> float:
    if not isinstance(commerce, dict):
        return 0.0
    mode = str(commerce.get("mode") or "free").strip().lower()
    if mode == "free":
        return 0.0
    try:
        return float(commerce.get("price") or commerce.get("amount") or 0)
    except (TypeError, ValueError):
        return 0.0


def upsert_catalog_item_from_xc_package_dict(
    session,
    r: Dict[str, Any],
    *,
    author_id: Optional[int] = None,
) -> None:
    """Upsert ``catalog_items`` from a ``catalog_store`` package record (e.g. ``append_package`` output).

    Uses **XC** ``catalog_data/files/`` basenames in ``stored_filename`` so
    :func:`modstore_server.employee_runtime.load_employee_pack` resolves zip paths.
    One row per ``pkg_id`` (matches :class:`SqlCatalogRepository`).
    """
    pkg_id = str(r.get("id") or "").strip()
    version = str(r.get("version") or "").strip()
    if not pkg_id or not version:
        return
    name = (str(r.get("name") or pkg_id).strip() or pkg_id)[:256]
    description = str(r.get("description") or "")[:8000]
    artifact = str(r.get("artifact") or "mod").strip() or "mod"
    industry = str(r.get("industry") or "通用").strip() or "通用"
    price = _commerce_price(r.get("commerce"))
    stored = str(r.get("stored_filename") or "").strip()
    sha256 = str(r.get("sha256") or "").strip()
    row = session.query(CatalogItem).filter(CatalogItem.pkg_id == pkg_id).first()
    if not row:
        row = CatalogItem(pkg_id=pkg_id, author_id=author_id)
        session.add(row)
        row.is_public = False
    elif author_id is not None:
        row.author_id = author_id
    row.version = version
    row.name = name
    row.description = description
    row.price = float(price)
    row.artifact = artifact
    row.industry = industry
    row.stored_filename = stored
    row.sha256 = sha256


def sync_packages_json_to_catalog_items(session, *, admin_user_id: int) -> Dict[str, Any]:
    """将 ``catalog_store`` 中缺失的包插入 ``catalog_items``。"""
    inserted = 0
    skipped = 0
    errors: List[str] = []
    xc_dir = xc_catalog_files_dir()
    mdir = market_catalog_files_dir()

    for r in load_store().get("packages") or []:
        if not isinstance(r, dict):
            continue
        pkg_id = str(r.get("id") or "").strip()
        version = str(r.get("version") or "").strip()
        if not pkg_id or not version:
            continue
        had_row = session.query(CatalogItem).filter(CatalogItem.pkg_id == pkg_id).first() is not None

        stored = str(r.get("stored_filename") or "").strip()
        dest_name = stored
        if stored:
            src = xc_dir / stored
            if src.is_file():
                suffix = src.suffix.lower() or ".zip"
                dest_name = f"{pkg_id}-{version}{suffix}"
                try:
                    shutil.copy2(src, mdir / dest_name)
                except OSError as e:
                    errors.append(f"{pkg_id}@{version}: copy failed {e}")
        upsert_catalog_item_from_xc_package_dict(session, r, author_id=admin_user_id)
        if had_row:
            skipped += 1
        else:
            inserted += 1

    return {"inserted": inserted, "skipped_existing": skipped, "errors": errors}
