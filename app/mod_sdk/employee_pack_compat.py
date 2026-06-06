# -*- coding: utf-8 -*-
"""里程碑 3b：办公 employee_pack 目录与宿主 ``mods/_employees`` 安装态。"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

OFFICE_PACK_BRIDGE_MOD_ID = "xcagi-office-employee-pack-bridge"

logger = logging.getLogger(__name__)

FACADE_PREFIX = f"/api/mod/{OFFICE_PACK_BRIDGE_MOD_ID}"


def _resolve_mod_dir() -> Path | None:
    try:
        from app.infrastructure.mods.mod_manager import get_mod_manager

        meta = get_mod_manager().get_mod(OFFICE_PACK_BRIDGE_MOD_ID)
        if meta and meta.mod_path and (Path(meta.mod_path) / "manifest.json").is_file():
            return Path(meta.mod_path)
    except Exception:
        pass
    trial = Path(__file__).resolve().parents[2] / "mods" / OFFICE_PACK_BRIDGE_MOD_ID
    return trial if (trial / "manifest.json").is_file() else None


def _load_catalog_pack_ids() -> list[str]:
    mod_dir = _resolve_mod_dir()
    if not mod_dir:
        return []
    cat_file = mod_dir / "config" / "office_pack_catalog.json"
    if not cat_file.is_file():
        return []
    try:
        data = json.loads(cat_file.read_text(encoding="utf-8"))
        raw = data.get("pack_ids") or []
        if isinstance(raw, list):
            return [str(x).strip() for x in raw if str(x).strip()]
    except Exception:
        logger.debug("read office_pack_catalog failed", exc_info=True)
    return []


def _pack_role(pack_id: str) -> str:
    pid = pack_id.lower()
    if "full-read" in pid or "-read-" in pid:
        return "read"
    if "generate" in pid:
        return "generate"
    return ""


def _pack_format(pack_id: str) -> str:
    pid = pack_id.lower()
    for fmt in ("excel", "csv", "pdf", "ppt", "word"):
        if pid.startswith(f"{fmt}-"):
            return fmt
    return "other"


def list_office_pack_catalog() -> dict[str, Any]:
    pack_ids = _load_catalog_pack_ids()
    entries = [
        {
            "pack_id": pid,
            "format": _pack_format(pid),
            "role": _pack_role(pid),
            "install_path": f"mods/_employees/{pid}",
        }
        for pid in pack_ids
    ]
    return {
        "collection": "office_employee_pack",
        "pack_count": len(entries),
        "pack_ids": pack_ids,
        "entries": entries,
        "seed_hint": "MODstore_deploy/modstore_server/scripts/seed_csv_employees.py",
    }


def list_installed_employee_packs() -> dict[str, Any]:
    installed: list[dict[str, Any]] = []
    try:
        from app.infrastructure.mods.employee_registry import EmployeeRegistry
        from app.infrastructure.mods.mod_manager import _default_mods_root

        root = _default_mods_root()
        reg = EmployeeRegistry(root)
        installed = reg.list_packs()
    except Exception:
        logger.debug("list_installed_employee_packs failed", exc_info=True)
    catalog_ids = set(_load_catalog_pack_ids())
    office_installed = [
        p for p in installed if str(p.get("pack_id") or p.get("id") or "") in catalog_ids
    ]
    other_installed = [
        p for p in installed if str(p.get("pack_id") or p.get("id") or "") not in catalog_ids
    ]
    return {
        "install_root": "mods/_employees",
        "total_installed": len(installed),
        "office_installed_count": len(office_installed),
        "office_installed": office_installed,
        "other_installed_count": len(other_installed),
        "other_installed": other_installed,
    }


def list_employee_pack_facade_registry() -> dict[str, Any]:
    cat = list_office_pack_catalog()
    inst = list_installed_employee_packs()
    return {
        "ok": True,
        "mod_id": OFFICE_PACK_BRIDGE_MOD_ID,
        "facade_prefix": FACADE_PREFIX,
        "endpoints": [
            "GET /catalog",
            "GET /installed",
            "GET /status",
        ],
        "catalog_pack_count": cat.get("pack_count", 0),
        "office_installed_count": inst.get("office_installed_count", 0),
        "phase": "3b",
        "note": "employee_pack 执行在各 pack 目录；本 Mod 仅提供目录与安装态查询。",
    }


__all__ = [
    "FACADE_PREFIX",
    "OFFICE_PACK_BRIDGE_MOD_ID",
    "list_employee_pack_facade_registry",
    "list_installed_employee_packs",
    "list_office_pack_catalog",
]
