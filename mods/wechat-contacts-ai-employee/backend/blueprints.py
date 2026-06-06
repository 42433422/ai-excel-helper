"""
微信触点 AI 员工 — 最小 FastAPI 挂载（上架/审计可见；业务 API 在宿主核心路由）。
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
                "role": "wechat_contacts_shell",
                "message": "微信联系人与星标能力由宿主页面提供；本 Mod 提供侧栏与工作流员工元数据。",
            },
        }

    app.include_router(router)
    logger.info("wechat-contacts-ai-employee FastAPI stub registered for: %s", mod_id)


def mod_init():
    logger.info("wechat-contacts-ai-employee initialized (no comms channels)")
