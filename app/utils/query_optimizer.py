# -*- coding: utf-8 -*-
"""
数据库查询优化器

提供查询性能优化工具：
- 查询结果缓存
- 批量操作优化
- N+1 查询检测和预防
- 慢查询日志
- 连接池管理
- 分页优化
"""

import functools
import logging
import time
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')

SLOW_QUERY_THRESHOLD = float(__import__('os').environ.get("XCAGI_SLOW_QUERY_THRESHOLD", "0.5"))
MAX_BATCH_SIZE = int(__import__('os').environ.get("XCAGI_MAX_BATCH_SIZE", "100"))


@dataclass
class QueryStats:
    """查询统计"""
    query_id: str
    sql: str
    duration_ms: float
    rows_affected: int = 0
    is_slow: bool = False
    traceback_str: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class BatchResult:
    """批量操作结果"""
    success_count: int = 0
    failed_count: int = 0
    errors: List[str] = field(default_factory=list)
    total_duration_ms: float = 0.0


class QueryOptimizer:
    """
    查询优化器

    提供：
    - 查询缓存装饰器
    - 批量操作工具
    - 慢查询监控
    - 性能分析工具
    """

    def __init__(self):
        self._query_stats: List[QueryStats] = []
        self._slow_queries: List[QueryStats] = []
        self._max_stats = 1000

    def record_query(
        self,
        sql: str,
        duration_ms: float,
        rows_affected: int = 0,
        include_traceback: bool = False
    ) -> None:
        """记录查询统计信息"""
        stats = QueryStats(
            query_id=f"q_{len(self._query_stats)}",
            sql=sql[:500],
            duration_ms=duration_ms,
            rows_affected=rows_affected,
            is_slow=duration_ms > SLOW_QUERY_THRESHOLD * 1000,
            traceback_str=traceback.format_stack()[-5:] if include_traceback else "",
            timestamp=time.time()
        )

        self._query_stats.append(stats)

        if stats.is_slow:
            self._slow_queries.append(stats)
            logger.warning(
                f"慢查询检测 [{stats.query_id}]: {duration_ms:.2f}ms > {SLOW_QUERY_THRESHOLD*1000:.0f}ms | SQL: {sql[:200]}"
            )

        if len(self._query_stats) > self._max_stats:
            self._query_stats = self._query_stats[-self._max_stats:]

    @contextmanager
    def track_query(self, sql: str = "", include_traceback: bool = False):
        """
        查询跟踪上下文管理器

        用法：
            with optimizer.track_query("SELECT * FROM products"):
                result = db.session.query(Product).all()
        """
        start_time = time.perf_counter()
        yield
        duration_ms = (time.perf_counter() - start_time) * 1000
        self.record_query(sql, duration_ms, include_traceback=include_traceback)

    def cached_query(
        self,
        cache_key_func: Optional[Callable] = None,
        ttl: int = 300,
        cache_instance=None
    ):
        """
        查询结果缓存装饰器

        用法：
            @optimizer.cached_query(ttl=600)
            def get_products_by_category(category_id):
                return db.session.query(Product).filter(...).all()
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                cache = None

                if cache_instance:
                    cache = cache_instance
                else:
                    try:
                        from app.utils.redis_cache import get_redis_cache
                        cache = get_redis_cache()
                    except Exception:
                        pass

                key = cache_key_func(*args, **kwargs) if cache_key_func else f"query:{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"

                if cache:
                    cached_result = cache.get(key)
                    if cached_result is not None:
                        return cached_result

                start_time = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    duration_ms = (time.perf_counter() - start_time) * 1000

                    if cache:
                        cache.set(key, result, ttl=ttl)

                    self.record_query(f"CACHED:{func.__name__}", duration_ms)
                    return result

                except Exception as e:
                    logger.error(f"缓存查询执行失败 [{func.__name__}]: {e}")
                    raise

            wrapper.invalidate_cache = lambda *a, **kw: (
                cache.delete(cache_key_func(*a, **kw) if cache_key_func else f"query:{func.__name__}:{str(a)}:{str(sorted(kw.items()))}")
                if cache else None
            )
            return wrapper
        return decorator

    def batch_execute(
        self,
        items: List[Any],
        execute_func: Callable[[Any], T],
        batch_size: int = MAX_BATCH_SIZE,
        continue_on_error: bool = True,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> BatchResult:
        """
        批量执行操作

        Args:
            items: 要处理的项目列表
            execute_func: 单项处理函数
            batch_size: 每批大小
            continue_on_error: 是否在错误时继续
            progress_callback: 进度回调函数 (current, total)

        Returns:
            BatchResult 包含执行结果
        """
        result = BatchResult()
        total_items = len(items)
        start_time = time.perf_counter()

        for i in range(0, total_items, batch_size):
            batch = items[i:i + batch_size]

            for item in batch:
                try:
                    execute_func(item)
                    result.success_count += 1
                except Exception as e:
                    result.failed_count += 1
                    error_msg = f"项目 {i + result.success_count + result.failed_count} 处理失败: {str(e)}"
                    result.errors.append(error_msg)
                    logger.error(error_msg)

                    if not continue_on_error:
                        break

                if progress_callback and (result.success_count + result.failed_count) % 10 == 0:
                    progress_callback(result.success_count + result.failed_count, total_items)

            if not continue_on_error and result.failed_count > 0:
                break

        result.total_duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"批量执行完成: 成功={result.success_count}, 失败={result.failed_count}, "
            f"耗时={result.total_duration_ms:.2f}ms"
        )

        return result

    def batch_insert(
        self,
        session,
        model_class,
        items: List[Dict[str, Any]],
        batch_size: int = MAX_BATCH_SIZE
    ) -> BatchResult:
        """批量插入数据库记录"""
        def insert_item(item_data: Dict[str, Any]):
            instance = model_class(**item_data)
            session.add(instance)

        try:
            result = self.batch_execute(items, insert_item, batch_size)
            session.commit()
            return result
        except Exception as e:
            session.rollback()
            logger.error(f"批量插入失败: {e}")
            raise

    def optimized_pagination(
        self,
        query,
        page: int = 1,
        per_page: int = 20,
        max_per_page: int = 100
    ) -> Tuple[List[Any], int, Dict[str, Any]]:
        """
        优化的分页查询

        使用 COUNT(*) OVER() 窗口函数或单独的 COUNT 查询优化分页

        Returns:
            (items, total, metadata)
        """
        per_page = min(max(per_page, 1), max_per_page)
        page = max(page, 1)
        offset = (page - 1) * per_page

        metadata = {
            "page": page,
            "per_page": per_page,
            "offset": offset,
        }

        start_time = time.perf_counter()

        try:
            count_query = query.statement.with_only_columns([query.count()]).order_by(None)
            total = query.session.execute(count_query).scalar() or 0

            paginated_query = query.offset(offset).limit(per_page)
            items = paginated_query.all()

            duration_ms = (time.perf_counter() - start_time) * 1000
            self.record_query(f"PAGINATED:total={total}", duration_ms, rows_affected=len(items))

            metadata.update({
                "total": total,
                "pages": (total + per_page - 1) // per_page,
                "has_next": offset + per_page < total,
                "has_prev": page > 1,
                "duration_ms": round(duration_ms, 2),
            })

            return items, total, metadata

        except Exception as e:
            logger.error(f"分页查询失败: {e}")
            raise

    def eager_load(
        self,
        query,
        relationships: List[str]
    ):
        """
        预加载关联关系（解决 N+1 问题）

        用法：
            query = optimizer.eager_load(
                db.session.query(Order),
                ['customer', 'items.product']
            )
        """
        from sqlalchemy.orm import joinedload, selectinload, subqueryload

        loaded_query = query
        for rel in relationships:
            if '.' in rel:
                parts = rel.split('.')
                loaded_query = loaded_query.options(
                    selectinload(getattr(loaded_query._entity_zero().class_, parts[0])).selectinload(
                        getattr(loaded_query._entity_zero().class_, parts[0]).prop.mapper.class_,
                        parts[1]
                    ) if len(parts) > 1 else selectinload(getattr(loaded_query._entity_zero().class_, parts[0]))
                )
            else:
                loaded_query = loaded_query.options(selectinload(getattr(loaded_query._entity_zero().class_, rel)))

        return loaded_query

    @property
    def stats(self) -> Dict[str, Any]:
        """获取查询统计"""
        total_queries = len(self._query_stats)
        slow_count = len(self._slow_queries)

        avg_duration = 0.0
        if total_queries > 0:
            durations = [q.duration_ms for q in self._query_stats]
            avg_duration = sum(durations) / len(durations)

        return {
            "total_queries": total_queries,
            "slow_queries": slow_count,
            "avg_duration_ms": round(avg_duration, 3),
            "slow_query_rate": round(slow_count / total_queries * 100, 2) if total_queries > 0 else 0,
            "recent_slow_queries": [
                {
                    "id": q.query_id,
                    "duration_ms": round(q.duration_ms, 2),
                    "sql": q.sql[:100]
                }
                for q in self._slow_queries[-10:]
            ]
        }

    def get_slow_queries(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取慢查询列表"""
        return [
            {
                "query_id": q.query_id,
                "sql": q.sql,
                "duration_ms": round(q.duration_ms, 2),
                "rows_affected": q.rows_affected,
                "timestamp": q.timestamp,
            }
            for q in sorted(self._slow_queries, key=lambda x: x.duration_ms, reverse=True)[:limit]
        ]

    def clear_stats(self) -> None:
        """清除统计信息"""
        self._query_stats.clear()
        self._slow_queries.clear()


_optimizer_instance: Optional[QueryOptimizer] = None


def get_query_optimizer() -> QueryOptimizer:
    """获取查询优化器单例"""
    global _optimizer_instance
    if _optimizer_instance is None:
        _optimizer_instance = QueryOptimizer()
    return _optimizer_instance


def optimize_query(ttl: int = 300):
    """
    查询优化装饰器（快捷方式）

    用法：
        @optimize_query(ttl=600)
        def get_expensive_data():
            ...
    """
    optimizer = get_query_optimizer()
    return optimizer.cached_query(ttl=ttl)


def batch_operation(batch_size: int = MAX_BATCH_SIZE):
    """
    批量操作装饰器

    将列表参数自动拆分为批次处理

    用法：
        @batch_operation(batch_size=50)
        def process_items(items: List[int]) -> List[Result]:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(items: List[Any], *args, **kwargs) -> BatchResult:
            optimizer = get_query_optimizer()
            return optimizer.batch_execute(
                items,
                lambda item: func([item], *args, **kwargs)[0] if isinstance(func([item], *args, **kwargs), list) else func([item], *args, **kwargs),
                batch_size=batch_size
            )
        return wrapper
    return decorator
