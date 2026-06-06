"""Vue dist 静态目录挂载与 SPA fallback（使用沙盒解析到的 vue-dist 路径）。"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from sandbox_app.banner_inject import inject_sandbox_banner

logger = logging.getLogger(__name__)

_EXCLUDED_PREFIXES = (
    "api/",
    "assets/",
    "static/",
    "outputs/",
    "uploads/",
    "fonts/",
    "images/",
    "js/",
    "css/",
    "favicon",
    "docs",
    "openapi.json",
    "redoc",
    "font-awesome/",
    "startup/",
    "yuangong/",
    "workflow/",
    "brand-xc-logo",
    "workflow-employee-docs.json",
)


def mount_vue_static(app: FastAPI, vue_dist_dir: Path) -> None:
    """挂载 public 子目录与 /assets（与主栈 fastapi_app 行为对齐）。"""
    vue_dist_dir = Path(vue_dist_dir)
    if not vue_dist_dir.is_dir():
        logger.warning("Vue dist 不存在，跳过静态挂载: %s", vue_dist_dir)
        return

    for sub in ("font-awesome", "startup", "yuangong", "workflow"):
        directory = vue_dist_dir / sub
        if directory.is_dir():
            mount_path = f"/{sub}"
            try:
                app.mount(mount_path, StaticFiles(directory=str(directory)), name=f"sandbox-vue-{sub}")
                logger.info("sandbox static: %s -> %s", mount_path, directory)
            except Exception as e:
                logger.warning("sandbox static mount failed %s: %s", mount_path, e)

    css_dir = vue_dist_dir / "assets" / "css"
    if css_dir.is_dir():

        @app.get("/assets/css/{filename:path}", include_in_schema=False)
        async def sandbox_css(filename: str):
            fp = (css_dir / filename).resolve()
            try:
                fp.relative_to(css_dir.resolve())
            except ValueError:
                return JSONResponse({"success": False, "message": "资源路径非法"}, status_code=400)
            if not fp.is_file():
                return JSONResponse({"success": False, "message": "CSS 不存在"}, status_code=404)
            text = fp.read_text(encoding="utf-8", errors="ignore")
            # Vite 产物里的 FontAwesome 字体是根绝对路径 /assets/fonts；
            # 沙盒在 /sandbox/ 子路径下时必须改成 /sandbox/assets/fonts。
            from sandbox_app.sandbox_settings import SANDBOX_URL_PREFIX

            prefix = SANDBOX_URL_PREFIX.rstrip("/")
            if prefix:
                text = text.replace("url(/assets/", f"url({prefix}/assets/")
            return Response(content=text, media_type="text/css")

    assets_dir = vue_dist_dir / "assets"
    if assets_dir.is_dir():
        try:
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="sandbox_vue_assets")
            logger.info("sandbox static: /assets -> %s", assets_dir)
        except Exception as e:
            logger.warning("sandbox /assets mount failed: %s", e)

    def _route_factory(fp: Path):
        async def _send():
            return FileResponse(str(fp))

        return _send

    for name in ("vite.svg", "brand-xc-logo.jpg"):
        p = vue_dist_dir / name
        if p.is_file():
            app.add_api_route(
                f"/{name}",
                _route_factory(p),
                methods=["GET"],
                include_in_schema=False,
                name=f"sandbox_root_{name.replace('.', '_')}",
            )


def register_sandbox_spa_fallback(app: FastAPI, vue_dist_dir: Path) -> None:
    vue_dist_dir = Path(vue_dist_dir)
    index_html = vue_dist_dir / "index.html"

    @app.get("/{fallback:path}", include_in_schema=False)
    async def vue_history_fallback(fallback: str):
        if any(fallback.startswith(p) for p in _EXCLUDED_PREFIXES):
            return JSONResponse(
                {"success": False, "message": f"资源不存在：/{fallback}", "sandbox": True},
                status_code=404,
            )
        if not index_html.is_file():
            return JSONResponse(
                {
                    "success": False,
                    "message": "index.html 缺失，请先构建 FHD 前端或运行 scripts/sync-frontend-dist.mjs",
                    "sandbox": True,
                },
                status_code=404,
            )
        try:
            raw = index_html.read_text(encoding="utf-8")
        except OSError as e:
            return JSONResponse({"success": False, "message": str(e)}, status_code=500)
        body = inject_sandbox_banner(raw)
        return HTMLResponse(content=body)


def register_root_index(app: FastAPI, vue_dist_dir: Path) -> None:
    """GET / 直接返回注入后的 index.html（无需 SPA fallback 捕获空路径）。"""
    index_html = Path(vue_dist_dir) / "index.html"

    @app.get("/", include_in_schema=False)
    async def root_index():
        if not index_html.is_file():
            return JSONResponse(
                {
                    "success": False,
                    "message": "index.html 缺失",
                    "sandbox": True,
                },
                status_code=404,
            )
        raw = index_html.read_text(encoding="utf-8")
        return HTMLResponse(content=inject_sandbox_banner(raw))
