"""
FastAPI 应用入口包。

历史代码 ``from app.fastapi_app import create_fastapi_app`` 仍有效；
实现已拆分为同目录下 ``cors`` / ``lifespan`` / ``factory`` 等子模块。
"""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_repo_root_on_sys_path() -> None:
    """把含 ``app`` 包的仓库根加入 ``sys.path``。"""
    here = Path(__file__).resolve()
    for p in here.parents:
        try:
            pkg = p / "app" / "fastapi_app" / "__init__.py"
            routes = p / "app" / "fastapi_routes"
            if pkg.is_file() and routes.is_dir():
                s = str(p)
                if s not in sys.path:
                    sys.path.insert(0, s)
                return
        except OSError:
            continue


_ensure_repo_root_on_sys_path()

from .cors import resolve_cors_allow_origin_regex, resolve_cors_allow_origins
from .factory import create_fastapi_app, get_fastapi_app
from .lifespan import lifespan

__all__ = [
    "create_fastapi_app",
    "get_fastapi_app",
    "lifespan",
    "resolve_cors_allow_origins",
    "resolve_cors_allow_origin_regex",
]
