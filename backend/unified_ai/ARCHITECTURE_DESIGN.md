# Unified AI Architecture Design Document (ADD)
# 统一AI架构设计文档

## 1. 概述

### 1.1 背景与问题

当前系统存在以下问题：
- **两套并行AI系统**：FHD Backend (`planner.py`, `user_input_parser.py`) 和 XCAGI (`neuro_domains/`) 各自分立
- **职责分散**：意图识别、槽位填充、产品匹配、合同校验等逻辑散落在多个模块
- **扩展性差**：每新增一个功能需要额外堆砌代码，无法统一调度
- **缺乏统一抽象**：没有标准的输入输出协议

### 1.2 设计目标

1. **统一编排**：所有AI能力通过单一入口调度
2. **分层处理**：Reflex (<1ms) → Cache (<10ms) → Rules (<50ms) → LLM (动态)
3. **注册机制**：新功能通过注册表注入，不修改核心代码
4. **标准协议**：统一的输入输出格式
5. **可观测**：每个环节记录 processing_mode 和耗时

### 1.3 核心价值

```
用户输入 ──▶ 统一编排器 ──▶ 智能路由 ──▶ 最佳处理器 ──▶ 结构化响应
                    │
                    ├── Reflex (预定义响应 <1ms)
                    ├── Cache (缓存命中 <10ms)
                    ├── Rules (规则匹配 <50ms)
                    └── LLM (深度理解 Tool Calling)
```

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           Unified AI System                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      Orchestrator (编排器)                         │   │
│  │                                                                   │   │
│  │   用户输入 ──▶ Intent Engine ──▶ Slot Filler ──▶ Tool Orch      │   │
│  │                        │              │              │             │   │
│  │                        ▼              ▼              ▼             │   │
│  │                   ┌─────────┐  ┌─────────┐  ┌─────────────┐      │   │
│  │                   │ Reflex  │  │ Rules   │  │ Tool Reg    │      │   │
│  │                   │ Cache   │  │ LLM     │  │             │      │   │
│  │                   └─────────┘  └─────────┘  └─────────────┘      │   │
│  │                                                                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    │                                     │
│                                    ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    Response Generator                             │   │
│  │              结构化数据 ──▶ 自然语言 / 多模态输出                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 核心组件

| 组件 | 职责 | 性能目标 |
|------|------|---------|
| **Orchestrator** | 统一入口，协调各组件 | <5ms overhead |
| **IntentEngine** | 意图识别，分层路由 | <100ms |
| **SlotFiller** | 槽位填充，实体提取 | <50ms |
| **ToolOrchestrator** | 工具编排与执行 | 动态 |
| **ResponseGenerator** | 响应生成 | <10ms |

### 2.3 数据流

```
1. 用户输入 (User Input)
       │
       ▼
2. IntentEngine.process()
   ├── ReflexArc: 预定义模式匹配 (<1ms)
   ├── CacheProcessor: 缓存查询 (<10ms)
   ├── RuleProcessor: 规则匹配 (<50ms)
   └── LLMProcessor: 深度理解 (Tool Calling)
       │
       ▼
3. IntentResult {intent, confidence, entities}
       │
       ▼
4. SlotFiller.fill()
   ├── 槽位验证
   ├── 缺失填充
   └── 歧义消解
       │
       ▼
5. FilledSlots {intent, slots, missing, ambiguous}
       │
       ▼
6. ToolOrchestrator.execute()
   ├── 工具选择
   ├── 参数绑定
   └── 执行调度
       │
       ▼
7. ToolResult {success, data, error}
       │
       ▼
8. ResponseGenerator.generate()
   └── 最终响应
```

---

## 3. 核心模块详细设计

### 3.1 Orchestrator (编排器)

**职责**：
- 提供统一入口 `process(user_message, context)`
- 协调 IntentEngine、SlotFiller、ToolOrchestrator
- 管理处理链路
- 统一错误处理和降级策略

**接口**：
```python
class UnifiedOrchestrator:
    async def process(
        user_message: str,
        context: dict | None = None,
        preferred_mode: str | None = None  # "fast", "accurate", "auto"
    ) -> ProcessingResult:
        """
        统一处理入口
        Returns: ProcessingResult {
            success: bool,
            intent: str,
            slots: dict,
            response: str,
            processing_mode: str,
            processing_time_ms: float,
            metadata: dict
        }
        """
```

### 3.2 IntentEngine (意图引擎)

**分层处理策略**：

```
用户输入
    │
    ├──▶ ReflexArc (<1ms)
    │    └─▶ 预定义模式匹配
    │        └─▶ 直接返回响应
    │
    ├──▶ CacheProcessor (<10ms)
    │    └─▶ L1/L2/L3 缓存
    │        └─▶ 命中则返回
    │
    ├──▶ RuleProcessor (<50ms)
    │    └─▶ 正则 + 关键词
    │        └─▶ 规则匹配
    │
    └──▶ LLMProcessor (动态)
         └─▶ DeepSeek/离线模型
             └─▶ Tool Calling
```

**IntentResult**：
```python
@dataclass
class IntentResult:
    intent: str                          # 意图名称
    confidence: float                    # 置信度 0.0-1.0
    entities: dict                       # 提取的实体
    processing_mode: str                  # 处理模式
    processing_time_ms: float            # 处理耗时
    fallback_available: bool             # 是否有降级方案
    metadata: dict                       # 附加信息
```

### 3.3 SlotFiller (槽位填充器)

**职责**：
- 验证意图所需的槽位是否完整
- 填充缺失槽位
- 消解歧义

**槽位定义示例**：
```python
INTENT_SLOTS = {
    "sales_contract": {
        "customer_name": {
            "type": "string",
            "required": True,
            "source": ["user_input", "context", "history"]
        },
        "products": {
            "type": "list[ProductItem]",
            "required": True,
            "entities": ["model_number", "quantity"]
        },
        "delivery_date": {
            "type": "date",
            "required": False
        }
    }
}
```

### 3.4 ToolOrchestrator (工具编排器)

**Tool Registry**：
```python
@dataclass
class ToolDefinition:
    name: str                            # 工具名称
    description: str                     # 工具描述
    input_schema: dict                   # 输入参数模式
    output_schema: dict                  # 输出结果模式
    handler: Callable                   # 处理函数
    required_intents: list[str]          # 适用的意图列表
    priority: int                        # 优先级
    timeout_ms: int                     # 超时时间
```

**内置工具**：
| 工具名 | 职责 | 对应现有模块 |
|--------|------|-------------|
| `contract_validate` | 合同校验 | contract_validator.py |
| `product_match` | 产品匹配 | product_semantic_matcher.py |
| `excel_analysis` | Excel分析 | tools.py |
| `template_fill` | 模板填充 | word_template.py |
| `customer_lookup` | 客户查询 | xcagi_compat.py |

---

## 4. 注册机制

### 4.1 Intent Registry (意图注册)

```python
# unified_ai/registry/intent_registry.py

INTENT_REGISTRY: dict[str, IntentDefinition] = {
    "sales_contract": IntentDefinition(
        name="sales_contract",
        description="生成销售合同",
        slots=["customer_name", "products"],
        default_response="正在为您生成销售合同...",
        tools=["contract_validate", "template_fill"]
    ),
    "product_query": IntentDefinition(...),
    "price_list_export": IntentDefinition(...),
    # 新增意图只需注册
}

def register_intent(intent_def: IntentDefinition):
    """注册新意图"""
    INTENT_REGISTRY[intent_def.name] = intent_def
```

### 4.2 Reflex Registry (反射弧注册)

```python
REFLEX_PATTERNS: dict[str, ReflexPattern] = {
    "greeting": ReflexPattern(
        regex=re.compile(r"^(hi|hello|你好|在吗)$", re.I),
        response="你好！有什么可以帮助你的？",
        priority=100
    ),
    "stop": ReflexPattern(
        regex=re.compile(r"^(stop|停止|cancel|取消)$", re.I),
        response="好的，已停止。",
        priority=100
    ),
    # 新增反射只需注册
}
```

### 4.3 Tool Registry (工具注册)

```python
# unified_ai/registry/tool_registry.py

TOOL_REGISTRY: dict[str, ToolDefinition] = {}

def register_tool(tool_def: ToolDefinition):
    """注册新工具"""
    TOOL_REGISTRY[tool_def.name] = tool_def

def get_tool(name: str) -> ToolDefinition | None:
    return TOOL_REGISTRY.get(name)

def get_tools_for_intent(intent: str) -> list[ToolDefinition]:
    """获取适用于某意图的所有工具"""
    return [t for t in TOOL_REGISTRY.values()
            if intent in t.required_intents]
```

---

## 5. 扩展机制

### 5.1 新增意图

```python
# 1. 在 intent_registry.py 注册
INTENT_REGISTRY["inventory_alert"] = IntentDefinition(
    name="inventory_alert",
    description="库存预警查询",
    slots=["product_model", "threshold"],
    tools=["inventory_check"]
)

# 2. 在 tool_registry.py 注册工具
register_tool(ToolDefinition(
    name="inventory_check",
    handler=inventory_check_handler,
    required_intents=["inventory_alert"]
))

# 3. 实现 handler
async def inventory_check_handler(product_model: str, threshold: int):
    # 业务逻辑
    return {"alert": True, "current_stock": 5}
```

### 5.2 新增反射

```python
REFLEX_PATTERNS["thank_you"] = ReflexPattern(
    regex=re.compile(r"^(谢谢|感谢|thanks)$", re.I),
    response="不客气！还有其他问题吗？",
    priority=50
)
```

---

## 6. 目录结构

```
backend/unified_ai/
├── __init__.py                      # 统一导出
│
├── core/                            # 核心引擎
│   ├── __init__.py
│   ├── orchestrator.py              # 统一编排器
│   ├── intent_engine.py              # 意图引擎
│   ├── slot_filler.py                # 槽位填充器
│   ├── tool_orchestrator.py          # 工具编排器
│   └── response_generator.py         # 响应生成器
│
├── registry/                        # 注册表
│   ├── __init__.py
│   ├── intent_registry.py            # 意图注册
│   ├── reflex_registry.py            # 反射弧注册
│   ├── tool_registry.py              # 工具注册
│   └── slot_registry.py              # 槽位定义注册
│
├── processors/                      # 处理器
│   ├── __init__.py
│   ├── reflex_processor.py           # 反射弧处理器
│   ├── cache_processor.py            # 缓存处理器
│   ├── rule_processor.py             # 规则处理器
│   └── llm_processor.py              # LLM处理器
│
├── tools/                           # 工具实现
│   ├── __init__.py
│   ├── base_tool.py                  # 工具基类
│   ├── contract_tool.py              # 合同工具
│   ├── product_tool.py               # 产品工具
│   └── excel_tool.py                 # Excel工具
│
├── utils/                           # 工具类
│   ├── __init__.py
│   ├── llm_client.py                 # LLM客户端
│   ├── cache.py                      # 缓存管理
│   ├── metrics.py                    # 指标收集
│   └── config.py                     # 配置管理
│
└── migrations/                       # 迁移脚本
    ├── __init__.py
    └── from_legacy.py                # 从旧架构迁移
```

---

## 7. 迁移策略

### 7.1 增量迁移（推荐）

```
Phase 1: 建立核心
├── 创建 unified_ai/core/ 基础结构
├── 实现 UnifiedOrchestrator
├── 实现 IntentEngine (Reflex + Cache + Rules)
└── 保持现有代码兼容

Phase 2: 迁移功能
├── 迁移 user_input_parser.py → IntentEngine + SlotFiller
├── 迁移 planner.py → ToolOrchestrator
├── 迁移 contract_validator.py → tools/contract_tool.py
└── 迁移 product_semantic_matcher.py → tools/product_tool.py

Phase 3: 切换入口
├── 修改 http_app.py 使用 UnifiedOrchestrator
├── 修改 xcagi_compat.py 使用 UnifiedOrchestrator
└── 逐步废弃旧模块

Phase 4: 清理
├── 删除旧模块（确认无引用后）
└── 优化目录结构
```

### 7.2 兼容模式

```python
# 迁移期间保持双轨运行
class UnifiedOrchestrator:
    def __init__(self):
        self._legacy_mode = True  # 兼容旧代码

    async def process(self, user_message, context=None):
        if self._legacy_mode:
            # 调用旧逻辑
            return await self._legacy_process(user_message, context)
        else:
            # 新逻辑
            return await self._new_process(user_message, context)
```

---

## 8. 接口规范

### 8.1 输入格式

```python
@dataclass
class ProcessInput:
    user_message: str                 # 用户消息
    session_id: str | None = None     # 会话ID
    user_id: str | None = None        # 用户ID
    context: dict | None = None       # 上下文
    preferred_mode: str | None = None # 偏好模式
    language: str = "zh"              # 语言
```

### 8.2 输出格式

```python
@dataclass
class ProcessingResult:
    success: bool                     # 是否成功
    intent: str | None = None         # 识别的意图
    confidence: float = 0.0           # 置信度
    slots: dict | None = None         # 填充的槽位
    missing_slots: list[str] = []     # 缺失槽位
    response: str = ""                # 自然语言响应
    data: dict | None = None          # 结构化数据
    processing_mode: str = "unknown"  # 处理模式
    processing_time_ms: float = 0.0  # 处理耗时
    error: str | None = None         # 错误信息
    metadata: dict = field(default_factory=dict)
```

---

## 9. 配置项

```python
# unified_ai/utils/config.py

class AIConfig:
    # 性能配置
    REFLEX_TIMEOUT_MS = 1
    CACHE_TIMEOUT_MS = 10
    RULE_TIMEOUT_MS = 50
    LLM_TIMEOUT_MS = 10000

    # 降级配置
    ENABLE_REFLEX = True
    ENABLE_CACHE = True
    ENABLE_RULES = True
    ENABLE_LLM = True
    FALLBACK_ON_ERROR = True

    # LLM配置
    DEFAULT_LLM = "deepseek"
    FALLBACK_LLM = "offline"

    # 缓存配置
    CACHE_SIZE = 1000
    CACHE_TTL_SECONDS = 300

    # 日志配置
    LOG_LEVEL = "INFO"
    LOG_PROCESSING_DETAILS = True
```

---

## 10. 监控与可观测性

### 10.1 处理链路日志

```python
logger.info(
    "processing链路",
    extra={
        "session_id": session_id,
        "input_length": len(user_message),
        "intent": result.intent,
        "mode": result.processing_mode,
        "time_ms": result.processing_time_ms,
        "slots_filled": len(result.slots or {}),
        "slots_missing": result.missing_slots
    }
)
```

### 10.2 性能指标

```python
metrics = {
    "intent_engine.total": counter,
    "intent_engine.reflex.hit": counter,
    "intent_engine.cache.hit": counter,
    "intent_engine.llm.calls": counter,
    "slot_filler.success": counter,
    "slot_filler.missing_slots": histogram,
    "tool_orchestrator.duration": histogram,
}
```

---

## 11. 风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| 迁移期间功能回退 | 高 | 保持双轨运行，灰度切换 |
| LLM 调用失败 | 中 | 降级到规则匹配 |
| 性能下降 | 中 | 分层处理，快速路径优先 |
| 缓存不一致 | 低 | TTL + 主动失效 |
| 新功能引入bug | 中 | 充分测试 + 回滚机制 |

---

## 12. 未来演进

### 12.1 v2.0 规划

- 支持多轮对话上下文
- 支持主动推荐和提示
- 支持个性化学习（用户习惯）

### 12.2 v3.0 规划

- 支持多模态输入（语音、图像）
- 支持分布式部署
- 支持模型自动选择

---

## 13. 附录

### 13.1 术语表

| 术语 | 定义 |
|------|------|
| Intent | 意图，用户想要完成的操作 |
| Slot | 槽位，意图所需的参数 |
| Reflex | 反射，预定义快速响应 |
| Fallback | 降级，当高级策略失败时使用低级策略 |
| Tool Calling | 工具调用，LLM触发外部函数 |

### 13.2 参考资料

- LangChain Agents
- LangGraph
- Rasa NLU
- OpenAI Function Calling

---

*文档版本: 1.0*
*最后更新: 2026-04-12*
