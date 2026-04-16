"""
从旧架构迁移的工具
提供与旧架构的兼容接口
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def migrate_user_input_parser(user_message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    迁移旧版 user_input_parser 到统一架构

    旧代码:
        from backend.user_input_parser import extract_structured_info
        result = extract_structured_info(user_message)

    新代码:
        from backend.unified_ai import UnifiedOrchestrator
        orchestrator = get_orchestrator()
        result = await orchestrator.process(user_message)
    """
    try:
        from backend.user_input_parser import extract_structured_info
        return extract_structured_info(user_message, context)
    except Exception as e:
        logger.warning(f"[Migration] user_input_parser 迁移失败: {e}")
        return {
            "customer_name": None,
            "products": [],
            "quantities": {},
            "raw_message": user_message,
            "parsed": False,
            "migration_error": str(e)
        }


def migrate_planner_chat(user_message: str, runtime_context: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    迁移旧版 planner.chat 到统一架构
    """
    try:
        from backend.planner import chat as old_chat
        return old_chat(user_message, runtime_context=runtime_context)
    except Exception as e:
        logger.warning(f"[Migration] planner.chat 迁移失败: {e}")
        return {"error": str(e), "message": "聊天处理失败"}


def create_unified_wrapper():
    """
    创建统一包装器，兼容旧代码
    """
    from backend.unified_ai.core.orchestrator import UnifiedOrchestrator

    class UnifiedWrapper:
        def __init__(self):
            self._orchestrator = UnifiedOrchestrator()

        async def process(self, user_message: str, context: dict | None = None):
            return await self._orchestrator.process(user_message, context)

        def process_sync(self, user_message: str, context: dict | None = None):
            import asyncio
            return asyncio.run(self._orchestrator.process(user_message, context))

    return UnifiedWrapper()


class LegacyAdapter:
    """
    旧架构适配器 - 将旧版 API 适配到统一架构

    使用方式:
        adapter = LegacyAdapter()
        result = await adapter.chat("打印销售合同，客户是XXX")

        # 或者同步方式
        result = adapter.chat_sync("打印销售合同")
    """

    def __init__(self):
        from backend.unified_ai.core.orchestrator import get_orchestrator
        self._orchestrator = get_orchestrator()

    async def chat(self, user_message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """异步聊天接口"""
        result = await self._orchestrator.process(user_message, context)
        return {
            "success": result.success,
            "intent": result.intent,
            "confidence": result.confidence,
            "slots": result.slots,
            "response": result.response,
            "data": result.data,
            "processing_mode": result.processing_mode,
            "processing_time_ms": result.processing_time_ms,
            "error": result.error,
        }

    def chat_sync(self, user_message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """同步聊天接口"""
        import asyncio
        return asyncio.run(self.chat(user_message, context))

    def parse_input(self, user_message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """解析用户输入"""
        return migrate_user_input_parser(user_message, context)
