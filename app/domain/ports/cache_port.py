from __future__ import annotations

from typing import Any, Callable, Protocol


class IntentCachePort(Protocol):
    def get_or_compute(
        self,
        text: str,
        mod_id: str,
        compute_fn: Callable[[], dict[str, Any]],
    ) -> dict[str, Any]: ...


_cache_instance: IntentCachePort | None = None


def set_intent_cache(cache: IntentCachePort) -> None:
    global _cache_instance
    _cache_instance = cache


def get_intent_cache_port() -> IntentCachePort | None:
    return _cache_instance
