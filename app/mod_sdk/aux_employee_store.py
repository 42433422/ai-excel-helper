# -*- coding: utf-8 -*-
"""触点/授权类 AI 员工：商店上架与种子安装（无 host_foundation 依赖，便于生产增量部署）。"""

from __future__ import annotations

import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

STORE_COLLECTION_WORKFLOW_EMPLOYEE = "workflow_employee"

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
    mods_root = os.environ.get("XCAGI_MODS_ROOT", "").strip()
    if mods_root:
        p = Path(mods_root).expanduser()
        if p.is_dir():
            roots.append(p)
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
    index_by_id = {
        str(r.get("id") or r.get("pkg_id") or "").strip(): i
        for i, r in enumerate(available)
        if str(r.get("id") or r.get("pkg_id") or "").strip()
    }
    for pack_id in AUX_EMPLOYEE_PACK_MOD_IDS:
        if not read_aux_employee_pack_manifest(pack_id):
            continue
        row = aux_employee_pack_catalog_row(pack_id=pack_id, installed=pack_id in installed_ids)
        if pack_id in index_by_id:
            i = index_by_id[pack_id]
            prev = available[i] if isinstance(available[i], dict) else {}
            available[i] = {**row, **{k: v for k, v in prev.items() if k == "is_installed"}}
            continue
        available.append(row)


def install_aux_employee_pack_from_repo_seed(
    pack_id: str, *, activate: bool = True
) -> tuple[bool, str]:
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
        logger.exception("install_aux_employee_pack_from_repo_seed %s", pid)
        return False, str(e)
