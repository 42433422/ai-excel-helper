# -*- coding: utf-8 -*-
"""从 MOD 商店或内置种子目录，装齐某 edition 所需的 Mod 包。"""

from __future__ import annotations

import logging
from typing import Any

from app.mod_sdk.edition_policy import (
    Edition,
    edition_mod_ids,
    resolve_edition,
    seed_edition_mods_from_bundle,
)

logger = logging.getLogger(__name__)


async def bootstrap_edition_pack(edition: Edition | None = None) -> dict[str, Any]:
    """先通过宿主基础员工包 materialize bridge，再对行业 Mod 尝试 Catalog。"""
    ed = edition or resolve_edition()
    mod_ids = list(edition_mod_ids(ed))
    from app.mod_sdk.host_foundation import (
        is_host_bridge_mod_id,
        materialize_host_foundation_bridges,
    )

    materialized = materialize_host_foundation_bridges(ed)
    seeded = materialized.get("seed") or seed_edition_mods_from_bundle(ed)
    seeded_map = {r["mod_id"]: r for r in seeded}

    from app.infrastructure.mods.mod_manager import get_mod_manager

    mm = get_mod_manager()
    installed_ids = {m.id for m in (mm.list_loaded_mods() or []) if getattr(m, "id", None)}
    if not installed_ids:
        installed_ids = {m.id for m in mm.scan_mods() if getattr(m, "id", None)}

    catalog_results: list[dict[str, Any]] = []
    for mod_id in mod_ids:
        if is_host_bridge_mod_id(mod_id):
            if mod_id in installed_ids:
                catalog_results.append(
                    {
                        "mod_id": mod_id,
                        "status": "installed",
                        "message": "host bridge via foundation pack",
                    }
                )
            else:
                catalog_results.append(
                    {
                        "mod_id": mod_id,
                        "status": "missing",
                        "message": "bridge 未齐，请安装「宿主基础能力（预装员工）」",
                    }
                )
            continue
        if mod_id in installed_ids:
            catalog_results.append(
                {"mod_id": mod_id, "status": "installed", "message": "already loaded"}
            )
            continue
        if seeded_map.get(mod_id, {}).get("status") == "seeded":
            try:
                if mm.load_mod(mod_id):
                    catalog_results.append(
                        {"mod_id": mod_id, "status": "loaded", "message": "loaded after seed"}
                    )
                    continue
            except Exception as exc:
                logger.warning("load_mod after seed failed %s: %s", mod_id, exc)

        try:
            from app.fastapi_routes.mod_store_routes import _install_from_catalog

            result = await _install_from_catalog(mod_id, "", activate=True)
            catalog_results.append(
                {
                    "mod_id": mod_id,
                    "status": "catalog" if result.success else "catalog_failed",
                    "message": result.message,
                }
            )
        except Exception as exc:
            catalog_results.append(
                {"mod_id": mod_id, "status": "catalog_failed", "message": str(exc)}
            )

    mm.load_all_mods()
    final_installed = {m.id for m in (mm.list_loaded_mods() or []) if getattr(m, "id", None)}
    ready = all(mid in final_installed for mid in mod_ids)

    return {
        "edition": ed,
        "mod_ids": mod_ids,
        "ready": ready,
        "installed_count": len(final_installed & set(mod_ids)),
        "expected_count": len(mod_ids),
        "seed": seeded,
        "catalog": catalog_results,
    }


__all__ = ["bootstrap_edition_pack"]
