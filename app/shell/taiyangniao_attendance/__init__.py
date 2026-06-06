"""兼容 shim：历史上 ``app.shell.taiyangniao_attendance`` 承载了太阳鸟 PRO 的考勤
实现；实际代码已迁入 ``mods/taiyangniao-pro/backend/taiyangniao_attendance/``。

本包下的每个子模块都只做一件事——把 mod 的同名模块 re-export 过来——这样
老的调用方（开发脚本、``app.mod_sdk.attendance``）继续可用，而新增的 mod 能
在没有宿主代码的环境下自给自足。
"""

from __future__ import annotations

import importlib
import os
import sys


def _ensure_mod_backend_on_path() -> None:
    here = os.path.abspath(os.path.dirname(__file__))
    # app/shell/taiyangniao_attendance -> repo_root
    repo_root = os.path.abspath(os.path.join(here, "..", "..", ".."))
    mod_backend = os.path.join(repo_root, "mods", "taiyangniao-pro", "backend")
    if os.path.isdir(mod_backend) and mod_backend not in sys.path:
        sys.path.insert(0, mod_backend)


def _load_mod_submodule(stem: str):
    _ensure_mod_backend_on_path()
    return importlib.import_module(f"taiyangniao_attendance.{stem}")


__all__ = ["_load_mod_submodule"]
