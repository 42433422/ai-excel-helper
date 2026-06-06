"""FHD 内嵌 MODstore：将本地库 / 同步 / 调试等 HTTP 路由注册到 FastAPI 应用。"""

from __future__ import annotations

from fastapi import FastAPI

from modstore_server.fhd_routes_api import router as fhd_modstore_router


def register_fhd_modstore_routes(app: FastAPI) -> None:
    app.include_router(fhd_modstore_router)
