"""
XCAGI 壳层路由聚合：mod 相关 + 传统资源管理器。

具体实现见 ``xcagi_mods``、``xcagi_traditional``；本模块仅合并子路由以保持
``http_app`` 中 ``include_router(..., prefix="/api")`` 不变。
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.routers.xcagi_mods import router as xcagi_mods_router
from backend.routers.xcagi_traditional import router as xcagi_traditional_router

router = APIRouter(tags=["xcagi-shell"])
router.include_router(xcagi_mods_router)
router.include_router(xcagi_traditional_router)
