#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Celery 应用配置

用于 Celery worker 启动的配置文件。
"""

import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.config import DevelopmentConfig
from app.extensions import celery_app

# 创建 Flask 应用（用于加载配置）
app = create_app(DevelopmentConfig)

# 自动发现并注册任务
celery_app.autodiscover_tasks(['app.tasks'])


# 定期任务配置
celery_app.conf.beat_schedule = {
    'scan-wechat-messages': {
        'task': 'app.tasks.wechat_tasks.scan_wechat_messages',
        'schedule': 30.0,  # 每 30 秒扫描一次
        'options': {'limit': 20}
    },
    'cleanup-old-tasks': {
        'task': 'app.tasks.wechat_tasks.cleanup_old_tasks',
        'schedule': 86400.0,  # 每天执行一次
        'options': {'days': 30}
    },
    'cleanup-old-documents': {
        'task': 'app.tasks.shipment_tasks.cleanup_old_shipment_documents',
        'schedule': 86400.0,  # 每天执行一次
        'options': {'days': 90}
    },
}

# Celery 其他配置
celery_app.conf.task_routes = {
    'app.tasks.wechat_tasks.*': {'queue': 'wechat'},
    'app.tasks.shipment_tasks.*': {'queue': 'shipment'},
}

if __name__ == "__main__":
    # 如果直接运行此文件，启动 Celery worker
    # 使用示例：python celery_app.py worker -l info
    argv = sys.argv[1:]
    celery_app.start(argv)
