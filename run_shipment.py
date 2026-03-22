#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XCAGI 发货/AI助手 服务启动入口

把原 `run.py` 的全量接口拆成“shipment”组，独立启动。
默认端口：5000（如端口冲突可改）。
"""

from app import create_app
from app.config import DevelopmentConfig


# shipment 进程原本只注册“出货/AI助手”相关路由；
# 但前端 `chat.js` 依赖对话/偏好接口（conversations 组），不加入会导致 404。
app = create_app(DevelopmentConfig, blueprint_groups=["all"])


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        threaded=True,
    )

