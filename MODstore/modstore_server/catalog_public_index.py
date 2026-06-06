"""公网 ``/v1/index.json`` 可见性：与 AI 市场 ``catalog_items.is_public`` 对齐。"""

from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, Set

from modstore_server.catalog_store import load_store, norm_pkg_id, norm_version
from modstore_server.duty_roster import all_planned_employee_ids, is_planned_duty_employee_pack

logger = logging.getLogger(__name__)


def _public_pkg_ids_from_db() -> Set[str] | None:
    """返回已上架 pkg_id；数据库不可用时返回 None。"""
    try:
        from modstore_server.db import get_session_factory
        from modstore_server.models import CatalogItem

        sf = get_session_factory()
        with sf() as session:
            rows = (
                session.query(CatalogItem.pkg_id)
                .filter(
                    CatalogItem.is_public == True,  # noqa: E712
                    CatalogItem.compliance_status != "delisted",
                )
                .all()
            )
        return {norm_pkg_id(r[0]) for r in rows if r and norm_pkg_id(r[0])}
    except Exception as exc:
        logger.warning("catalog_public_index: DB lookup failed: %s", exc)
        return None


def package_row_eligible_for_public_index(row: Dict[str, Any], *, public_pkg_ids: Set[str] | None) -> bool:
    """是否应出现在 XCAGI / 公网 ``index.json``。"""
    if not isinstance(row, dict):
        return False
    pid = norm_pkg_id(row.get("id"))
    if not pid:
        return False
    ver = norm_version(row.get("version"))
    artifact = str(row.get("artifact") or "mod").strip().lower()

    if pid in all_planned_employee_ids() or is_planned_duty_employee_pack(pid, artifact):
        return False

    channel = str(row.get("release_channel") or "stable").strip().lower()
    if channel == "draft" or ver.startswith("draft-"):
        return False

    stored = str(row.get("stored_filename") or "").strip()
    download_url = str(row.get("download_url") or "").strip()
    if not stored and not download_url:
        return False

    if public_pkg_ids is None:
        # 无市场库时：至少挡掉编制内 employee_pack；其余 mod 保持兼容
        if artifact == "employee_pack":
            return False
        return True

    return pid in public_pkg_ids


def project_index_row(row: Dict[str, Any]) -> Dict[str, Any]:
    pid = row.get("id")
    ver = row.get("version")
    return {
        "id": pid,
        "version": ver,
        "name": row.get("name"),
        "artifact": row.get("artifact") or "mod",
        "sha256": row.get("sha256"),
        "download_url": row.get("download_url")
        or (f"/v1/packages/{pid}/{ver}/download" if row.get("stored_filename") else None),
        "commerce": row.get("commerce"),
        "license": row.get("license"),
        "store_collection": row.get("store_collection"),
        "public_listing": True,
    }


def build_public_index_packages() -> list[Dict[str, Any]]:
    public_ids = _public_pkg_ids_from_db()
    out: list[Dict[str, Any]] = []
    for row in load_store().get("packages") or []:
        if not isinstance(row, dict):
            continue
        if not package_row_eligible_for_public_index(row, public_pkg_ids=public_ids):
            continue
        out.append(project_index_row(row))
    return out
