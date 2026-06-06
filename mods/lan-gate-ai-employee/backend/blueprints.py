"""
局域网授权 AI 员工 — 最小 FastAPI 挂载（上架/审计可见；LAN API 在 xcagi-lan-license-bridge）。
"""

import logging

logger = logging.getLogger(__name__)


def register_fastapi_routes(app, mod_id: str) -> None:
    from fastapi import APIRouter

    router = APIRouter(prefix=f"/api/mod/{mod_id}", tags=[f"mod-{mod_id}"])

    @router.get("/status")
    def status():
        return {
            "success": True,
            "data": {
                "mod_id": mod_id,
                "role": "lan_gate_shell",
                "message": "局域网授权页与 License API 由宿主与 lan-license-bridge 提供；本 Mod 提供商店与工作流元数据。",
            },
        }

    app.include_router(router)
    logger.info("lan-gate-ai-employee FastAPI stub registered for: %s", mod_id)


def mod_init():
    logger.info("lan-gate-ai-employee initialized (no comms channels)")
