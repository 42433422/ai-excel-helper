"""
import logging

logger = logging.getLogger(__name__)
路由层事件发布工具

为 FastAPI 路由提供便捷的 Neuro 事件发布功能。
自动追踪请求生命周期并发布相关事件。
"""

from __future__ import annotations

import functools
import time
import uuid
from collections.abc import Callable
from typing import Any, TypeVar

from fastapi import Request

from app.neuro_bus.application_neuro_bridge import publish_neuro_event
from app.neuro_bus.integrations.intent_integration import is_neuro_stack_enabled

F = TypeVar("F", bound=Callable[..., Any])


def publish_route_event(
    event_type: str,
    domain: str = "api",
    include_payload: bool = True,
    payload_extractor: Callable[..., dict[str, Any]] | None = None,
) -> Callable[[F], F]:
    """
    路由事件发布装饰器

    为 FastAPI 路由函数自动添加 Neuro 事件发布。

    Args:
        event_type: 事件类型（如 "chat.request", "tool.executed"）
        domain: 领域名称
        include_payload: 是否包含请求/响应数据
        payload_extractor: 自定义 payload 提取函数

    Example:
        @router.post("/ai/chat")
        @publish_route_event("chat.request", domain="ai")
        async def ai_chat(request: Request, body: ChatBody):
            return await process_chat(body)
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            # 提取 request 对象
            request: Request | None = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request = kwargs.get("request")

            # 生成追踪 ID
            trace_id = str(uuid.uuid4())
            start_time = time.perf_counter()

            # 构建 payload
            payload: dict[str, Any] = {
                "trace_id": trace_id,
                "route": func.__name__,
                "timestamp": time.time(),
            }

            if request:
                payload.update(
                    {
                        "method": request.method,
                        "path": str(request.url.path),
                        "client": request.client.host if request.client else None,
                    }
                )

            # 自定义提取
            if payload_extractor:
                try:
                    custom = payload_extractor(*args, **kwargs)
                    if custom:
                        payload.update(custom)
                except Exception:
                    logger.debug("suppressed exception", exc_info=True)

            # 发布开始事件
            if is_neuro_stack_enabled():
                publish_neuro_event(
                    f"{event_type}.started",
                    payload,
                    domain=domain,
                )

            try:
                # 执行路由函数
                result = await func(*args, **kwargs)

                # 计算延迟
                latency_ms = (time.perf_counter() - start_time) * 1000

                # 发布成功事件
                success_payload = {
                    **payload,
                    "latency_ms": round(latency_ms, 3),
                    "success": True,
                }

                if include_payload and isinstance(result, dict):
                    # 只包含关键字段，避免数据过大
                    success_payload["result_keys"] = list(result.keys())
                    if "error" in result:
                        success_payload["has_error"] = True

                if is_neuro_stack_enabled():
                    publish_neuro_event(
                        f"{event_type}.completed",
                        success_payload,
                        domain=domain,
                    )

                return result

            except Exception as e:
                # 发布失败事件
                latency_ms = (time.perf_counter() - start_time) * 1000

                error_payload = {
                    **payload,
                    "latency_ms": round(latency_ms, 3),
                    "success": False,
                    "error_type": type(e).__name__,
                    "error_message": str(e)[:200],
                }

                if is_neuro_stack_enabled():
                    publish_neuro_event(
                        f"{event_type}.failed",
                        error_payload,
                        domain=domain,
                    )

                raise

        # 同步版本处理
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            request: Request | None = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request:
                request = kwargs.get("request")

            trace_id = str(uuid.uuid4())
            start_time = time.perf_counter()

            payload: dict[str, Any] = {
                "trace_id": trace_id,
                "route": func.__name__,
                "timestamp": time.time(),
            }

            if request:
                payload.update(
                    {
                        "method": request.method,
                        "path": str(request.url.path),
                        "client": request.client.host if request.client else None,
                    }
                )

            if is_neuro_stack_enabled():
                publish_neuro_event(
                    f"{event_type}.started",
                    payload,
                    domain=domain,
                )

            try:
                result = func(*args, **kwargs)

                latency_ms = (time.perf_counter() - start_time) * 1000

                success_payload = {
                    **payload,
                    "latency_ms": round(latency_ms, 3),
                    "success": True,
                }

                if is_neuro_stack_enabled():
                    publish_neuro_event(
                        f"{event_type}.completed",
                        success_payload,
                        domain=domain,
                    )

                return result

            except Exception as e:
                latency_ms = (time.perf_counter() - start_time) * 1000

                error_payload = {
                    **payload,
                    "latency_ms": round(latency_ms, 3),
                    "success": False,
                    "error_type": type(e).__name__,
                    "error_message": str(e)[:200],
                }

                if is_neuro_stack_enabled():
                    publish_neuro_event(
                        f"{event_type}.failed",
                        error_payload,
                        domain=domain,
                    )

                raise

        # 根据函数类型返回适当的包装器
        import asyncio

        wrapper = async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

        # 预解析 func 的类型注解，避免 ``from __future__ import annotations`` 场景下
        # FastAPI 使用 wrapper 的 ``__globals__`` 解析字符串注解失败（会把 BaseModel
        # 参数退化为 Query，进而在 OpenAPI 生成时抛 PydanticUserError）。
        #
        # 注意：FastAPI 内部 ``inspect.signature(wrapper)`` 会跟随
        # ``functools.wraps`` 设置的 ``__wrapped__`` 回到原函数读取注解，因此
        # 这里同时把 resolved hints 写回原函数，保证两边一致。
        try:
            import typing

            resolved = typing.get_type_hints(func, include_extras=True)
            wrapper.__annotations__ = resolved
            try:
                func.__annotations__ = resolved
            except (AttributeError, TypeError):
                pass
        except Exception:
            logger.debug("suppressed exception", exc_info=True)

        return wrapper  # type: ignore[return-value]

    return decorator


def publish_simple_event(
    event_type: str,
    payload: dict[str, Any],
    domain: str = "api",
) -> bool:
    """
    简单的事件发布函数

    用于在路由内部手动发布事件。

    Args:
        event_type: 事件类型
        payload: 事件数据
        domain: 领域名称

    Returns:
        是否发布成功
    """
    if not is_neuro_stack_enabled():
        return False

    try:
        return publish_neuro_event(event_type, payload, domain=domain)
    except Exception:
        return False


# 预定义的领域事件类型
class RouteEvents:
    """常用路由事件类型"""

    CHAT_REQUEST = "chat.request"
    CHAT_STREAM = "chat.stream"
    CHAT_BATCH = "chat.batch"

    TOOL_EXECUTE = "tool.execute"
    TOOL_BATCH = "tool.batch"

    FILE_UPLOAD = "file.upload"
    FILE_DOWNLOAD = "file.download"
    FILE_DELETE = "file.delete"

    CONVERSATION_CREATE = "conversation.create"
    CONVERSATION_MESSAGE = "conversation.message"
    CONVERSATION_DELETE = "conversation.delete"

    DB_QUERY = "db.query"
    DB_EXPORT = "db.export"
    DB_IMPORT = "db.import"

    CONFIG_GET = "config.get"
    CONFIG_SET = "config.set"

    HEALTH_CHECK = "health.check"
    METRICS_GET = "metrics.get"
