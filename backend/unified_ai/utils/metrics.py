"""
指标收集模块
"""

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricRecord:
    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: dict[str, str] = field(default_factory=dict)


class MetricsCollector:
    def __init__(self):
        self._counters: dict[str, int] = defaultdict(int)
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._gauges: dict[str, float] = {}
        self._lock = threading.RLock()
        self._records: list[MetricRecord] = []

    def inc(self, name: str, value: int = 1, tags: dict[str, str] | None = None) -> None:
        with self._lock:
            self._counters[name] += value
            self._records.append(MetricRecord(name=name, value=value, tags=tags or {}))

    def histogram(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        with self._lock:
            self._histograms[name].append(value)
            self._records.append(MetricRecord(name=name, value=value, tags=tags or {}))

    def gauge(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        with self._lock:
            self._gauges[name] = value

    def get_counter(self, name: str) -> int:
        with self._lock:
            return self._counters.get(name, 0)

    def get_histogram_stats(self, name: str) -> dict[str, float]:
        with self._lock:
            values = self._histograms.get(name, [])
            if not values:
                return {"count": 0, "min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}

            sorted_values = sorted(values)
            count = len(sorted_values)
            return {
                "count": count,
                "min": sorted_values[0],
                "max": sorted_values[-1],
                "avg": sum(sorted_values) / count,
                "p50": sorted_values[int(count * 0.5)],
                "p95": sorted_values[int(count * 0.95)] if count > 1 else sorted_values[0],
                "p99": sorted_values[int(count * 0.99)] if count > 1 else sorted_values[0],
            }

    def get_all_stats(self) -> dict[str, Any]:
        with self._lock:
            result = {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {
                    name: self.get_histogram_stats(name)
                    for name in self._histograms.keys()
                }
            }
            return result

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._histograms.clear()
            self._gauges.clear()
            self._records.clear()


_metrics: MetricsCollector | None = None


def get_metrics() -> MetricsCollector:
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics
