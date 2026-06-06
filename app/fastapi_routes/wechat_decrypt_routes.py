"""微信本地库自动配置 API。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Body

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/wechat/decrypt", tags=["wechat-decrypt"])


@router.get("/status")
def wechat_decrypt_config_status():
    from app.services.wechat_decrypt_autoconfig import get_wechat_decrypt_status

    return get_wechat_decrypt_status()


@router.post("/auto_configure")
def wechat_decrypt_auto_configure(body: dict | None = Body(default=None)):
    from app.services.wechat_decrypt_http import wechat_decrypt_auto_configure_response

    return wechat_decrypt_auto_configure_response(body)
