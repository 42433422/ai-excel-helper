#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XCAGI 应用启动入口

开发环境启动脚本。
"""

import os
import sys

# Force UTF-8 for stdout/stderr so Windows console doesn't render Chinese
# as "ï¿½ï¿½..." (looks like "code rain" in logs).
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("DATABASE_URL", "sqlite:///e:/FHD/XCAGI/products.db")
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    # Best-effort; don't block server startup.
    pass

# 在导入 app 之前固定 mods 目录，避免 ModManager 单例首次创建时扫错路径（工作目录无关）。
_RUN_DIR = os.path.dirname(os.path.abspath(__file__))
_MODS_DIR = os.path.join(_RUN_DIR, "mods")
# 强制清除 XCAGI_DISABLE_MODS 环境变量，确保 mods 能够加载
if "XCAGI_DISABLE_MODS" in os.environ:
    del os.environ["XCAGI_DISABLE_MODS"]
if os.path.isdir(_MODS_DIR) and not (os.environ.get("XCAGI_MODS_ROOT") or os.environ.get("XCAGI_MODS_DIR") or "").strip():
    os.environ["XCAGI_MODS_ROOT"] = os.path.abspath(_MODS_DIR)

from app import create_app
from app.config import DevelopmentConfig

# 创建 Flask 应用
app = create_app(DevelopmentConfig)


if __name__ == "__main__":
    # 启动开发服务器
    # host="0.0.0.0" 允许外部访问
    # port=5000 默认端口
    # debug=True 启用调试模式
    debug_flag = os.environ.get("XCAGI_DEBUG", "0").lower() in {"1", "true", "yes", "on"}
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=debug_flag,
        threaded=True
    )
