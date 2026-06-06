# XCAGI 架构设计文档

> Neuro-DDD（分层 + AI 用例编排）架构详解  
> 版本：7.0.0

---

## 📐 一、架构概览

### 1.1 架构演进

```
v1.0: 单文件脚本
    ↓
v2.0: 分层架构（MVC）
    ↓
v3.0: 领域驱动设计（DDD）
    ↓
v4.0: AI 员工定位 + 全自动流程
    ↓
v5.0: Neuro-DDD 架构 + 小程序
    ↓
v6.0: 商业模式明确 + Mod 生态
    ↓
v7.0: 桌面版 + Web 版并行交付
```

### 1.2 为什么选择 Neuro-DDD？

**v2.0 架构的问题**:
- ❌ 业务逻辑分散，难以维护
- ❌ 数据库耦合严重
- ❌ 难以测试
- ❌ 代码复用性差

**Neuro-DDD 架构的优势**:
- ✅ 清晰的职责划分（Domain / Application / Infrastructure）
- ✅ 业务逻辑集中在领域层
- ✅ 易于测试和维护
- ✅ 支持复杂业务场景
- ✅ AI 用例编排（NeuroBus 事件总线）
- ✅ 技术栈可替换

### 1.3 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                      表现层 (Presentation)                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Vue 3 SPA  │  │  REST API   │  │  WebSocket  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      应用层 (Application)                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  应用服务 (Application Services)                     │    │
│  │  - AIChatAppService                                 │    │
│  │  - ProductAppService                                │    │
│  │  - ShipmentAppService                               │    │
│  │  - WechatContactAppService                          │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  端口接口 (Ports)                                    │    │
│  │  - ProductRepository                                │    │
│  │  - ShipmentRepository                               │    │
│  │  - FileAnalysis                                     │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      领域层 (Domain)                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  领域实体 (Entities)                                 │    │
│  │  - Product                                          │    │
│  │  - ShipmentRecord                                   │    │
│  │  - WechatContact                                    │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  值对象 (Value Objects)                              │    │
│  │  - Money                                            │    │
│  │  - Quantity                                         │    │
│  │  - ProductSpec                                      │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  领域服务 (Domain Services)                          │    │
│  │  - PricingEngine                                    │    │
│  │  - ShipmentRulesEngine                              │    │
│  │  - UnifiedIntentRecognizer                          │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  聚合根 (Aggregates)                                 │    │
│  │  - ShipmentAggregate                                │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   基础设施层 (Infrastructure)                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  仓储实现 (Repositories)                             │    │
│  │  - ProductRepositoryImpl                            │    │
│  │  - ShipmentRepositoryImpl                           │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  技术组件                                            │    │
│  │  - Database (SQLAlchemy)                            │    │
│  │  - Cache (Redis)                                    │    │
│  │  - Message Queue (Celery)                           │    │
│  │  - AI Services (DeepSeek, BERT, RASA)               │    │
│  │  - OCR Services                                     │    │
│  │  - TTS Services                                     │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 1.4 v7.0 桌面版架构

v7.0 新增桌面交付形态，采用 Electron 壳 + 本地 FastAPI 子进程架构：

```
┌─────────────────────────────────────────────────────────────┐
│                    桌面版架构（Desktop）                       │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Electron 主进程 (desktop/)                          │   │
│  │  - 应用生命周期管理                                   │   │
│  │  - 自动更新服务                                       │   │
│  │  - 系统托盘/通知                                     │   │
│  └─────────────────┬───────────────────────────────────┘   │
│                    │ IPC                                    │
│  ┌─────────────────▼───────────────────────────────────┐   │
│  │  Electron 渲染进程 (frontend/)                        │   │
│  │  - Vue 3 SPA                                        │   │
│  │  - 本地 API 调用 (http://127.0.0.1:5000)            │   │
│  └─────────────────────────────────────────────────────┘   │
│                    │                                        │
│  ┌─────────────────▼───────────────────────────────────┐   │
│  │  FastAPI 子进程 (app/)                                │   │
│  │  - 本地 SQLite 数据库                                 │   │
│  │  - 本地文件队列                                       │   │
│  │  - 所有业务逻辑                                       │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                     Web 版架构（Web）                         │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Nginx 反向代理                                      │   │
│  └─────────────────┬───────────────────────────────────┘   │
│                    │                                        │
│  ┌─────────────────▼───────────────────────────────────┐   │
│  │  FastAPI 应用 (app/)                                  │   │
│  │  - PostgreSQL 数据库                                  │   │
│  │  - Redis 缓存                                        │   │
│  │  - Celery 异步任务                                    │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**桌面版特性**：
- 环境变量 `XCAGI_DESKTOP_MODE=1` 启用桌面运行时
- 使用 SQLite 替代 PostgreSQL
- 本地队列替代 Redis/Celery
- 自动更新支持
- 离线可用性

---

## 📁 二、目录结构

### 2.1 后端目录结构

```
app/
├── domain/                    # 领域层
│   ├── ai/                   # AI 领域
│   │   ├── __init__.py
│   │   └── tier.py           # AI 层级定义
│   ├── neuro/                # 神经域
│   │   └── __init__.py
│   ├── ports/                # 领域端口
│   │   └── __init__.py
│   ├── value_objects.py      # 值对象
│   └── README.md             # 领域层说明

├── application/              # 应用层
│   ├── README.md             # 应用层说明
│   └── __init__.py
│
├── infrastructure/           # 基础设施层
│   ├── README.md             # 基础设施层说明
│   ├── skills/               # AI 技能系统
│   │   ├── label_template_generator/
│   │   ├── excel_toolkit/
│   │   └── excel_analyzer/
│   ├── mods/                 # Mod 加载器
│   ├── payment/              # 支付实现
│   └── persistence/          # 持久化实现
│
├── fastapi_routes/           # FastAPI 路由（表现层）
│   ├── ai_assistant.py
│   ├── shipment_orders.py
│   ├── excel_extract.py
│   ├── miniprogram.py
│   ├── ocr.py
│   ├── print_routes.py
│   └── ...
│
├── routes/                   # 兼容路由（遗留）
│   ├── ai_chat.py
│   ├── wechat_miniprogram.py
│   └── ...
│
├── legacy/                   # 过渡期支持模块（待细拆）
│   ├── tools.py
│   ├── planner.py
│   ├── llm_config.py
│   └── ...
│
├── shell/                    # CLI 工具
│   ├── mods_catalog.py
│   ├── mods_schemas.py
│   └── mod_row_scope.py
│
├── neuro_bus/                # NeuroBus 事件总线
│   ├── bus.py
│   ├── events/
│   ├── domains/
│   └── ...
│
├── db/                       # 数据库模型（基础设施）
│   ├── models/               # ORM 模型
│   │   ├── user.py
│   │   ├── product.py
│   │   ├── shipment.py
│   │   ├── customer.py
│   │   └── ...
│   ├── base.py
│   ├── init_db.py
│   └── session.py
│
├── di/                       # 依赖注入
│   ├── registry.py           # 服务容器
│   └── fastapi_deps.py
│
├── services/                 # 领域服务
│   ├── auth_service.py
│   ├── ocr_service.py
│   ├── tts_service.py
│   ├── wechat_contact_service.py
│   └── ...
│
├── utils/                    # 工具函数
│   ├── logger.py
│   ├── cache_manager.py
│   ├── retry.py
│   └── ...
│
├── config.py                 # 配置管理
├── bootstrap.py              # 应用启动
├── fastapi_app.py            # FastAPI 应用工厂
└── extensions.py             # 扩展模块
```

### 2.2 前端目录结构

```
frontend/
├── src/
│   ├── api/                  # API 接口层
│   │   ├── products.ts
│   │   ├── shipment.ts
│   │   └── chat.ts
│   │
│   ├── components/           # UI 组件
│   │   ├── DataTable.vue
│   │   ├── Modal.vue
│   │   └── Sidebar.vue
│   │
│   ├── composables/          # Vue Composables
│   │   ├── useProducts.ts
│   │   ├── useApi.ts
│   │   └── useFileImport.ts
│   │
│   ├── stores/               # Pinia 状态管理
│   │   ├── products.ts
│   │   ├── shipment.ts
│   │   └── jarvisChat.ts
│   │
│   ├── views/                # 页面视图
│   │   ├── ProductsView.vue
│   │   ├── ShipmentRecordsView.vue
│   │   └── ChatView.vue
│   │
│   ├── router/               # 路由
│   │   └── index.js
│   │
│   ├── types/                # TypeScript 类型
│   │   ├── product.ts
│   │   └── order.ts
│   │
│   ├── utils/                # 工具函数
│   │   ├── index.ts
│   │   └── memory-manager.ts
│   │
│   ├── styles/               # 样式
│   │   ├── base.css
│   │   └── pro-mode.css
│   │
│   ├── App.vue
│   └── main.js
│
└── package.json
```

---

## 🏗️ 三、核心设计模式

### 3.1 仓储模式（Repository Pattern）

**目的**: 抽象数据访问逻辑，隔离领域层和基础设施层

**接口定义**:
```python
# app/application/ports/product_repository.py
from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.product.entities import Product

class ProductRepository(ABC):
    @abstractmethod
    def find_by_id(self, id: int) -> Optional[Product]:
        pass
    
    @abstractmethod
    def find_all(self) -> List[Product]:
        pass
    
    @abstractmethod
    def save(self, product: Product) -> Product:
        pass
    
    @abstractmethod
    def delete(self, id: int) -> bool:
        pass
```

**实现**:
```python
# app/infrastructure/repositories/product_repository_impl.py
from app.application.ports.product_repository import ProductRepository
from app.domain.product.entities import Product

class ProductRepositoryImpl(ProductRepository):
    def __init__(self, db_session):
        self.db = db_session
    
    def find_by_id(self, id: int) -> Optional[Product]:
        # 实现细节
        pass
    
    def find_all(self) -> List[Product]:
        # 实现细节
        pass
    
    def save(self, product: Product) -> Product:
        # 实现细节
        pass
    
    def delete(self, id: int) -> bool:
        # 实现细节
        pass
```

**使用**:
```python
# app/application/product_app_service.py
class ProductAppService:
    def __init__(self, product_repository: ProductRepository):
        self.product_repository = product_repository
    
    def get_product(self, id: int) -> Product:
        return self.product_repository.find_by_id(id)
```

### 3.2 领域事件（Domain Events）

**目的**: 解耦领域逻辑，支持事件驱动架构

```python
# app/domain/services/shipment_rules_engine.py
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ShipmentCreatedEvent:
    shipment_id: int
    purchase_unit: str
    products: list
    created_at: datetime
    user_id: str

class ShipmentRulesEngine:
    def __init__(self, event_bus):
        self.event_bus = event_bus
    
    def validate_shipment(self, shipment):
        # 验证逻辑
        if shipment.is_valid():
            event = ShipmentCreatedEvent(
                shipment_id=shipment.id,
                purchase_unit=shipment.purchase_unit,
                products=shipment.products,
                created_at=datetime.now(),
                user_id=shipment.user_id
            )
            self.event_bus.publish(event)
```

### 3.3 CQRS（命令查询职责分离）

**目的**: 分离读写操作，优化性能

```python
# 命令（写操作）
class CreateShipmentCommand:
    def __init__(self, purchase_unit: str, products: list):
        self.purchase_unit = purchase_unit
        self.products = products

class ShipmentCommandHandler:
    def handle(self, command: CreateShipmentCommand):
        # 写操作，使用领域模型
        shipment = Shipment.create(
            purchase_unit=command.purchase_unit,
            products=command.products
        )
        return shipment

# 查询（读操作）
class ShipmentQuery:
    def __init__(self, filters: dict):
        self.filters = filters

class ShipmentQueryHandler:
    def handle(self, query: ShipmentQuery):
        # 读操作，直接使用数据库查询
        return self.db.query(ShipmentRecord).filter(
            **query.filters
        ).all()
```

---

## 🔄 四、数据流

### 4.1 典型请求流程

```
用户请求 → API 路由 → 应用服务 → 领域服务 → 仓储 → 数据库
                ↓
            返回 DTO
```

**详细流程**:

1. **请求接收** (routes/products.py)
```python
@routes.post('/api/products')
def create_product(request: ProductCreateRequest):
    # 1. 接收并验证请求
    product_service = ProductAppService()
    return product_service.create_product(request)
```

2. **应用服务处理** (application/product_app_service.py)
```python
class ProductAppService:
    def create_product(self, request: ProductCreateRequest):
        # 2. 创建领域实体
        product = Product.create(
            name=request.name,
            model_number=request.model_number,
            price=request.price
        )
        
        # 3. 保存到仓储
        saved_product = self.product_repository.save(product)
        
        # 4. 返回 DTO
        return ProductDTO.from_entity(saved_product)
```

3. **领域逻辑** (domain/product/entities.py)
```python
class Product:
    @classmethod
    def create(cls, name: str, model_number: str, price: float):
        # 领域逻辑验证
        if price < 0:
            raise ValueError("价格不能为负")
        
        return cls(
            name=name,
            model_number=model_number,
            price=price
        )
```

4. **数据持久化** (infrastructure/repositories/product_repository_impl.py)
```python
def save(self, product: Product) -> Product:
    # 转换为数据库模型
    db_model = ProductDBModel(
        name=product.name,
        model_number=product.model_number,
        price=product.price
    )
    self.db.add(db_model)
    self.db.commit()
    
    # 转换回领域模型
    return Product.from_db(db_model)
```

### 4.2 领域事件流程

```
领域服务 → 发布事件 → 事件总线 → 订阅者处理
                              ↓
                         - 发送邮件
                         - 更新缓存
                         - 记录日志
```

---

## 🎯 五、关键设计决策

### 5.1 为什么使用多数据库文件？

**决策**: 使用多个 SQLite 数据库文件（products.db, customers.db, users.db）

**理由**:
- ✅ 职责分离，每个数据库负责特定领域
- ✅ 备份和恢复更简单
- ✅ 性能优化，减少单文件锁竞争
- ✅ 安全隔离，敏感数据独立存储

**权衡**:
- ⚠️ 跨数据库查询复杂
- ⚠️ 事务管理困难

**解决方案**:
- 使用应用层协调多个数据库
- 关键操作使用最终一致性

### 5.2 为什么选择 SQLAlchemy ORM？

**决策**: 使用 SQLAlchemy 2.0+ ORM

**理由**:
- ✅ 类型安全
- ✅ 支持领域模型设计
- ✅ 数据库无关性
- ✅ 丰富的查询功能
- ✅ 活跃的社区支持

**权衡**:
- ⚠️ 学习曲线
- ⚠️ 性能开销（相比原生 SQL）

**解决方案**:
- 复杂查询使用原生 SQL
- 使用 joinedload 优化 N+1 问题

### 5.3 混合意图识别架构

**决策**: 规则系统 + RASA NLU + BERT 模型

**架构**:
```
用户输入
    ↓
┌──────────────────────────────┐
│  统一意图识别器              │
├──────────────────────────────┤
│  1. 规则系统 (快速匹配)       │
│  2. RASA NLU (变体处理)      │
│  3. BERT 模型 (深度语义)      │
└──────────────────────────────┘
    ↓
意图结果
```

**理由**:
- ✅ 快速响应（规则系统）
- ✅ 处理口语化（RASA）
- ✅ 深度理解（BERT）
- ✅ 离线可用（本地模型）

#### 5.3.1 能力落地证据（RASA / pgvector）

> 针对 "RASA、pgvector 仅停留在配置阶段，未看到深度落地证据" 的评审意见，
> 统一用下列三类工件作为**运行时证据**，而不是仅靠 ``.env`` / README 声称。

| 维度 | 落地位置 | 证据 / 复现方式 |
|------|----------|----------------|
| RASA 客户端 | `app/ai_engines/rasa/nlu_service.py` | 支持嵌入式 (`RASA_MODEL_PATH`) / 服务器 (`RASA_SERVER_URL`) 双模，`get_status()` 暴露结构化状态。 |
| RASA 接入统一识别器 | `app/domain/services/unified_intent_recognizer.py` | `recognize()` 中新增 RASA 分支，阈值来自 `RASA_CONFIDENCE_THRESHOLD`；`get_engine_status()` 报告每个子引擎是否真正加载。 |
| pgvector 落库 DDL | `app/infrastructure/persistence/pg_vector_store.py`、`user_memory_vector_store.py` | `CREATE EXTENSION vector`、`vector(256)` 列、`ivfflat (... vector_cosine_ops)` 索引与 `<=>` 余弦距离查询。 |
| 运行时健康探针 | `GET /health/readiness`、`GET /health/details` | `checks.rasa` / `checks.pgvector` 分项报告 `healthy / degraded / disabled / unhealthy` 与成因。 |
| 深度诊断端点 | `GET /api/diagnostics/capabilities` | 同时返回 RASA 配置快照、pgvector 扩展版本 + `ivfflat` 索引数 + 挂载的向量表，以及 `intent_engines` 加载明细。 |
| 自检脚本 | `scripts/dev/smoke_capabilities.py` | 本地一条命令产出能力清单，退出码与 CI 兼容。 |
| 回归测试 | `tests/test_services/test_rasa_nlu_service.py`、`tests/test_infrastructure/test_pg_vector_store.py`、`tests/test_routes/test_health_capabilities.py` | 16 条用例覆盖 disabled / server unreachable / server success / embedded missing-model / DDL 片段 / 诊断路由契约。 |

**关键环境变量**：

- `ENABLE_RASA`：全局开关，`0` 时健康检查返回 `disabled` 而非误报 `healthy`。
- `RASA_MODEL_PATH` / `RASA_SERVER_URL` / `RASA_USE_SERVER`：模型与模式控制。
- `RASA_CONFIDENCE_THRESHOLD`：`UnifiedIntentRecognizer` 决策阈值。
- `VECTOR_DB_URL`（回退 `DATABASE_URL`）：未设置或非 Postgres 时 pgvector 探针报告
  `disabled`，并给出 `reason`，避免和 "SQLite 场景" 混淆。

**复现流程（审查人员一条命令）**：

```bash
python scripts/dev/smoke_capabilities.py
# 或启动服务后：
curl -s http://127.0.0.1:5000/api/diagnostics/capabilities | jq
```

当打印中 `rasa.status` 不是 `healthy` 时，`detail` 内会写明 `last_error`
（例如 `model_not_found`、`server_unreachable`），从而把 "是否真用上"
的判断建立在事实而不是猜测之上。

---

## 📊 六、性能优化

### 6.1 缓存策略

**Redis 缓存**（示意，基于 ``redis-py`` + 业务函数装饰器，落点一般在
``app/infrastructure/cache/``）：
```python
import json
from functools import wraps

import redis

_redis = redis.Redis.from_url("redis://localhost:6379/0", decode_responses=True)


def redis_cached(key: str, ttl: int = 300):
    def _wrap(fn):
        @wraps(fn)
        def _inner(*args, **kwargs):
            cached = _redis.get(key)
            if cached is not None:
                return json.loads(cached)
            value = fn(*args, **kwargs)
            _redis.set(key, json.dumps(value, ensure_ascii=False), ex=ttl)
            return value

        return _inner

    return _wrap


@redis_cached("products:list", ttl=300)
def get_product_list():
    return product_service.get_all()
```

### 6.2 数据库优化

**SQLite 优化配置**:
```python
engine = create_engine(
    "sqlite:///products.db",
    connect_args={
        "check_same_thread": False,
    },
    connect_args={
        "pragma": [
            ("journal_mode", "WAL"),      # WAL 模式
            ("synchronous", "NORMAL"),    # 平衡性能和安全
            ("cache_size", "-64000"),     # 64MB 缓存
            ("foreign_keys", "ON"),       # 外键约束
        ]
    }
)
```

### 6.3 前端性能

**Vite 构建优化**:
```javascript
// vite.config.js
export default {
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vue-vendor': ['vue', 'vue-router', 'pinia'],
          'ui-vendor': ['element-plus'],
        },
      },
    },
  },
}
```

---

## 🔒 七、安全设计

### 7.1 认证和授权

**JWT Token 认证**:
```python
from app.auth_decorators import require_auth

@routes.post('/api/products')
@require_auth
def create_product(request):
    # 需要认证
    pass
```

**RBAC 权限控制**:
```python
# app/db/models/permission.py
class Role:
    ADMIN = 'admin'
    USER = 'user'
    GUEST = 'guest'

@require_role(Role.ADMIN)
def delete_product(id: int):
    # 需要管理员权限
    pass
```

### 7.2 数据安全

**密码加密**（使用 ``app/utils/password_hash.py``，纯 stdlib PBKDF2，
werkzeug-compatible 串格式便于与旧库存量哈希向前/向后兼容）：
```python
from app.utils.password_hash import generate_password_hash

class User:
    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)
```

**SQL 注入防护**:
```python
# ✅ 安全：使用参数化查询
products = db.query(Product).filter(
    Product.name == name
).all()

# ❌ 危险：字符串拼接
products = db.execute(
    f"SELECT * FROM products WHERE name = '{name}'"
)
```

---

## 🧪 八、测试策略

### 8.1 测试金字塔

```
         /\
        /  \
       / E2E \      端到端测试（10%）
      /------\
     /        \
    / Integration\  集成测试（20%）
   /--------------\
  /                \
 /    Unit Tests    \ 单元测试（70%）
/____________________\
```

### 8.2 单元测试

```python
# tests/test_domain/test_product_entities.py
def test_product_create():
    product = Product.create(
        name="测试产品",
        model_number="TEST-001",
        price=100.0
    )
    
    assert product.name == "测试产品"
    assert product.price == 100.0
```

### 8.3 集成测试

```python
# tests/test_routes/test_products.py
def test_create_product(client, auth_headers):
    response = client.post(
        '/api/products',
        json={
            'name': '测试产品',
            'price': 100.0
        },
        headers=auth_headers
    )
    
    assert response.status_code == 201
    assert response.json['name'] == '测试产品'
```

---

## 📈 九、扩展性设计

### 9.1 插件化设计

**技能系统**:
```python
# app/infrastructure/skills/__init__.py
class SkillRegistry:
    def __init__(self):
        self.skills = {}
    
    def register(self, name: str, skill):
        self.skills[name] = skill
    
    def get(self, name: str):
        return self.skills.get(name)
```

### 9.2 多数据库支持

**当前**: SQLite  
**未来**: PostgreSQL, MySQL

```python
# 数据库无关设计
class Base:
    pass

# 只需修改配置即可切换数据库
DATABASE_URL = "postgresql://..."
# 或
DATABASE_URL = "mysql://..."
```

---

## 📚 十、相关文档

- [快速开始指南](QUICK_START.md)
- [部署指南](DEPLOYMENT.md)
- [API 参考](API_REFERENCE.md)
- [开发规范](../.github/CONTRIBUTING.md)

---

*最后更新：2026-05-26 - 版本号更新至 v8.0.0，添加跨行业适配说明*
