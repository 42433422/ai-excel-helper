"""
缓存基础设施层

在 ``app/utils/redis_cache.py`` 提供的通用 Redis 封装之上，
按业务维度提供"带版本 + 租户隔离 + 归一化 key + 指标可观测"的
语义缓存抽象，供 domain / application 层直接调用。

当前暴露：
    - ``IntentCache``：意图识别 / NLU / 产品解析等 AI 调用的语义缓存
    - ``get_intent_cache()``：默认单例（scope=intent, version=v1）
"""

from app.infrastructure.cache.intent_cache import IntentCache, get_intent_cache

__all__ = ["IntentCache", "get_intent_cache"]
