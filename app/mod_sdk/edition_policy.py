# -*- coding: utf-8 -*-
"""宿主发行版（edition）策略：generic / minimal / full。"""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Literal

from app.mod_sdk.platform_shell import GENERIC_HOST_MOD_IDS, MINIMAL_HOST_MOD_IDS
from app.mod_sdk.product_skus import (
    bundled_mod_ids_for_sku,
    configure_sku_edition_env,
    resolve_product_sku,
)

logger = logging.getLogger(__name__)

Edition = Literal["minimal", "generic", "full"]


def resolve_edition() -> Edition:
    """与 ``platform_shell._resolve_edition`` 一致，供路由与中间件共用。"""
    explicit = (os.environ.get("XCAGI_EDITION") or "").strip().lower()
    if explicit in ("minimal", "generic", "full"):
        return explicit  # type: ignore[return-value]
    minimal = (os.environ.get("XCAGI_MINIMAL_EDITION") or "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    generic = (os.environ.get("XCAGI_GENERIC_EDITION") or "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    if minimal:
        return "minimal"
    if generic:
        return "generic"
    return "full"


def should_register_host_legacy_routes() -> bool:
    """非 full 发行版默认不挂载 legacy_gaps 大批兼容路由。"""
    flag = (os.environ.get("XCAGI_REGISTER_LEGACY_ROUTES") or "").strip().lower()
    if flag in ("0", "false", "no"):
        return False
    if flag in ("1", "true", "yes"):
        return True
    from app.mod_sdk.host_profile import edition_legacy_routes_enabled

    return edition_legacy_routes_enabled(resolve_edition())


def edition_mod_ids(edition: Edition | None = None) -> tuple[str, ...]:
    sku_mods = bundled_mod_ids_for_sku()
    if sku_mods:
        return sku_mods
    ed = edition or resolve_edition()
    if ed == "minimal":
        return MINIMAL_HOST_MOD_IDS
    if ed == "generic":
        return GENERIC_HOST_MOD_IDS
    return (*MINIMAL_HOST_MOD_IDS, *GENERIC_HOST_MOD_IDS)


def configure_edition_defaults(*, desktop: bool = False) -> Edition:
    """填充进程环境默认：打包桌面与显式 ``XCAGI_DEFAULT_EDITION`` 时偏向 generic 壳。"""
    if resolve_product_sku():
        configure_sku_edition_env()
    ed = resolve_edition()
    if ed != "full":
        return ed
    if os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("PYTEST_VERSION"):
        return ed
    default_ed = (os.environ.get("XCAGI_DEFAULT_EDITION") or "").strip().lower()
    is_desktop = desktop or (os.environ.get("XCAGI_DESKTOP_MODE") or "").strip().lower() in {
        "1",
        "true",
        "yes",
    }
    if is_desktop or default_ed == "generic":
        os.environ.setdefault("XCAGI_GENERIC_EDITION", "1")
        os.environ.setdefault("XCAGI_PLATFORM_SHELL", "1")
    elif default_ed == "minimal":
        os.environ.setdefault("XCAGI_MINIMAL_EDITION", "1")
        os.environ.setdefault("XCAGI_PLATFORM_SHELL", "1")
    return resolve_edition()


def _extra_mod_seed_roots() -> list[Path]:
    """除主 mods 根外，开发树中常见的 bridge 种子目录（如 FHD/mods 缺件时回退 XCAGI/mods）。"""
    roots: list[Path] = []
    for raw in (
        os.environ.get("XCAGI_EXTRA_SEED_MODS_DIR"),
        os.environ.get("XCAGI_REPO_MODS_DIR"),
    ):
        if raw:
            p = Path(raw).expanduser().resolve()
            if p.is_dir():
                roots.append(p)
    here = Path(__file__).resolve()
    for parent in here.parents:
        for rel in ("XCAGI/mods", "FHD/XCAGI/mods"):
            p = (parent / rel).resolve()
            if p.is_dir() and p not in roots:
                roots.append(p)
    return roots


def _resolve_mod_seed_source(mod_id: str, primary: Path) -> Path | None:
    trial = primary / mod_id
    if trial.is_dir():
        return trial
    for root in _extra_mod_seed_roots():
        alt = root / mod_id
        if alt.is_dir():
            return alt
    return None


def bundled_mods_dir() -> Path | None:
    """PyInstaller 或源码树中的只读 Mod 种子目录。"""
    for raw in (
        os.environ.get("XCAGI_BUNDLED_MODS_DIR"),
        os.environ.get("XCAGI_SEED_MODS_DIR"),
    ):
        if raw:
            p = Path(raw).expanduser().resolve()
            if p.is_dir():
                return p
    import sys

    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", ""))
        for name in ("mods", "XCAGI/mods"):
            p = base / name
            if p.is_dir():
                return p
    cwd = Path.cwd()
    for rel in ("mods", "XCAGI/mods", "FHD/mods"):
        p = (cwd / rel).resolve()
        if p.is_dir():
            return p
    here = Path(__file__).resolve()
    for parent in here.parents:
        trial = parent / "mods"
        if trial.is_dir() and (trial / "xcagi-planner-bridge").is_dir():
            return trial
    return None


def seed_edition_mods_from_bundle(
    edition: Edition | None = None,
    *,
    mods_root: str | Path | None = None,
) -> list[dict[str, str]]:
    """将内置 Mod 目录复制到用户 mods 目录（已存在则跳过）。"""
    from app.infrastructure.mods.mod_manager import get_mod_manager

    bundle = bundled_mods_dir()
    if bundle is None:
        logger.info("seed_edition_mods: no bundled mods directory found")
        return []

    mm = get_mod_manager()
    root = Path(mods_root or mm.mods_root)
    root.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, str]] = []

    for mod_id in edition_mod_ids(edition):
        dst = root / mod_id
        if dst.is_dir():
            results.append({"mod_id": mod_id, "status": "skipped", "message": "already present"})
            continue
        src = _resolve_mod_seed_source(mod_id, bundle)
        if src is None:
            results.append(
                {
                    "mod_id": mod_id,
                    "status": "missing",
                    "message": f"not in bundle: {bundle / mod_id}",
                }
            )
            continue
        try:
            shutil.copytree(src, dst)
            results.append({"mod_id": mod_id, "status": "seeded", "message": str(dst)})
        except OSError as exc:
            results.append({"mod_id": mod_id, "status": "error", "message": str(exc)})

    return results


__all__ = [
    "Edition",
    "resolve_edition",
    "should_register_host_legacy_routes",
    "edition_mod_ids",
    "configure_edition_defaults",
    "bundled_mods_dir",
    "seed_edition_mods_from_bundle",
]
