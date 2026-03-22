# -*- coding: utf-8 -*-
"""
指标路由

提供 Prometheus 指标端点。
"""

from flask import Blueprint, Response

from app.utils.metrics import metrics_endpoint

metrics_bp = Blueprint("metrics", __name__)


@metrics_bp.route("/metrics", methods=["GET"])
def get_metrics() -> Response:
    """
    Prometheus metrics 端点

    Returns:
        Prometheus 格式的指标数据
    """
    return metrics_endpoint()