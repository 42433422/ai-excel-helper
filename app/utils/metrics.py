# -*- coding: utf-8 -*-
"""
Prometheus 指标模块

提供应用指标采集和暴露功能。
"""

import time
from functools import wraps
from typing import Any, Callable

from flask import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, Info, generate_latest

materials_created_total = Counter(
    'materials_created_total',
    'Total number of materials created',
    ['category']
)

materials_operations_duration_seconds = Histogram(
    'materials_operations_duration_seconds',
    'Duration of materials operations in seconds',
    ['operation'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

api_requests_total = Counter(
    'api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status']
)

api_request_duration_seconds = Histogram(
    'api_request_duration_seconds',
    'API request duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

ai_requests_total = Counter(
    'ai_requests_total',
    'Total number of AI service requests',
    ['service', 'status']
)

ai_request_duration_seconds = Histogram(
    'ai_request_duration_seconds',
    'AI request duration in seconds',
    ['service'],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)
)

ai_request_errors_total = Counter(
    'ai_request_errors_total',
    'Total number of AI request errors',
    ['service', 'error_type']
)

active_requests = Gauge(
    'active_requests',
    'Number of active requests'
)

circuit_breaker_state = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=half_open, 2=open)',
    ['name']
)

circuit_breaker_failures_total = Counter(
    'circuit_breaker_failures_total',
    'Total number of circuit breaker failures',
    ['name', 'circuit_state']
)

app_info = Info(
    'app',
    'Application information'
)


def init_metrics(app_name: str, version: str):
    """初始化应用指标"""
    app_info.info({
        'name': app_name,
        'version': version
    })


def metrics_endpoint() -> Response:
    """Prometheus metrics 端点处理函数"""
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


def track_request_duration(method: str, endpoint: str):
    """请求持续时间追踪装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            active_requests.inc()
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                api_request_duration_seconds.labels(
                    method=method,
                    endpoint=endpoint
                ).observe(duration)
                return result
            finally:
                active_requests.dec()
        return wrapper
    return decorator


def track_ai_request(service: str):
    """AI 请求追踪装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                ai_requests_total.labels(service=service, status='success').inc()
                ai_request_duration_seconds.labels(service=service).observe(duration)
                return result
            except Exception as e:
                ai_requests_total.labels(service=service, status='error').inc()
                ai_request_errors_total.labels(service=service, error_type=type(e).__name__).inc()
                raise
        return wrapper
    return decorator