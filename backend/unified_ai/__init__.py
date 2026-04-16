"""
Unified AI - 统一AI架构

使用示例:
    from backend.unified_ai import UnifiedOrchestrator, get_orchestrator

    orchestrator = get_orchestrator()
    result = await orchestrator.process("打印销售合同，客户是XXX")

    # 或者直接调用
    result = await orchestrator.process(
        user_message="查询产品3721",
        context={"preferred_mode": "fast"}
    )
"""

from .core import (
    UnifiedOrchestrator,
    get_orchestrator,
    ProcessingResult,
    IntentEngine,
    get_intent_engine,
    IntentResult,
    SlotFiller,
    get_slot_filler,
)

from .registry import (
    INTENT_REGISTRY,
    IntentDefinition,
    register_intent,
    get_intent,
    REFLEX_PATTERNS,
    ReflexPattern,
    register_reflex,
    match_reflex,
    TOOL_REGISTRY,
    ToolDefinition,
    register_tool,
    get_tool,
    get_tools_for_intent,
    list_tools,
    register_builtin_tools,
    register_workflow_tools,
    initialize_tools,
    ensure_tools_initialized,
)

from .processors import (
    ReflexProcessor,
    CacheProcessor,
    RuleProcessor,
    LLMProcessor,
)

from .tools import (
    BaseTool,
    ToolResult,
    ContractTool,
    ProductTool,
)

from .utils import (
    AIConfig,
    get_config,
    AICache,
    get_cache,
    MetricsCollector,
    get_metrics,
)

from .migrations import (
    migrate_user_input_parser,
    migrate_planner_chat,
    create_unified_wrapper,
    LegacyAdapter,
)

__version__ = "1.0.0"

__all__ = [
    # 核心
    "UnifiedOrchestrator",
    "get_orchestrator",
    "ProcessingResult",
    "IntentEngine",
    "get_intent_engine",
    "IntentResult",
    "SlotFiller",
    "get_slot_filler",
    # 注册表
    "INTENT_REGISTRY",
    "IntentDefinition",
    "register_intent",
    "get_intent",
    "REFLEX_PATTERNS",
    "ReflexPattern",
    "register_reflex",
    "match_reflex",
    "TOOL_REGISTRY",
    "ToolDefinition",
    "register_tool",
    "get_tool",
    "get_tools_for_intent",
    # 处理器
    "ReflexProcessor",
    "CacheProcessor",
    "RuleProcessor",
    "LLMProcessor",
    # 工具
    "BaseTool",
    "ToolResult",
    "ContractTool",
    "ProductTool",
    # 工具类
    "AIConfig",
    "get_config",
    "AICache",
    "get_cache",
    "MetricsCollector",
    "get_metrics",
    # 迁移
    "migrate_user_input_parser",
    "migrate_planner_chat",
    "create_unified_wrapper",
    "LegacyAdapter",
    # 版本
    "__version__",
]
