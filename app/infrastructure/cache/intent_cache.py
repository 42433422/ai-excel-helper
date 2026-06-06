"""
意图识别 / AI 语义调用的缓存层

设计要点（对应前述讨论里的"四条硬要求"）：

1. **key 归一化**：去前后空白、折叠内部空白、lower；避免"帮我 开单"/"帮我开单"
   两条在 Redis 里各占一个 key，命中率被白白砍半。
2. **版本 + 租户隔离**：key 结构 ``{scope}:v{version}:{mod_id}:{sha256_16}``。
   - ``version`` 随 prompt / 模型升级递增，老缓存自动失效，不用手动 FLUSH；
   - ``mod_id`` 绑定 ``app.request_active_mod_ctx``，天然做到多租户隔离，
     A mod 的缓存不会污染 B mod。
3. **命中/未命中均上报指标**（``intent_cache_*``），跑一周看 hit_rate，
   决定是否保留或扩大接入范围。
4. **永远不让缓存故障变成业务故障**：底层 Redis 异常、序列化异常、甚至
   ``compute_fn`` 以外的任何错误，都降级到原 API 调用。

此模块刻意**不直接依赖 HTTP 请求对象**——调用方显式把
``mod_id`` 传进来，便于单元测试与非 HTTP 场景（Celery、CLI、后台任务）复用。
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import time
from collections.abc import Callable
from typing import Any

from app.utils.redis_cache import RedisCache, get_redis_cache

logger = logging.getLogger(__name__)

_WHITESPACE_RE = re.compile(r"\s+")

_DEFAULT_SCOPE = "intent"
_DEFAULT_VERSION = os.environ.get("XCAGI_INTENT_CACHE_VERSION", "1")
_DEFAULT_TTL = int(os.environ.get("XCAGI_INTENT_CACHE_TTL", "900"))  # 15 min
_ENABLED = (os.environ.get("XCAGI_INTENT_CACHE_ENABLED", "1") or "1").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def _normalize_text(text: str) -> str:
    """粗粒度归一化：足以解决"多余空白 + 大小写"这类低价值差异。

    故意不做更激进的归一化（比如去标点、简繁转换），因为意图识别对
    "你好" vs "你好？"是敏感的，过度归一化会把语义不同的输入合并，
    反而降低准确率。
    """
    if not text:
        return ""
    return _WHITESPACE_RE.sub(" ", text.strip()).lower()


def _digest(text: str) -> str:
    """short sha256 — 16 hex chars ≈ 64 bit，冲撞概率对缓存场景可忽略。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


class IntentCache:
    """语义缓存抽象。

    用法（推荐）：

        cache = get_intent_cache()
        result = cache.get_or_compute(
            text=user_text,
            mod_id=get_request_active_mod_id(),
            compute_fn=lambda: recognizer._raw_recognize(user_text),
        )

    直接调用 ``get`` / ``set`` 也可以，但 ``get_or_compute`` 才包含
    完整的指标采集和降级逻辑，**业务代码优先用它**。
    """

    def __init__(
        self,
        scope: str = _DEFAULT_SCOPE,
        version: str = _DEFAULT_VERSION,
        default_ttl: int = _DEFAULT_TTL,
        backend: RedisCache | None = None,
        enabled: bool | None = None,
    ):
        self._scope = scope
        self._version = str(version)
        self._default_ttl = int(default_ttl)
        self._backend = backend
        self._enabled = _ENABLED if enabled is None else bool(enabled)

    def _resolve_backend(self) -> RedisCache | None:
        if self._backend is not None:
            return self._backend
        try:
            client = _build_redis_client()
            if client is None:
                return None
            self._backend = get_redis_cache(client)
            return self._backend
        except Exception as e:
            logger.debug("IntentCache: Redis backend not available: %s", e)
            return None

    def make_key(self, text: str, mod_id: str | None) -> str:
        norm = _normalize_text(text)
        tenant = (mod_id or "_global").strip() or "_global"
        return f"{self._scope}:v{self._version}:{tenant}:{_digest(norm)}"

    def get(self, text: str, mod_id: str | None = None) -> Any:
        if not self._enabled or not text:
            return None
        backend = self._resolve_backend()
        if backend is None:
            return None
        try:
            return backend.get(self.make_key(text, mod_id))
        except Exception as e:
            logger.debug("IntentCache.get failed: %s", e)
            _observe_error(self._scope, "get")
            return None

    def set(
        self,
        text: str,
        value: Any,
        mod_id: str | None = None,
        ttl: int | None = None,
    ) -> bool:
        if not self._enabled or not text or value is None:
            return False
        backend = self._resolve_backend()
        if backend is None:
            return False
        try:
            return bool(
                backend.set(self.make_key(text, mod_id), value, ttl=ttl or self._default_ttl)
            )
        except Exception as e:
            logger.debug("IntentCache.set failed: %s", e)
            _observe_error(self._scope, "set")
            return False

    def get_or_compute(
        self,
        text: str,
        compute_fn: Callable[[], Any],
        mod_id: str | None = None,
        ttl: int | None = None,
        should_cache: Callable[[Any], bool] | None = None,
    ) -> Any:
        """先查缓存，未命中则调用 ``compute_fn`` 并回填。

        Args:
            text: 原始用户输入；内部会做归一化 + 哈希，不存明文。
            compute_fn: 真正产生结果的函数（会调 API / 模型），无参。
            mod_id: 租户隔离键；调用方通常传 ``get_request_active_mod_id()``。
            ttl: 本次覆盖默认 TTL；None 走构造时的默认值。
            should_cache: 过滤不值得缓存的结果（如 intent=unk、confidence=0）。
                默认规则见 :func:`_default_should_cache_intent`。

        永远返回 ``compute_fn`` 的结果语义——缓存层自身异常不抛出。
        """

        if not self._enabled:
            return compute_fn()

        key = None
        backend = self._resolve_backend()
        if backend is not None and text:
            try:
                key = self.make_key(text, mod_id)
                cached = backend.get(key)
                if cached is not None:
                    _observe_hit(self._scope, mod_id)
                    return cached
            except Exception as e:
                logger.debug("IntentCache lookup failed: %s", e)
                _observe_error(self._scope, "lookup")

        start = time.perf_counter()
        result = compute_fn()
        elapsed = time.perf_counter() - start

        _observe_miss(self._scope, mod_id, elapsed)

        predicate = should_cache or _default_should_cache_intent
        if key is not None and backend is not None:
            try:
                if predicate(result):
                    backend.set(key, result, ttl=ttl or self._default_ttl)
            except Exception as e:
                logger.debug("IntentCache set failed: %s", e)
                _observe_error(self._scope, "set")

        return result

    def invalidate(self, text: str, mod_id: str | None = None) -> None:
        backend = self._resolve_backend()
        if backend is None or not text:
            return
        try:
            backend.delete(self.make_key(text, mod_id))
        except Exception as e:
            logger.debug("IntentCache.invalidate failed: %s", e)


def _default_should_cache_intent(result: Any) -> bool:
    """默认不缓存"没识别出来"的结果——等下一次重试有新引擎兜底。"""
    if result is None:
        return False
    if isinstance(result, dict):
        intent = result.get("intent")
        conf = result.get("confidence") or 0
        if not intent or intent == "unk":
            return False
        if conf is not None and float(conf) <= 0:
            return False
    return True


# ---------------------------------------------------------------------------
# backend / metrics helpers
# ---------------------------------------------------------------------------


def _build_redis_client():
    """按 ``CACHE_REDIS_URL`` 惰性构建 redis 连接；失败返回 ``None``。

    之所以自己构建而不是复用 ``init_redis_cache_from_app``，是因为后者
    依赖应用实例；DDD 迁移过程里我们优先让 domain 层可脱壳运行。
    """
    try:
        import redis  # type: ignore
    except Exception:
        return None
    url = (
        os.environ.get("CACHE_REDIS_URL")
        or os.environ.get("REDIS_URL")
        or "redis://localhost:6379/0"
    )
    try:
        client = redis.from_url(url, decode_responses=True, socket_connect_timeout=1)
        client.ping()
        return client
    except Exception as e:
        logger.debug("IntentCache: redis.from_url(%s) failed: %s", url, e)
        return None


def _observe_hit(scope: str, mod_id: str | None) -> None:
    try:
        from app.utils import metrics as _m

        _m.intent_cache_hits_total.labels(scope=scope, mod_id=mod_id or "_global").inc()
    except Exception:
        pass


def _observe_miss(scope: str, mod_id: str | None, elapsed_sec: float) -> None:
    try:
        from app.utils import metrics as _m

        _m.intent_cache_misses_total.labels(scope=scope, mod_id=mod_id or "_global").inc()
        _m.intent_cache_compute_seconds.labels(scope=scope).observe(elapsed_sec)
    except Exception:
        pass


def _observe_error(scope: str, stage: str) -> None:
    try:
        from app.utils import metrics as _m

        _m.intent_cache_errors_total.labels(scope=scope, stage=stage).inc()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# singletons
# ---------------------------------------------------------------------------

_default_intent_cache: IntentCache | None = None


def get_intent_cache() -> IntentCache:
    """``scope=intent`` 的默认单例。其他 scope（embedding、product_parse）
    可以自己 ``IntentCache(scope="embedding", version="1", default_ttl=7*86400)``。
    """
    global _default_intent_cache
    if _default_intent_cache is None:
        _default_intent_cache = IntentCache()
    return _default_intent_cache
