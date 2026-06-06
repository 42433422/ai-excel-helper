# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)
MOD_ID = "xcagi-workflow-visualization-bridge"


def register_fastapi_routes(app, mod_id: str) -> None:
    router = APIRouter(prefix=f"/api/mod/{mod_id}", tags=[f"mod-{mod_id}"])

    @router.get("/status")
    def mod_status():
        return {"success": True, "data": {"mod_id": mod_id, "role": "workflow_visualization_bridge"}}

    app.include_router(router)
    logger.info("workflow visualization bridge registered %s", mod_id)


def mod_init():
    logger.info("%s mod_init", MOD_ID)
