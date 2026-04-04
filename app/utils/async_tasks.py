# -*- coding: utf-8 -*-
"""
异步任务工具模块

提供高性能异步处理能力：
- Celery 任务封装
- 任务结果缓存
- 异步任务装饰器
- 任务队列管理
- 重试和错误处理
- 进度追踪
"""

import functools
import logging
import os
import time
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar('T')

DEFAULT_TASK_TIMEOUT = int(os.environ.get("XCAGI_TASK_DEFAULT_TIMEOUT", "300"))
MAX_RETRIES = int(os.environ.get("XCAGI_TASK_MAX_RETRIES", "3"))
RETRY_DELAY = int(os.environ.get("XCAGI_TASK_RETRY_DELAY", "5"))


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"
    RETRYING = "retrying"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    status: TaskStatus
    result: Optional[Any] = None
    error: Optional[str] = None
    progress: int = 0
    total: Optional[int] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    retries: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_ms(self) -> float:
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at) * 1000
        return 0.0

    @property
    def is_success(self) -> bool:
        return self.status == TaskStatus.SUCCESS

    @property
    def is_failed(self) -> bool:
        return self.status in (TaskStatus.FAILURE, TaskStatus.TIMEOUT)


@dataclass
class AsyncTaskConfig:
    """异步任务配置"""
    name: str
    queue: str = "normal"
    timeout: int = DEFAULT_TASK_TIMEOUT
    max_retries: int = MAX_RETRIES
    retry_delay: int = RETRY_DELAY
    soft_time_limit: int = 240
    priority: int = 5
    cache_result: bool = True
    cache_ttl: int = 3600
    on_success: Optional[Callable] = None
    on_failure: Optional[Callable] = None
    on_progress: Optional[Callable[[int, int], None]] = None


class AsyncTaskManager:
    """
    异步任务管理器

    功能：
    - 统一的任务提交接口
    - 任务状态追踪
    - 结果缓存
    - 重试机制
    - 超时控制
    """

    def __init__(self):
        self._tasks: Dict[str, TaskResult] = {}
        self._task_configs: Dict[str, AsyncTaskConfig] = {}
        self._progress_callbacks: Dict[str, Callable] = {}

    def register_task(self, config: AsyncTaskConfig) -> None:
        """注册任务配置"""
        self._task_configs[config.name] = config
        logger.info(f"已注册异步任务: {config.name}")

    def submit(
        self,
        task_name: str,
        args: tuple = (),
        kwargs: dict = None,
        task_id: Optional[str] = None,
        sync: bool = False,
        **extra_config
    ) -> TaskResult:
        """
        提交异步任务

        Args:
            task_name: 已注册的任务名称
            args: 位置参数
            kwargs: 关键字参数
            task_id: 自定义任务ID
            sync: 是否同步执行（用于调试）
            **extra_config: 额外配置覆盖

        Returns:
            TaskResult 任务结果对象
        """
        import uuid

        task_id = task_id or str(uuid.uuid4())[:12]
        kwargs = kwargs or {}

        config = self._get_task_config(task_name, extra_config)
        result = TaskResult(
            task_id=task_id,
            status=TaskStatus.PENDING,
            total=None,
            metadata={"task_name": task_name}
        )

        self._tasks[task_id] = result

        if sync:
            return self._execute_sync(task_name, args, kwargs, result, config)
        else:
            return self._execute_async(task_name, args, kwargs, result, config)

    def _get_task_config(self, task_name: str, overrides: dict) -> AsyncTaskConfig:
        """获取任务配置（支持覆盖）"""
        base_config = self._task_configs.get(task_name, AsyncTaskConfig(name=task_name))

        if overrides:
            config_dict = {**base_config.__dict__, **overrides}
            return AsyncTaskConfig(**{k: v for k, v in config_dict.items() if k in AsyncTaskConfig.__dataclass_fields__})

        return base_config

    def _execute_sync(
        self,
        task_name: str,
        args: tuple,
        kwargs: dict,
        result: TaskResult,
        config: AsyncTaskConfig
    ) -> TaskResult:
        """同步执行任务（用于测试/调试）"""
        logger.info(f"[同步执行] 任务 {task_name} (ID: {result.task_id})")
        result.status = TaskStatus.RUNNING
        result.started_at = time.time()

        try:
            from app.tasks import get_task_function
            func = get_task_function(task_name)

            output = func(*args, **kwargs)

            result.status = TaskStatus.SUCCESS
            result.result = output
            result.progress = 100
            result.completed_at = time.time()

            if config.on_success:
                config.on_success(result)

            logger.info(f"[同步完成] 任务 {task_id}: {result.duration_ms:.2f}ms")

        except Exception as e:
            result.status = TaskStatus.FAILURE
            result.error = str(e)
            result.completed_at = time.time()
            logger.error(f"[同步失败] 任务 {task_name}: {e}")

            if config.on_failure:
                config.on_failure(result)

        return result

    def _execute_async(
        self,
        task_name: str,
        args: tuple,
        kwargs: dict,
        result: TaskResult,
        config: AsyncTaskConfig
    ) -> TaskResult:
        """异步执行任务（通过 Celery）"""
        from app.extensions import celery_app

        if not hasattr(celery_app, 'send_task') or isinstance(celery_app.__class__.__name__, str) and 'Dummy' in celery_app.__class__.__name__:
            logger.warning("Celery 不可用，回退到同步执行")
            return self._execute_sync(task_name, args, kwargs, result, config)

        logger.info(f"[异步提交] 任务 {task_name} → 队列: {config.queue}")

        try:
            celery_result = celery_app.send_task(
                f"app.tasks.{task_name}",
                args=args,
                kwargs={
                    **kwargs,
                    "_xcagi_task_id": result.task_id,
                },
                queue=config.queue,
                soft_time_limit=config.soft_time_limit,
                time_limit=config.timeout,
                retries=config.max_retries,
            )

            result.metadata["celery_task_id"] = celery_result.id
            result.metadata["queue"] = config.queue

            logger.info(f"任务已提交: {result.task_id} (Celery ID: {celery_result.id})")

        except Exception as e:
            logger.error(f"任务提交失败 [{task_name}]: {e}")
            result.status = TaskStatus.FAILURE
            result.error = f"任务提交失败: {str(e)}"

        return result

    def get_status(self, task_id: str) -> Optional[TaskResult]:
        """获取任务状态"""
        return self._tasks.get(task_id)

    def get_result(self, task_id: str, timeout: Optional[int] = None) -> Optional[Any]:
        """
        获取任务结果（阻塞等待）

        Args:
            task_id: 任务ID
            timeout: 最大等待时间（秒），None 为非阻塞

        Returns:
            任务结果或 None
        """
        result = self._tasks.get(task_id)
        if not result:
            return None

        if result.is_success:
            return result.result

        if result.is_failed:
            raise Exception(result.error or "任务执行失败")

        if timeout and result.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
            start = time.time()
            while time.time() - start < timeout:
                time.sleep(0.1)
                result = self._tasks.get(task_id)
                if result and result.status in (TaskStatus.SUCCESS, TaskStatus.FAILURE):
                    break

        return result.result if result and result.is_success else None

    def update_progress(self, task_id: str, current: int, total: Optional[int] = None) -> None:
        """更新任务进度"""
        result = self._tasks.get(task_id)
        if result:
            result.progress = current
            if total is not None:
                result.total = total

            callback = self._progress_callbacks.get(task_id)
            if callback:
                try:
                    callback(current, total or 100)
                except Exception as e:
                    logger.warning(f"进度回调失败: {e}")

    def cancel(self, task_id: str) -> bool:
        """取消任务"""
        result = self._tasks.get(task_id)
        if result and result.status in (TaskStatus.PENDING, TaskStatus.RUNNING):
            result.status = TaskStatus.CANCELLED
            result.completed_at = time.time()
            return True
        return False

    def cleanup(self, max_age_seconds: int = 3600) -> int:
        """清理旧任务记录"""
        cutoff = time.time() - max_age_seconds
        old_keys = [
            tid for tid, t in self._tasks.items()
            if t.completed_at and t.completed_at < cutoff
        ]

        for key in old_keys:
            del self._tasks[key]
            self._progress_callbacks.pop(key, None)

        cleaned = len(old_keys)
        if cleaned > 0:
            logger.info(f"清理了 {cleaned} 个旧任务记录")
        return cleaned

    @property
    def active_tasks(self) -> Dict[str, TaskResult]:
        """获取活跃任务"""
        return {
            tid: t for tid, t in self._tasks.items()
            if t.status in (TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.RETRYING)
        }

    @property
    def stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        status_counts = {}
        for t in self._tasks.values():
            status_counts[t.status.value] = status_counts.get(t.status.value, 0) + 1

        return {
            "total_tasks": len(self._tasks),
            "active_tasks": len(self.active_tasks),
            "registered_tasks": list(self._task_configs.keys()),
            "status_distribution": status_counts,
        }


def async_task(
    name: str,
    queue: str = "normal",
    timeout: int = DEFAULT_TASK_TIMEOUT,
    cache_result: bool = True,
    cache_ttl: int = 3600,
    **kwargs
):
    """
    异步任务装饰器

    用法：
        @async_task(
            name="generate_report",
            queue="heavy",
            timeout=600,
            cache_result=True,
            cache_ttl=1800
        )
        def generate_monthly_report(month: str, year: int):
            ...

        # 调用方式：
        # 同步调用：result = generate_monthly_report("01", 2026)
        # 异步调用：task = generate_monthry_report.async_submit("01", 2026)
    """
    def decorator(func: Callable) -> Callable:
        config = AsyncTaskConfig(
            name=name,
            queue=queue,
            timeout=timeout,
            cache_result=cache_result,
            cache_ttl=cache_ttl,
            **kwargs
        )

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            manager = get_async_task_manager()

            sync_mode = kwargs.pop('_sync', False) or os.environ.get('XCAGI_FORCE_SYNC_TASKS', '0') == '1'

            if sync_mode:
                return manager.submit(config.name, args, kwargs, sync=True).result

            task_result = manager.submit(config.name, args, kwargs)

            if task_result.is_success:
                return task_result.result

            if task_result.is_failed:
                raise Exception(task_result.error)

            return {"task_id": task_result.task_id, "status": task_result.status.value}

        def async_submit(*a, **kw) -> TaskResult:
            manager = get_async_task_manager()
            return manager.submit(config.name, a, kw)

        def get_task_status(task_id: str) -> Optional[TaskResult]:
            manager = get_async_task_manager()
            return manager.get_status(task_id)

        wrapper.async_submit = staticmethod(async_submit)
        wrapper.get_task_status = staticmethod(get_task_status)
        wrapper.config = config

        return wrapper
    return decorator


def background_task(
    name: Optional[str] = None,
    queue: str = "background",
    max_retries: int = MAX_RETRIES
):
    """
    后台任务装饰器（简化版）

    自动在后台执行，不等待结果
    """
    def decorator(func: Callable) -> Callable:
        task_name = name or f"bg_{func.__name__}"

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                from app.extensions import celery_app

                if hasattr(celery_app, 'send_task'):
                    celery_app.send_task(
                        f'app.tasks.{task_name}',
                        args=args,
                        kwargs=kwargs,
                        queue=queue,
                        retries=max_retries,
                    )
                    return {"status": "submitted", "task_name": task_name}

                logger.warning("Celery 不可用，同步执行后台任务")
                import threading
                t = threading.Thread(target=func, args=args, kwargs=kwargs, daemon=True)
                t.start()
                return {"status": "threaded", "task_name": task_name}

            except Exception as e:
                logger.error(f"后台任务提交失败 [{task_name}]: {e}")
                raise

        return wrapper
    return decorator


def retry_on_failure(
    max_retries: int = MAX_RETRIES,
    delay: int = RETRY_DELAY,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    重试装饰器

    用法：
        @retry_on_failure(max_retries=3, delay=2, exceptions=(ConnectionError, TimeoutError))
        def unreliable_operation():
            ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"重试 [{func.__name__}] 第 {attempt + 1}/{max_retries} 次 "
                            f"(等待 {current_delay}s): {e}"
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(f"重试耗尽 [{func.__name__}]: {e}")

            raise last_exception
        return wrapper
    return decorator


_async_task_manager: Optional[AsyncTaskManager] = None


def get_async_task_manager() -> AsyncTaskManager:
    """获取异步任务管理器单例"""
    global _async_task_manager
    if _async_task_manager is None:
        _async_task_manager = AsyncTaskManager()
        _register_default_tasks(_async_task_manager)
    return _async_task_manager


def _register_default_tasks(manager: AsyncTaskManager) -> None:
    """注册默认任务配置"""
    default_tasks = [
        AsyncTaskConfig(name="shipment_tasks.generate_shipment_order", queue="urgent", timeout=120),
        AsyncTaskConfig(name="shipment_tasks.export_shipment_records_task", queue="normal", timeout=300),
        AsyncTaskConfig(name="shipment_tasks.import_products_batch_task", queue="normal", timeout=600),
        AsyncTaskConfig(name="wechat_tasks.scan_wechat_messages", queue="wechat", timeout=60),
        AsyncTaskConfig(name="kitten_report.generate_report", queue="heavy", timeout=900),
    ]

    for config in default_tasks:
        manager.register_task(config)
