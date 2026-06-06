"""
路径工具函数模块

提供应用目录、数据目录等路径相关工具函数。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def get_base_dir() -> str:
    """
    获取应用基础目录（兼容 PyInstaller 打包）

    Returns:
        应用基础目录路径
    """
    if hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    # path_utils.py 位于 app/utils/，仓库根目录为向上 3 级（含 FHD 根与 backend/ 等）
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def resolve_fhd_repo_root(anchor: Path | None = None) -> Path | None:
    """
    解析 FHD 单仓根目录（含 app/、backend/、mods/ 等）。

    从 anchor 目录向上查找第一个存在 app/fastapi_app 包（__init__.py）的目录。
    """
    start = anchor if anchor is not None else Path(__file__).resolve()
    start = Path(start).resolve()
    if start.is_file():
        start = start.parent
    for d in (start, *start.parents):
        marker = d / "app" / "fastapi_app" / "__init__.py"
        if marker.is_file():
            return d
    return None


def ensure_fhd_repo_on_syspath(anchor: Path | None = None) -> Path | None:
    """
    将 FHD 仓库根目录加入 sys.path（若尚未加入），供 backend.* 等顶层包导入。

    Celery / 审计初始化等可在非标准 cwd 下调用。
    """
    root = resolve_fhd_repo_root(anchor)
    if root is None:
        return None
    s = str(root)
    if s not in sys.path:
        sys.path.insert(0, s)
    return root


def get_resources_dir() -> str:
    """
    获取项目资源目录（用于放置模板/配置/外部工具数据等，避免依赖项目外路径）。

    Returns:
        resources 目录路径
    """
    return os.path.join(get_base_dir(), "resources")


def get_resource_path(*parts: str) -> str:
    """拼接 resources 下的路径。"""
    return os.path.join(get_resources_dir(), *parts)


def get_app_data_dir() -> str:
    """
    获取应用程序数据目录

    Returns:
        应用程序数据目录路径
    """
    explicit = os.environ.get("XCAGI_DATA_DIR") or os.environ.get("XCAGI_DESKTOP_DATA_DIR")
    if explicit:
        app_data_dir = explicit
    else:
        base = get_base_dir()
        if hasattr(sys, "_MEIPASS"):
            if sys.platform == "darwin":
                app_data_dir = os.path.join(
                    os.path.expanduser("~"),
                    "Library",
                    "Application Support",
                    "XCAGI",
                )
            else:
                app_data = (
                    os.environ.get("APPDATA")
                    or os.environ.get("LOCALAPPDATA")
                    or os.path.expanduser("~")
                )
                app_data_dir = os.path.join(app_data, "XCAGI")
        else:
            app_data_dir = base

    os.makedirs(app_data_dir, exist_ok=True)
    return app_data_dir


def get_data_dir() -> str:
    """
    获取数据目录（用于存放数据库等数据文件）

    Returns:
        数据目录路径
    """
    return os.path.join(get_app_data_dir(), "data")


def get_upload_dir() -> str:
    """
    获取上传文件目录

    Returns:
        上传文件目录路径
    """
    upload_dir = os.path.join(get_app_data_dir(), "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def get_log_dir() -> str:
    """
    获取日志文件目录

    Returns:
        日志文件目录路径
    """
    log_dir = os.path.join(get_app_data_dir(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def get_db_path(db_name: str = "products.db") -> str:
    """
    获取数据库文件路径

    Args:
        db_name: 数据库文件名

    Returns:
        数据库文件完整路径
    """
    return os.path.join(get_data_dir(), db_name)


def ensure_dir(directory: str) -> str:
    """
    确保目录存在，如果不存在则创建

    Args:
        directory: 目录路径

    Returns:
        目录路径
    """
    os.makedirs(directory, exist_ok=True)
    return directory
