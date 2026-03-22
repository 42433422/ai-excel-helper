#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XCAGI 材料/基础数据 服务启动入口

把原 `run.py` 的全量接口拆成“warehouse”组，独立启动。
默认端口：5001（如需要可改）。
"""

from app import create_app
from app.config import DevelopmentConfig


app = create_app(DevelopmentConfig, blueprint_groups=["warehouse"])


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5001,
        debug=True,
        threaded=True,
    )

