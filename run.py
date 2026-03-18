#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
XCAGI 应用启动入口

开发环境启动脚本。
"""

from app import create_app
from app.config import DevelopmentConfig

# 创建 Flask 应用
app = create_app(DevelopmentConfig)


if __name__ == "__main__":
    # 启动开发服务器
    # host="0.0.0.0" 允许外部访问
    # port=5000 默认端口
    # debug=True 启用调试模式
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        threaded=True
    )
