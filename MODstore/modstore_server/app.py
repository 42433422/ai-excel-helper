from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import httpx  # noqa: F401  # tests: ``@patch("modstore_server.app.httpx.Client")``

from modman.repo_config import load_config, save_config
from modman.store import project_root
from modstore_server.portal_wallet_sync import fetch_wallet_secret
from modstore_server.constants import DEFAULT_API_PORT, DEFAULT_XCAGI_BACKEND_URL

_TAGS = [
    {"name": "health", "description": "服务探活"},
    {
        "name": "config",
        "description": "库路径、XCAGI 根目录、后端 URL、导出 FHD 壳层 /api/mods JSON",
    },
    {"name": "mods", "description": "Mod 列表、详情、manifest、文件读写、导入导出"},
    {"name": "sync", "description": "与 XCAGI/mods 推送与拉回"},
    {"name": "debug", "description": "沙箱目录、primary 批量标记、XCAGI 状态代理"},
    {"name": "authoring", "description": "扩展面文档、蓝图路由静态扫描、宿主 OpenAPI 合并"},
]

app = FastAPI(
    title="MODstore",
    version="0.2.0",
    description=(
        "XCAGI Mod 本地库与调试辅助 API。"
        f"\n\n**交互式文档**：本页同源的 [`/docs`](./docs)（Swagger UI）、[`/redoc`](./redoc)。"
        f"\n**机器可读**：[`/openapi.json`](./openapi.json)。"
        f"\n\n默认假设 XCAGI HTTP 后端在 `{DEFAULT_XCAGI_BACKEND_URL}`（可在配置中覆盖）。"
        f"\n开发时 API 默认监听 `127.0.0.1:{DEFAULT_API_PORT}`。"
    ),
    openapi_tags=_TAGS,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
        "http://127.0.0.1:5175",
        "http://localhost:5175",
        "http://127.0.0.1:4173",
        "http://localhost:4173",
        "http://127.0.0.1:5176",
        "http://localhost:5176",
        "http://127.0.0.1:5177",
        "http://localhost:5177",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from modstore_server.market_api import router as market_router

app.include_router(market_router)

_MARKET_DIST = Path(__file__).resolve().parent.parent / "market" / "dist"
if _MARKET_DIST.is_dir():
    app.mount("/market", StaticFiles(directory=str(_MARKET_DIST), html=True), name="market")

from modstore_server.fhd_routes_registry import register_fhd_modstore_routes

register_fhd_modstore_routes(app)

from modstore_server.catalog_api import router as catalog_public_router

app.include_router(catalog_public_router)


def _maybe_mount_ui() -> None:
    root = Path(__file__).resolve().parent.parent
    dist = root / "web" / "dist"
    if not dist.is_dir():
        return
    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="ui-assets")

    index_file = dist / "index.html"

    @app.get("/")
    def ui_root():
        if index_file.is_file():
            return FileResponse(index_file)
        raise HTTPException(404)

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        if (
            full_path.startswith("api")
            or full_path.startswith("v1")
            or full_path.startswith("docs")
            or full_path.startswith("redoc")
            or full_path == "openapi.json"
        ):
            raise HTTPException(404)
        if index_file.is_file():
            return FileResponse(index_file)
        raise HTTPException(404)


_maybe_mount_ui()
