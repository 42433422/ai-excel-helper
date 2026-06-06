"""宿主级注册：内部客服微信群被动/轮询 API（不依赖 Mod 热重载）。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from app.infrastructure.mods.mod_manager import is_mods_disabled

logger = logging.getLogger(__name__)

MOD_PREFIX = "/api/mod/xcagi-customer-service-bridge"


class PassivePollBody(BaseModel):
    market_user_id: int = Field(..., gt=0)
    username: str = Field(default="", max_length=128)
    dry_run: bool = Field(default=True)
    auto_reply: bool = Field(default=True)
    max_replies: int = Field(default=0, ge=0, le=5)
    use_llm: bool = Field(default=True)
    skip_sync: bool = Field(default=False)
    refresh_count_new: int | None = Field(default=None, ge=0)
    refresh_latest_label: str = Field(default="", max_length=32)
    catch_up_latest: bool = Field(default=False)


class PassiveLoopConfigBody(BaseModel):
    market_user_id: int = Field(..., gt=0)
    username: str = Field(default="", max_length=128)
    poll_enabled: bool = False
    poll_interval_sec: int = Field(default=60, ge=10, le=600)


def build_user_cs_wechat_passive_router() -> APIRouter:
    router = APIRouter(prefix=MOD_PREFIX, tags=["user-cs-wechat-passive"])

    @router.get("/user-cs/wechat/llm-status")
    def wechat_llm_status(request: Request):
        from app.fastapi_routes.market_account import session_id_from_request
        from app.services.wechat_passive_group_monitor import probe_passive_llm_ready

        return {
            "success": True,
            "data": probe_passive_llm_ready(
                session_id=session_id_from_request(request),
                request=request,
            ),
        }

    @router.post("/user-cs/wechat/passive-poll")
    async def passive_poll(request: Request, body: PassivePollBody):
        from app.fastapi_routes.market_account import session_id_from_request
        from app.services.wechat_passive_group_monitor import passive_poll_once

        out = passive_poll_once(
            market_user_id=int(body.market_user_id),
            username=body.username,
            dry_run=body.dry_run,
            auto_reply=body.auto_reply,
            max_replies=body.max_replies,
            use_llm=body.use_llm,
            skip_sync=body.skip_sync,
            refresh_count_new=body.refresh_count_new,
            refresh_latest_label=body.refresh_latest_label,
            catch_up_latest=body.catch_up_latest,
            session_id=session_id_from_request(request),
            request=request,
        )
        return {"success": bool(out.get("success")), "data": out}

    @router.get("/user-cs/wechat/passive-loop")
    def passive_loop_get(market_user_id: int, username: str = ""):
        from app.services.wechat_passive_group_monitor import get_passive_poll_config

        return {
            "success": True,
            "data": get_passive_poll_config(market_user_id, username=username),
        }

    @router.post(
        "/user-cs/wechat/passive-loop",
        operation_id="fhd_user_cs_passive_loop_post_compat",
    )
    def passive_loop_save_post(body: PassiveLoopConfigBody):
        from app.services.wechat_passive_group_monitor import save_passive_poll_config

        data = save_passive_poll_config(
            int(body.market_user_id),
            username=body.username,
            poll_enabled=body.poll_enabled,
            poll_interval_sec=body.poll_interval_sec,
        )
        return {"success": True, "data": data}

    @router.put(
        "/user-cs/wechat/passive-loop",
        operation_id="fhd_user_cs_passive_loop_put_compat",
    )
    def passive_loop_save_put(body: PassiveLoopConfigBody):
        from app.services.wechat_passive_group_monitor import save_passive_poll_config

        data = save_passive_poll_config(
            int(body.market_user_id),
            username=body.username,
            poll_enabled=body.poll_enabled,
            poll_interval_sec=body.poll_interval_sec,
        )
        return {"success": True, "data": data}

    @router.post("/user-cs/wechat/passive-reset-watch")
    def passive_reset_watch(body: PassiveLoopConfigBody):
        from app.services.wechat_passive_group_monitor import reset_passive_watch

        state = reset_passive_watch(int(body.market_user_id), username=body.username)
        return {"success": True, "data": state}

    return router


def register_user_cs_wechat_passive_routes(app) -> None:
    # Mod 启用时由 xcagi-customer-service-bridge 在热加载阶段注册同路径；compat 仅作无 Mod 回退。
    if not is_mods_disabled():
        logger.info(
            "Skip user_cs_wechat_passive_compat (%s): mod bridge owns routes when mods enabled",
            MOD_PREFIX,
        )
        return
    app.include_router(build_user_cs_wechat_passive_router())
    logger.info(
        "Registered user_cs_wechat_passive_compat (%s/user-cs/wechat/passive-*)", MOD_PREFIX
    )
