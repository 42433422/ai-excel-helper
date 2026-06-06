"""
Neuro 读写全量 trace 的环境开关与采样（HTTP / Application 分层）。

不修改业务逻辑；仅被中间件与桥接读取。
"""

from __future__ import annotations

import os
import random
from functools import lru_cache


def _truthy(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@lru_cache(maxsize=1)
def is_neuro_http_trace_enabled() -> bool:
    return _truthy(os.environ.get("XCAGI_NEURO_HTTP_TRACE", ""))


def neuro_http_sample_rate() -> float:
    try:
        v = float(os.environ.get("XCAGI_NEURO_HTTP_SAMPLE", "0") or 0.0)
    except ValueError:
        return 0.0
    return max(0.0, min(1.0, v))


def neuro_http_body_preview_max() -> int:
    try:
        return max(0, int(os.environ.get("XCAGI_NEURO_HTTP_BODY_MAX", "0") or 0))
    except ValueError:
        return 0


def neuro_app_service_sample_rate() -> float:
    try:
        raw = os.environ.get("XCAGI_NEURO_APP_SAMPLE", "")
        if raw is None or str(raw).strip() == "":
            return 1.0
        v = float(raw)
    except ValueError:
        return 1.0
    return max(0.0, min(1.0, v))


def should_sample_http() -> bool:
    if not is_neuro_http_trace_enabled():
        return False
    r = neuro_http_sample_rate()
    if r >= 1.0:
        return True
    if r <= 0.0:
        return False
    return random.random() < r


def should_sample_app_service() -> bool:
    r = neuro_app_service_sample_rate()
    if r >= 1.0:
        return True
    if r <= 0.0:
        return False
    return random.random() < r


def is_neuro_domain_metrics_enabled() -> bool:
    return _truthy(os.environ.get("XCAGI_NEURO_DOMAIN_METRICS", ""))


def is_neuro_service_layer_trace_enabled() -> bool:
    """Services 层 trace；默认开启，设 XCAGI_NEURO_SERVICE_TRACE=0 关闭。"""
    return os.environ.get("XCAGI_NEURO_SERVICE_TRACE", "1").strip().lower() not in {
        "0",
        "false",
        "off",
        "no",
    }


def clear_neuro_trace_config_cache() -> None:
    """供测试重置。"""
    is_neuro_http_trace_enabled.cache_clear()


# 各 NeuroDomain handler 在 XCAGI_NEURO_DOMAIN_METRICS=1 时的轻量计数（无副作用）。
_DOMAIN_HANDLER_METRICS: dict[str, int] = {}


def bump_domain_handler_metric(metric_key: str) -> None:
    """领域事件 handler 内调用；key 建议 ``<domain>.<event_type>``。"""
    if not is_neuro_domain_metrics_enabled():
        return
    try:
        _DOMAIN_HANDLER_METRICS[metric_key] = _DOMAIN_HANDLER_METRICS.get(metric_key, 0) + 1
    except Exception:
        pass


def get_domain_handler_metrics() -> dict[str, int]:
    return dict(_DOMAIN_HANDLER_METRICS)


def clear_domain_handler_metrics() -> None:
    """供单测隔离。"""
    _DOMAIN_HANDLER_METRICS.clear()
