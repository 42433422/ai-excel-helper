"""办公 employee_pack 桥接 Mod（里程碑 3b）— 目录与已安装清单，执行仍在各 pack / 宿主。"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

OFFICE_PACK_MOD_ID = "xcagi-office-employee-pack-bridge"


def _catalog_path() -> Path | None:
    here = Path(__file__).resolve().parent.parent
    p = here / "config" / "office_pack_catalog.json"
    return p if p.is_file() else None


def load_office_pack_catalog() -> dict:
    p = _catalog_path()
    if not p:
        return {"pack_ids": [], "collection": "office_employee_pack"}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"pack_ids": []}
    except Exception:
        return {"pack_ids": [], "collection": "office_employee_pack"}


def register_fastapi_routes(app, mod_id: str) -> None:
    from fastapi import APIRouter

    router = APIRouter(prefix=f"/api/mod/{mod_id}", tags=[f"office-pack-bridge-{mod_id}"])

    @router.get("/status")
    def status():
        from app.mod_sdk.employee_pack_compat import list_employee_pack_facade_registry

        cat = load_office_pack_catalog()
        return {
            "success": True,
            "data": {
                **list_employee_pack_facade_registry(),
                "mod_id": mod_id,
                "phase": "3b",
                "catalog_pack_count": len(cat.get("pack_ids") or []),
            },
        }

    @router.get("/catalog")
    def catalog():
        from app.mod_sdk.employee_pack_compat import list_office_pack_catalog

        return {"success": True, "data": list_office_pack_catalog()}

    @router.get("/installed")
    def installed():
        from app.mod_sdk.employee_pack_compat import list_installed_employee_packs

        return {"success": True, "data": list_installed_employee_packs()}

    app.include_router(router)
    logger.info("xcagi-office-employee-pack-bridge registered: %s", mod_id)


def mod_init():
    logger.info("xcagi-office-employee-pack-bridge mod_init (3b)")
