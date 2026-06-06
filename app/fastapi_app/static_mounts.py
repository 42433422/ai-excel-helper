"""Vue 产物静态目录挂载。"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.utils.path_utils import get_base_dir

logger = logging.getLogger(__name__)


def mount_vue_dist_public_static(app: FastAPI) -> None:
    """挂载与 Vite ``public/`` 对齐的根路径静态目录（须在 SPA fallback 之前）。"""
    vue_dist = os.path.join(get_base_dir(), "templates", "vue-dist")
    if not os.path.isdir(vue_dist):
        logger.warning("Vue dist 目录不存在，跳过 public 静态挂载: %s", vue_dist)
        return
    for sub in ("font-awesome", "startup", "yuangong", "workflow"):
        directory = os.path.join(vue_dist, sub)
        if not os.path.isdir(directory):
            continue
        mount_path = f"/{sub}"
        try:
            app.mount(mount_path, StaticFiles(directory=directory), name=f"vue-dist-{sub}")
            logger.info("Mounted Vue static: %s -> %s", mount_path, directory)
        except Exception as e:
            logger.warning("挂载 %s 失败: %s", mount_path, e)


def mount_vue_dist_assets_dir(app: FastAPI) -> None:
    """挂载 Vite 产物 ``vue-dist/assets`` 到 ``/assets``（须在 SPA fallback 之前）。"""
    vue_dist = os.path.join(get_base_dir(), "templates", "vue-dist")
    assets_dir = os.path.join(vue_dist, "assets")
    if not os.path.isdir(assets_dir):
        logger.warning("Vue dist assets 目录不存在，跳过 /assets 挂载: %s", assets_dir)
        return
    try:
        app.mount("/assets", StaticFiles(directory=assets_dir), name="vue_dist_assets")
        logger.info("Mounted Vue dist assets: /assets -> %s", assets_dir)
    except Exception as e:
        logger.warning("挂载 /assets 失败: %s", e)
