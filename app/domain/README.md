# NeuroDDD 领域层

此目录包含 XCAGI 系统的领域模型，按照 NeuroDDD（神经领域驱动设计）架构组织。

NeuroDDD 是以神经系统为隐喻的领域驱动架构，核心组件包括：

## 目录结构

```
domain/
├── __init__.py
├── neuro/                    # NeuroDDD 核心组件
│   ├── reflex_arc.py         # 神经反射弧（<1ms SLA）
│   ├── reflex_patterns.py    # 反射模式匹配器
│   ├── neuro_uow.py          # 神经工作单元
│   └── processors/           # 三级处理器
│       ├── coordinator.py    # 处理器协调器（Reflex→Subconscious→Conscious）
│       ├── subconscious.py   # 潜意识处理器（<10ms）
│       └── conscious.py      # 显意识处理器（<200ms）
├── services/                 # 领域服务（无状态业务逻辑）
│   └── unified_intent_recognizer.py  # 统一意图识别器
├── ports/                    # 域通道接口（领域与基础设施的契约）
│   └── cache_port.py         # 缓存通道
└── value_objects/            # 值对象（不可变的领域概念）
    ├── money.py              # 金额
    ├── price.py              # 价格
    ├── quantity.py           # 数量
    ├── address.py            # 地址
    ├── phone.py              # 电话
    ├── email.py              # 邮箱
    ├── date_range.py         # 日期范围
    ├── percentage.py         # 百分比
    ├── order_number.py       # 订单号
    └── model_number.py       # 型号
```

## NeuroDDD 核心概念

### 神经反射弧 (IntentReflexArc)
- <1ms 响应保证的极速意图识别
- 预编译正则模式匹配
- 零分配执行路径 + 内存级缓存
- 覆盖：问候/否定/确认/帮助/紧急停止

### 三级处理器管道
1. **Reflex 级**（<1ms）：IntentReflexArc 处理简单意图
2. **Subconscious 级**（<10ms）：后台异步任务（日志、统计）
3. **Conscious 级**（<200ms）：核心业务逻辑（完整可靠性机制栈）

### 神经总线 (NeuroBus)
- 多优先级事件队列（5级）
- 领域隔离 + 同步/异步处理器
- 去重/限流/熔断/链路追踪

### 命令网关 (CommandGateway)
- 请求-回复模式的跨域通信
- 变更操作通过 NeuroBus 发布领域事件

## 设计原则

1. **事件驱动优先**：变更操作通过 NeuroBus 发布领域事件
2. **反射弧快速路径**：简单意图走 ReflexArc（<1ms），不经过 Conscious Processor
3. **领域隔离**：每个 NeuroDomain 有独立的处理器和事件通道
4. **可靠性机制栈**：去重、限流、熔断、链路追踪、Outbox 保证最终一致性
