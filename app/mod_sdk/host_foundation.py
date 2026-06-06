# -*- coding: utf-8 -*-
"""宿主基础能力：以 employee_pack（员工）交付，磁盘上仍为多个 bridge Mod 目录。"""

from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any

from app.mod_sdk.platform_shell import GENERIC_HOST_MOD_IDS, MINIMAL_HOST_MOD_IDS

logger = logging.getLogger(__name__)

HOST_FOUNDATION_EMPLOYEE_PACK_ID = "xcagi-host-foundation-employee"
HOST_FOUNDATION_EMPLOYEE_ID = "host_foundation"
HOST_FOUNDATION_BUNDLE_MOD_ID = "xcagi-generic-host-bundle"

STORE_COLLECTION_HOST_FOUNDATION = "host_foundation"
STORE_COLLECTION_WORKFLOW_EMPLOYEE = "workflow_employee"
STORE_COLLECTION_INDUSTRY_MOD = "industry_mod"

_INFRASTRUCTURE_PREFIXES = (
    "xcagi-planner-bridge",
    "xcagi-erp-domain-bridge",
    "xcagi-workflow-visualization-bridge",
    "xcagi-approval-bridge",
    "xcagi-lan-license-bridge",
    "xcagi-model-payment-bridge",
    "xcagi-neuro-bus-bridge",
    "xcagi-office-employee-pack-bridge",
    "xcagi-customer-service-bridge",
    "xcagi-core-workflow-employees",
    "xcagi-planner-excel-tools",
)


def is_host_bridge_mod_id(mod_id: str) -> bool:
    mid = str(mod_id or "").strip()
    if not mid:
        return False
    if mid in GENERIC_HOST_MOD_IDS or mid in MINIMAL_HOST_MOD_IDS:
        return True
    return mid.startswith("xcagi-") and mid.endswith("-bridge")


def is_workflow_employee_mod_id(mod_id: str) -> bool:
    return str(mod_id or "").strip().startswith("xcagi-workflow-employee-")


def is_infrastructure_mod_hidden_from_store(mod_id: str) -> bool:
    """商店 Catalog 不单独展示 bridge / 工作流单员工等基础设施件。"""
    mid = str(mod_id or "").strip()
    if not mid:
        return False
    if mid in (HOST_FOUNDATION_EMPLOYEE_PACK_ID, HOST_FOUNDATION_BUNDLE_MOD_ID):
        return False
    if is_host_bridge_mod_id(mid):
        return True
    if is_workflow_employee_mod_id(mid):
        return True
    if mid in _INFRASTRUCTURE_PREFIXES:
        return True
    return False


def is_host_foundation_employee_pack(pack_id: str) -> bool:
    return str(pack_id or "").strip() == HOST_FOUNDATION_EMPLOYEE_PACK_ID


AUX_EMPLOYEE_PACK_MOD_IDS: tuple[str, ...] = (
    "wechat-contacts-ai-employee",
    "lan-gate-ai-employee",
)


def is_aux_employee_pack_mod_id(mod_id: str) -> bool:
    return str(mod_id or "").strip() in AUX_EMPLOYEE_PACK_MOD_IDS


def _repo_mod_seed_dirs() -> list[Path]:
    here = Path(__file__).resolve()
    repo = here.parents[2]
    roots: list[Path] = []
    for base in (repo / "mods", repo / "XCAGI" / "mods"):
        if base.is_dir():
            roots.append(base)
    raw = os.environ.get("XCAGI_ROOT", "").strip()
    if raw:
        p = Path(raw).expanduser() / "mods"
        if p.is_dir():
            roots.append(p)
    seen: set[str] = set()
    out: list[Path] = []
    for p in roots:
        key = str(p.resolve())
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def read_aux_employee_pack_manifest(pack_id: str) -> dict[str, Any] | None:
    pid = str(pack_id or "").strip()
    if not pid or not is_aux_employee_pack_mod_id(pid):
        return None
    for root in _repo_mod_seed_dirs():
        mf = root / pid / "manifest.json"
        if not mf.is_file():
            continue
        try:
            raw = json.loads(mf.read_text(encoding="utf-8"))
            return raw if isinstance(raw, dict) else None
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("read_aux_employee_pack_manifest %s: %s", mf, e)
    return None


def aux_employee_pack_catalog_row(*, pack_id: str, installed: bool) -> dict[str, Any]:
    manifest = read_aux_employee_pack_manifest(pack_id) or {}
    mid = str(manifest.get("id") or pack_id).strip() or pack_id
    ver = str(manifest.get("version") or "1.0.0").strip() or "1.0.0"
    return {
        "id": mid,
        "pkg_id": mid,
        "name": str(manifest.get("name") or mid),
        "version": ver,
        "author": str(manifest.get("author") or "成都修茈科技有限公司"),
        "description": str(manifest.get("description") or "").strip(),
        "artifact": "employee_pack",
        "store_collection": STORE_COLLECTION_WORKFLOW_EMPLOYEE,
        "is_installed": installed,
        "source": "local",
        "package_file": f"{mid}:{ver}",
        "download_count": 0,
        "total_downloads": 0,
        "avg_rating": 0.0,
        "rating_count": 0,
        "dependencies": (
            manifest.get("dependencies") if isinstance(manifest.get("dependencies"), dict) else {}
        ),
        "catalog_base_url": "",
        "commerce": {"price_label": "免费", "collection": STORE_COLLECTION_WORKFLOW_EMPLOYEE},
    }


def inject_aux_employee_pack_rows(available: list[dict[str, Any]], installed_ids: set[str]) -> None:
    """商店「AI 员工」展示触点/授权类扩展（非远端逐项 bridge）。"""
    seen = {str(r.get("id") or "").strip() for r in available}
    for pack_id in AUX_EMPLOYEE_PACK_MOD_IDS:
        if pack_id in seen:
            continue
        if not read_aux_employee_pack_manifest(pack_id):
            continue
        available.append(
            aux_employee_pack_catalog_row(pack_id=pack_id, installed=pack_id in installed_ids)
        )


def install_aux_employee_pack_from_repo_seed(
    pack_id: str, *, activate: bool = True
) -> tuple[bool, str]:
    """无远端 zip 时，从仓库内置 mods/<pack_id> 复制到用户 mods 根。"""
    pid = str(pack_id or "").strip()
    if not is_aux_employee_pack_mod_id(pid):
        return False, "非触点员工包"
    src: Path | None = None
    for root in _repo_mod_seed_dirs():
        candidate = root / pid
        if (candidate / "manifest.json").is_file():
            src = candidate
            break
    if src is None:
        return False, f"未找到内置员工包：{pid}"
    from app.infrastructure.mods.mod_manager import get_mod_manager

    mm = get_mod_manager()
    dest = Path(mm.mods_root) / pid
    try:
        if dest.is_dir():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
        mm.load_all_mods()
        return True, f"已从内置种子安装 {pid}"
    except OSError as e:
        return False, str(e)


def catalog_store_collection(row: dict[str, Any]) -> str:
    """从 Catalog / 本机行推断商店分区。"""
    if not isinstance(row, dict):
        return STORE_COLLECTION_INDUSTRY_MOD
    sc = str(row.get("store_collection") or "").strip()
    if sc:
        return sc
    art = str(row.get("artifact") or "").strip().lower()
    if art == "employee_pack":
        cfg = row.get("config") if isinstance(row.get("config"), dict) else {}
        if cfg.get("host_foundation_pack"):
            return STORE_COLLECTION_HOST_FOUNDATION
        return STORE_COLLECTION_WORKFLOW_EMPLOYEE
    mid = str(row.get("id") or row.get("pkg_id") or "").strip()
    if is_host_foundation_employee_pack(mid):
        return STORE_COLLECTION_HOST_FOUNDATION
    if is_workflow_employee_mod_id(mid):
        return STORE_COLLECTION_WORKFLOW_EMPLOYEE
    if is_infrastructure_mod_hidden_from_store(mid):
        return ""
    return STORE_COLLECTION_INDUSTRY_MOD


def materialize_host_foundation_bridges(edition: str | None = None) -> dict[str, Any]:
    """将内置 mods/ 种子复制到用户 mods 根并 load_all_mods。"""
    from app.infrastructure.mods.mod_manager import get_mod_manager
    from app.mod_sdk.edition_policy import (
        Edition,
        edition_mod_ids,
        resolve_edition,
        seed_edition_mods_from_bundle,
    )

    ed: Edition = edition or resolve_edition() or "generic"  # type: ignore[assignment]
    if ed not in ("minimal", "generic", "full"):
        ed = "generic"  # type: ignore[assignment]

    seeded = seed_edition_mods_from_bundle(ed)
    mm = get_mod_manager()
    mm.load_all_mods()
    installed = {m.id for m in (mm.list_loaded_mods() or []) if getattr(m, "id", None)}
    if not installed:
        installed = {m.id for m in mm.scan_mods() if getattr(m, "id", None)}
    expected = list(edition_mod_ids(ed))
    missing = [mid for mid in expected if mid not in installed]
    return {
        "edition": ed,
        "expected_mod_ids": expected,
        "missing_mod_ids": missing,
        "ready": not missing,
        "seed": seeded,
        "installed_count": len(installed & set(expected)),
        "expected_count": len(expected),
    }


def host_foundation_employee_present() -> bool:
    """用户已安装「宿主基础能力·预装员工」目录（对外一个 Mod/员工包）。"""
    from app.infrastructure.mods.employee_registry import employees_root, get_employee_registry

    er = get_employee_registry()
    dest = os.path.join(employees_root(er.mods_root), HOST_FOUNDATION_EMPLOYEE_PACK_ID)
    return os.path.isdir(dest)


def host_foundation_bridges_ready(edition: str | None = None) -> bool:
    """当前 edition 所需 bridge Mod 均已出现在 mods 根目录（可被 ModManager 加载）。"""
    from app.infrastructure.mods.mod_manager import get_mod_manager
    from app.mod_sdk.edition_policy import edition_mod_ids, resolve_edition

    ed = (edition or resolve_edition() or "generic").strip().lower()
    if ed not in ("minimal", "generic", "full"):
        ed = "generic"
    expected = [mid for mid in edition_mod_ids(ed) if is_host_bridge_mod_id(mid)]
    if not expected:
        return False
    mm = get_mod_manager()
    loaded = {m.id for m in (mm.list_loaded_mods() or []) if getattr(m, "id", None)}
    if not loaded:
        loaded = {m.id for m in mm.scan_mods() if getattr(m, "id", None)}
    return all(mid in loaded for mid in expected)


def is_host_foundation_pack_installed() -> bool:
    """宿主能力就绪：bridge 已齐；仅员工包目录存在时返回 False（需 materialize）。"""
    return host_foundation_bridges_ready()


def try_materialize_host_foundation_if_needed(edition: str | None = None) -> dict[str, Any] | None:
    """员工包在盘但 bridge 未齐时，从内置种子展开（供引导页检测与装包 API 复用）。"""
    if not host_foundation_employee_present() or host_foundation_bridges_ready(edition):
        return None
    return materialize_host_foundation_bridges(edition)


def host_foundation_catalog_row(*, installed: bool = False) -> dict[str, Any]:
    """本机内置的「宿主基础能力·预装员工」商店行（非远端逐项 bridge）。"""
    return {
        "id": HOST_FOUNDATION_EMPLOYEE_PACK_ID,
        "pkg_id": HOST_FOUNDATION_EMPLOYEE_PACK_ID,
        "name": "宿主基础能力（预装员工）",
        "version": "1.0.0",
        "author": "成都修茈科技有限公司",
        "description": (
            "以员工包交付的通用宿主底座：安装后自动写入对话/ERP/审批/客服等 "
            f"{len(GENERIC_HOST_MOD_IDS)} 个 bridge Mod，无需在商店逐项安装基础设施 Mod。"
        ),
        "artifact": "employee_pack",
        "store_collection": STORE_COLLECTION_HOST_FOUNDATION,
        "is_installed": installed,
        "source": "local",
        "package_file": None,
        "download_count": 0,
        "total_downloads": 0,
        "avg_rating": 0.0,
        "rating_count": 0,
        "dependencies": {},
        "catalog_base_url": "",
    }


__all__ = [
    "HOST_FOUNDATION_EMPLOYEE_PACK_ID",
    "HOST_FOUNDATION_EMPLOYEE_ID",
    "HOST_FOUNDATION_BUNDLE_MOD_ID",
    "AUX_EMPLOYEE_PACK_MOD_IDS",
    "host_foundation_employee_present",
    "host_foundation_bridges_ready",
    "try_materialize_host_foundation_if_needed",
    "STORE_COLLECTION_HOST_FOUNDATION",
    "STORE_COLLECTION_WORKFLOW_EMPLOYEE",
    "STORE_COLLECTION_INDUSTRY_MOD",
    "is_host_bridge_mod_id",
    "is_workflow_employee_mod_id",
    "is_infrastructure_mod_hidden_from_store",
    "is_host_foundation_employee_pack",
    "is_aux_employee_pack_mod_id",
    "aux_employee_pack_catalog_row",
    "inject_aux_employee_pack_rows",
    "install_aux_employee_pack_from_repo_seed",
    "read_aux_employee_pack_manifest",
    "catalog_store_collection",
    "materialize_host_foundation_bridges",
    "host_foundation_catalog_row",
    "is_host_foundation_pack_installed",
]
