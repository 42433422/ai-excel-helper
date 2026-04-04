# -*- coding: utf-8 -*-
"""
AI 对话服务性能优化装饰器

为 AIConversationService 添加：
- 响应缓存
- 请求去重
- 性能监控
- 异步处理支持
"""

import functools
import hashlib
import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class AIOptimizedService:
    """
    AI 服务性能优化包装器

    用法：
        optimized_ai = AIOptimizedService(ai_service)
        result = optimized_ai.chat(user_id, message, context)
    """

    def __init__(self, ai_service):
        self._service = ai_service

        self._cache = None
        self._deduplicator = None
        self._monitor = None
        self._rate_limiter = None

        try:
            from app.utils.performance_initializer import get_performance_optimizer
            optimizer = get_performance_optimizer()

            if optimizer.redis_cache:
                self._cache = optimizer.redis_cache
            if optimizer.request_deduplicator:
                self._deduplicator = optimizer.request_deduplicator
            if optimizer.performance_monitor:
                self._monitor = optimizer.performance_monitor
            if hasattr(optimizer, 'get_rate_limiter'):
                from app.utils.rate_limiter import get_rate_limiter
                self._rate_limiter = get_rate_limiter("ai_chat", max_requests=30, window_seconds=60)

        except Exception as e:
            logger.debug(f"AI服务优化组件加载失败: {e}")

    def _make_cache_key(self, user_id: str, message: str, context: Optional[Dict] = None) -> str:
        context_hash = ""
        if context:
            import json
            context_str = json.dumps(context, sort_keys=True, default=str)
            context_hash = hashlib.md5(context_str.encode()).hexdigest()[:16]

        return f"ai_chat:v2:{user_id}:{hashlib.sha256(message.strip().lower().encode()).hexdigest()}:{context_hash}"

    def chat(
        self,
        user_id: str,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None,
        mode: Optional[str] = None,
        use_cache: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        优化的聊天方法（带缓存和监控）

        Args:
            use_cache: 是否使用缓存（默认True，设为False强制重新生成）
        """
        start_time = time.perf_counter()

        # 限流检查
        if self._rate_limiter:
            rate_result = __import__('app.utils.rate_limiter', fromlist=['check_rate_limit']).check_rate_limit(
                user_id, "ai_chat", max_requests=30, window_seconds=60
            )
            if not rate_result.get("allowed", True):
                return {
                    "text": "请求过于频繁，请稍后再试",
                    "action": "rate_limited",
                    "data": {"retry_after": rate_result.get("retry_after")},
                    "_optimized": True,
                }

        # 缓存检查（仅对简单查询启用）
        cache_key = None
        should_cache = (
            use_cache and
            self._cache and
            len(message) < 200 and
            not message.startswith("/")  # 排除命令
        )

        if should_cache:
            cache_key = self._make_cache_key(user_id, message, context)
            cached = self._cache.get(cache_key)
            if cached is not None:
                duration_ms = (time.perf_counter() - start_time) * 1000
                if self._monitor:
                    self._monitor.record_metric("ai_chat_cached", duration_ms, success=True)

                result = dict(cached)
                result["_cached"] = True
                result["_optimized"] = True
                return result

        # 执行实际对话
        try:
            with self._monitor.track("ai_chat_call") if self._monitor else _dummy_context():
                result = self._service.chat(
                    user_id=user_id,
                    message=message,
                    context=context,
                    source=source,
                    mode=mode,
                    **kwargs
                )

            duration_ms = (time.perf_counter() - start_time) * 1000

            # 记录性能指标
            if self._monitor:
                self._monitor.record_metric(
                    "ai_chat",
                    duration_ms,
                    success=True,
                    user_id=user_id[:8],
                    msg_len=len(message),
                    has_context=context is not None
                )

            # 缓存结果（仅缓存成功响应）
            if should_cache and cache_key and result.get("text"):
                try:
                    cacheable_result = {k: v for k, v in result.items() if not k.startswith("_")}
                    self._cache.set(cache_key, cacheable_result, ttl=int(__import__('os').environ.get("XCAGI_AI_RESPONSE_CACHE_TTL", "300")))
                except Exception as e:
                    logger.debug(f"AI响应缓存写入失败: {e}")

            if isinstance(result, dict):
                result["_cached"] = False
                result["_optimized"] = True
                result["_duration_ms"] = round(duration_ms, 2)

            return result

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000

            if self._monitor:
                self._monitor.record_metric("ai_chat_error", duration_ms, success=False, error=str(e)[:200])

            logger.error(f"AI对话执行失败: {e}")
            raise

    def chat_async(self, user_id: str, message: str, **kwargs) -> Dict[str, Any]:
        """
        异步聊天（提交到后台任务队列）

        Returns:
            包含 task_id 的字典
        """
        try:
            from app.utils.async_tasks import get_async_task_manager

            manager = get_async_task_manager()
            task_result = manager.submit(
                "ai_chat_task",
                args=(user_id, message),
                kwargs=kwargs,
                queue="ai"
            )

            return {
                "task_id": task_result.task_id,
                "status": task_result.status.value,
                "message": "任务已提交到队列",
                "_async": True,
            }

        except Exception as e:
            logger.warning(f"异步任务提交失败，回退同步执行: {e}")
            return self.chat(user_id, message, **kwargs)

    def clear_user_cache(self, user_id: str) -> int:
        """清除指定用户的AI对话缓存"""
        if not self._cache:
            return 0

        try:
            pattern = f"ai_chat*v2:{user_id}:*"
            cleared = self._cache.clear_pattern(pattern)
            logger.info(f"已清除用户 {user_id} 的AI缓存 ({cleared} 个键)")
            return cleared
        except Exception as e:
            logger.warning(f"清除AI缓存失败: {e}")
            return 0


def _dummy_context():
    """空上下文管理器"""
    class DummyContext:
        def __enter__(self): return self
        def __exit__(self, *args): pass
    return DummyContext()


def optimize_ai_service(ai_service_class):
    """
    AI 服务类装饰器：自动包装为优化版本

    用法：
        @optimize_ai_service
        class AIConversationService:
            ...
    """
    original_init = ai_service_class.__init__

    @functools.wraps(original_init)
    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)

        self._optimizer = AIOptimizedService(self)

    ai_service_class.__init__ = new_init

    # 添加快捷方法
    def optimized_chat(self, user_id, message, **kwargs):
        return self._optimizer.chat(user_id, message, **kwargs)

    ai_service_class.optimized_chat = optimized_chat
    ai_service_class.clear_user_cache = lambda self, uid: self._optimizer.clear_user_cache(uid)

    return ai_service_class


# 客户服务优化工具函数
class CustomerServiceOptimizer:
    """客户服务性能优化器"""

    def __init__(self):
        self._cache = None
        self._monitor = None

        try:
            from app.utils.performance_initializer import get_performance_optimizer
            optimizer = get_performance_optimizer()
            self._cache = optimizer.redis_cache
            self._monitor = optimizer.performance_monitor
        except Exception:
            pass

    @staticmethod
    def get_instance():
        if not hasattr(CustomerServiceOptimizer, '_instance'):
            CustomerServiceOptimizer._instance = CustomerServiceOptimizer()
        return CustomerServiceOptimizer._instance

    def get_customers_cached(self, fetch_func, keyword=None, page=1, per_page=20):
        """带缓存的客户列表获取"""
        cache_key = f"customers:list:{keyword or 'all'}:{page}:{per_page}"

        if self._cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached

        start_time = time.perf_counter()
        result = fetch_func(keyword=keyword, page=page, per_page=per_page)
        duration_ms = (time.perf_counter() - start_time) * 1000

        if self._monitor:
            self._monitor.record_metric("get_customers", duration_ms, success=True)

        if self._cache and result.get("success"):
            self._cache.set(cache_key, result, ttl=int(__import__('os').environ.get("XCAGI_CUSTOMER_CACHE_TTL", "600")))

        return result

    def invalidate_customer_cache(self, customer_id=None):
        """清除客户缓存"""
        if not self._cache:
            return

        try:
            if customer_id:
                self._cache.delete(f"customer:{customer_id}")
            else:
                self._cache.clear_pattern("customers:*")
                self._cache.clear_pattern("customer:*")
        except Exception as e:
            logger.warning(f"清除客户缓存失败: {e}")


# 订单/出货服务优化工具函数
class ShipmentServiceOptimizer:
    """订单/出货服务性能优化器"""

    def __init__(self):
        self._cache = None
        self._async_manager = None
        self._monitor = None

        try:
            from app.utils.performance_initializer import get_performance_optimizer
            optimizer = get_performance_optimizer()
            self._cache = optimizer.redis_cache
            self._async_manager = optimizer.async_task_manager
            self._monitor = optimizer.performance_monitor
        except Exception:
            pass

    @staticmethod
    def get_instance():
        if not hasattr(ShipmentServiceOptimizer, '_instance'):
            ShipmentServiceOptimizer._instance = ShipmentServiceOptimizer()
        return ShipmentServiceOptimizer._instance

    def create_shipment_optimized(self, create_func, data: Dict) -> Dict:
        """优化的出货单创建（带去重）"""
        dedup_key = f"shipment:create:{hash(str(sorted(data.items())))}"

        if self._cache:
            existing = self._cache.get(dedup_key)
            if existing is not None:
                return {**existing, "_deduplicated": True}

        start_time = time.perf_counter()
        result = create_func(data)
        duration_ms = (time.perf_counter() - start_time) * 1000

        if self._monitor:
            self._monitor.record_metric("create_shipment", duration_ms, success=result.get("success", False))

        if self._cache and result.get("success"):
            self._cache.set(dedup_key, result, ttl=30)  # 短时间防重复

        return result

    def generate_labels_async(self, shipment_ids: list, generate_func) -> Dict:
        """异步批量生成标签"""
        if self._async_manager and len(shipment_ids) > 5:
            task_result = self._async_manager.submit(
                "shipment_tasks.generate_labels_batch_task",
                args=(shipment_ids,),
                queue="urgent"
            )
            return {
                "task_id": task_result.task_id,
                "status": "submitted",
                "message": f"已提交 {len(shipment_ids)} 个标签生成任务",
            }

        # 少量数据同步处理
        return generate_func(shipment_ids)

    def invalidate_shipment_cache(self, shipment_id=None):
        """清除出货单缓存"""
        if not self._cache:
            return

        try:
            patterns = ["shipment:list:*", "shipment:detail:*"]
            for p in patterns:
                self._cache.clear_pattern(p)

            if shipment_id:
                self._cache.delete(f"shipment:{shipment_id}")
        except Exception as e:
            logger.warning(f"清除出货单缓存失败: {e}")
