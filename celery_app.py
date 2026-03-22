#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Celery 应用配置

用于 Celery worker 启动的配置文件。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.config import DevelopmentConfig
from app.extensions import celery_app

app = create_app(DevelopmentConfig)

celery_app.autodiscover_tasks(['app.tasks'])


celery_app.conf.task_routes = {
    'app.tasks.wechat_tasks.*': {'queue': 'wechat'},
    'app.tasks.shipment_tasks.generate_shipment_order': {'queue': 'urgent'},
    'app.tasks.shipment_tasks.generate_parallel_shipment_orders': {'queue': 'urgent'},
    'app.tasks.shipment_tasks.export_shipment_records_task': {'queue': 'normal'},
    'app.tasks.shipment_tasks.import_products_batch_task': {'queue': 'normal'},
    'app.tasks.shipment_tasks.generate_labels_batch_task': {'queue': 'normal'},
    'app.tasks.shipment_tasks.cleanup_old_shipment_documents': {'queue': 'background'},
}

celery_app.conf.task_default_queue = 'normal'
celery_app.conf.task_default_exchange = 'default'
celery_app.conf.task_default_routing_key = 'normal'

celery_app.conf.worker_prefetch_multiplier = 4
celery_app.conf.worker_max_tasks_per_child = 1000

celery_app.conf.beat_schedule = {
    'scan-wechat-messages': {
        'task': 'app.tasks.wechat_tasks.scan_wechat_messages',
        'schedule': 30.0,
        'options': {'limit': 20}
    },
    'cleanup-old-tasks': {
        'task': 'app.tasks.wechat_tasks.cleanup_old_tasks',
        'schedule': 86400.0,
        'options': {'days': 30}
    },
    'cleanup-old-documents': {
        'task': 'app.tasks.shipment_tasks.cleanup_old_shipment_documents',
        'schedule': 86400.0,
        'options': {'days': 90}
    },
}


if __name__ == "__main__":
    argv = sys.argv[1:]
    celery_app.start(argv)
