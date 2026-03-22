# XCAGI 架构设计文档

> 领域驱动设计（DDD）架构详解  
> 版本：3.0.0

---

## 📐 一、架构概览

### 1.1 架构演进

```
v1.0: 单文件脚本
    ↓
v2.0: 分层架构（MVC）
    ↓
v3.0: 领域驱动设计（DDD）
```

### 1.2 为什么选择 DDD？

**v2.0 架构的问题**:
- ❌ 业务逻辑分散，难以维护
- ❌ 数据库耦合严重
- ❌ 难以测试
- ❌ 代码复用性差

**v3.0 DDD 架构的优势**:
- ✅ 清晰的职责划分
- ✅ 业务逻辑集中在领域层
- ✅ 易于测试和维护
- ✅ 支持复杂业务场景
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

---

## 📁 二、目录结构

### 2.1 后端目录结构

```
app/
├── domain/                    # 领域层
│   ├── product/              # 产品领域
│   │   ├── __init__.py
│   │   ├── entities.py       # 领域实体
│   │   └── value_objects.py  # 值对象
│   ├── customer/             # 客户领域
│   │   ├── __init__.py
│   │   └── entities.py
│   ├── shipment/             # 发货领域
│   │   ├── __init__.py
│   │   ├── aggregates.py     # 聚合根
│   │   └── shipment_product_parser.py
│   ├── services/             # 领域服务
│   │   ├── pricing_engine.py
│   │   ├── shipment_rules_engine.py
│   │   └── unified_intent_recognizer.py
│   └── README.md             # 领域层说明
│
├── application/              # 应用层
│   ├── ports/                # 端口接口
│   │   ├── product_repository.py
│   │   ├── shipment_repository.py
│   │   ├── file_analysis.py
│   │   └── wechat_contact_store.py
│   ├── __init__.py
│   ├── product_app_service.py    # 应用服务
│   ├── shipment_app_service.py
│   ├── wechat_contact_app_service.py
│   └── README.md
│
├── infrastructure/           # 基础设施层
│   ├── repositories/         # 仓储实现
│   │   ├── product_repository_impl.py
│   │   └── shipment_repository_impl.py
│   ├── database/             # 数据库
│   │   └── database_manager.py
│   ├── ocr/                  # OCR 服务
│   │   └── ocr_adapter.py
│   ├── printing/             # 打印服务
│   │   └── printer_adapter.py
│   ├── tts/                  # TTS 服务
│   │   └── tts_adapter.py
│   └── README.md
│
├── routes/                   # API 路由（表现层）
│   ├── products.py
│   ├── shipment.py
│   ├── wechat_contacts.py
│   └── __init__.py
│
├── services/                 # 业务服务（遗留，逐步迁移）
│   ├── products_service.py
│   ├── shipment_service.py
│   └── ...
│
├── db/                       # 数据库模型（基础设施）
│   ├── models/
│   ├── base.py
│   └── init_db.py
│
└── utils/                    # 工具函数
    ├── logger.py
    └── ...
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

---

## 📊 六、性能优化

### 6.1 缓存策略

**Redis 缓存**:
```python
from flask_caching import Cache

cache = Cache(config={'CACHE_TYPE': 'redis'})

@cache.cached(timeout=300)
def get_product_list():
    # 缓存 5 分钟
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

**密码加密**:
```python
from werkzeug.security import generate_password_hash

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

*最后更新：2026-03-23*
