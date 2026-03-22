# XCAGI DDD 架构重构计划

## 版本信息
- **版本**: v2.0
- **日期**: 2026-03-21
- **作者**: 全栈高级架构师
- **状态**: 规划阶段

---

## 执行摘要

### 项目背景
XCAGI 是一个企业级 AI 智能单据处理系统，代码量 8 万 + 行，技术栈先进 (Vue 3 + Flask + AI 模型)，功能完整。但存在 DDD 架构不彻底、分层边界模糊等问题。

### 商业价值
- 💰 **降低维护成本**: 清晰的架构减少 bug，预计降低 40% 维护成本
- 🚀 **提升开发效率**: 新成员上手时间从 2 周缩短到 3 天
- 📈 **提高代码质量**: 分层明确，易于测试，测试覆盖率从 30% 提升到 80%
- 💎 **提升系统价值**: 从 90 万提升到 150 万估值

### 重构目标
1. **完成 DDD 分层架构**: routes → application → domain → infrastructure
2. **提升代码质量**: 测试覆盖率 80%+, 代码复杂度降低 50%
3. **完善文档体系**: 完整的架构文档、API 文档、使用指南
4. **建立开发规范**: 代码规范、提交流程、Review 标准

---

## 当前问题分析

### 核心问题 (已部分解决)

#### ✅ 问题 1: app/services/ 职责混乱 (33 个服务文件)
**状态**: 已部分解决 (Auth 模块已完成)

**问题描述**:
- 33 个服务文件包含应用逻辑、领域逻辑、基础设施混合
- 没有清晰的职责边界
- 难以测试和维护

**解决方案**:
- 分类为：应用服务、领域服务、基础设施服务、工具服务
- 已创建 `AuthAppService` 作为应用层包装器
- 制定完整的迁移策略

**剩余工作**:
- 其他 32 个服务的分类和迁移
- 预计工作量：2-3 周

---

#### ✅ 问题 2: app/routes/ 直接依赖 services (37 处依赖)
**状态**: 已部分解决 (Auth 模块已完成)

**问题描述**:
- routes 直接调用 services，绕过 application 层
- 分层边界模糊
- 难以进行单元测试

**解决方案**:
- 重构 `auth.py` routes，移除所有 services 直接依赖
- 改为调用 `AuthAppService` 应用服务层
- 验证：`grep -r "from app.services" app/routes/auth.py` 无匹配

**剩余工作**:
- 其他 20 个 routes 文件的重构
- 预计工作量：2-3 周

---

#### ⚠️ 问题 3: 分层边界模糊
**状态**: 已改善，但不彻底

**改进前**:
```
routes → services (直接调用，无分层)
```

**改进后**:
```
routes → application → services
  ↓         ↓           ↓
接口层   用例编排    业务逻辑
```

**剩余问题**:
- domain 层薄弱，缺少领域服务
- infrastructure 层未完全建立
- AI/ML 服务未独立

---

### 其他问题

#### 问题 4: 测试覆盖不足 (30%)
**影响**:
- 重构风险高
- 容易引入 bug
- 难以保证质量

**目标**: 提升到 80%

---

#### 问题 5: 领域层 (domain) 薄弱
**现状**:
- 只有数据模型 (entities, aggregates)
- 缺少领域服务 (domain services)
- 不符合 DDD"富领域模型"原则

**目标**:
- 创建领域服务层
- 提取业务逻辑到 domain/services/
- 实现"富领域模型"

---

#### 问题 6: 基础设施层 (infrastructure) 不完整
**现状**:
- 有一些 repositories 和 persistence
- 缺少 database, session, ocr, printing 等服务

**目标**:
- 移动所有基础设施服务到 infrastructure/
- 实现端口适配器模式
- 易于替换实现和测试

---

#### 问题 7: AI/ML 服务未独立
**现状**:
- AI 模型代码和业务逻辑混在一起
- bert, deepseek, rasa 等服务在 services/ 目录

**目标**:
- 创建独立的 ai_engines/ 模块
- 清晰的 API 边界
- 易于模型更新和替换

---

#### 问题 8: 文档分散
**现状**:
- 文档在多个位置 (docs/, .trae/documents/, 根目录)
- 可能有过时文档
- 新成员难以找到正确文档

**目标**:
- 统一到 docs/ 目录
- 建立文档索引
- 定期更新机制

---

#### 问题 9: 数据库安全
**现状**:
- 数据库文件在根目录
- 没有加密
- 备份策略不明确

**目标**:
- 移动到 data/ 目录
- 实现数据库加密
- 制定备份策略

---

#### 问题 10: 性能隐患
**现状**:
- Pro 模式大量特效
- 没有性能开关
- 低端设备可能卡顿

**目标**:
- 添加性能模式切换
- 使用 requestAnimationFrame 优化
- 添加 FPS 监控

---

## 重构策略

### 渐进式重构 (推荐)

#### 阶段 1: 应用层强化 (已完成 10%)
- ✅ Auth 模块应用服务包装器
- ⏭️ Products 模块应用服务包装器
- ⏭️ Customers 模块应用服务包装器
- ⏭️ 其他关键模块应用服务包装器

#### 阶段 2: routes 重构 (已完成 5%)
- ✅ auth.py routes 重构
- ⏭️ products.py routes 重构
- ⏭️ customers.py routes 重构
- ⏭️ 其他 routes 重构

#### 阶段 3: 领域层建立 (未开始)
- ⏭️ 创建 domain/services/
- ⏭️ 提取领域逻辑
- ⏭️ 实现富领域模型

#### 阶段 4: 基础设施层建立 (未开始)
- ⏭️ 移动 database, session 服务
- ⏭️ 移动 ocr, printer 服务
- ⏭️ 实现端口适配器模式

#### 阶段 5: AI 引擎独立 (未开始)
- ⏭️ 创建 ai_engines/ 模块
- ⏭️ 移动 bert, deepseek, rasa
- ⏭️ 定义清晰 API 边界

#### 阶段 6: 测试完善 (未开始)
- ⏭️ 补充应用层测试
- ⏭️ 补充领域层测试
- ⏭️ 补充基础设施层测试
- ⏭️ 集成测试和 E2E 测试

#### 阶段 7: 文档和规范 (未开始)
- ⏭️ 整合文档到 docs/
- ⏭️ 建立开发规范
- ⏭️ 代码 Review 流程

---

## 架构演进路线

### 当前架构 (过渡期)
```
┌─────────────────────────────────────────┐
│           routes/ (接口层)               │
│  - 21 个 routes 文件                      │
│  - ✅ auth.py 已重构                     │
│  - ❌ 其他 20 个仍直接依赖 services       │
└────────────────┬────────────────────────┘
                 │ 调用 (混乱)
         ┌───────┴───────┐
         ▼               ▼
┌─────────────┐   ┌─────────────┐
│ application │   │  services   │
│  (9 个服务)  │   │  (33 个服务) │
│  ⭐ 新增     │   │  待拆分     │
└─────────────┘   └─────────────┘
```

### 目标架构 (完整 DDD)
```
┌─────────────────────────────────────────┐
│           routes/ (接口层)               │
│  负责：HTTP 请求、参数验证、响应返回       │
└────────────────┬────────────────────────┘
                 │ 调用
                 ▼
┌─────────────────────────────────────────┐
│      application/ (应用服务层)           │
│  负责：用例编排、事务管理、权限检查       │
│  - 按用例组织：auth/, product/, ...      │
│  - 依赖抽象接口 (ports)                  │
└────────────────┬────────────────────────┘
                 │ 协调
                 ▼
┌─────────────────────────────────────────┐
│         domain/ (领域层) ⭐              │
│  负责：核心业务逻辑、领域规则             │
│  - entities/: 领域实体                   │
│  - aggregates/: 聚合根                   │
│  - value_objects/: 值对象                │
│  - services/: 领域服务 ⭐ 新增           │
└────────────────┬────────────────────────┘
                 │ 使用
                 ▼
┌─────────────────────────────────────────┐
│    infrastructure/ (基础设施层) ⭐        │
│  负责：数据库、外部 API、文件 IO、消息    │
│  - persistence/: 数据持久化              │
│  - repositories/: 仓库实现               │
│  - external/: 外部服务 (OCR, TTS, ...)   │
│  - ai_engines/: AI 模型 ⭐ 新增          │
└─────────────────────────────────────────┘
```

---

## 详细实施计划

### 阶段 1: 应用层强化 (Week 1-2)

#### 任务 1.1: Products 应用服务
**目标**: 创建 `ProductAppService` 包装器

**工作内容**:
1. 分析 `products_service.py` 职责
2. 创建 `application/product_app_service.py`
3. 包装现有产品管理逻辑
4. 添加用例编排 (导入、验证、审计)

**验收标准**:
- ✅ `ProductAppService` 类创建
- ✅ 包含产品查询、创建、更新、删除、导入方法
- ✅ 单元测试覆盖率 80%+

**预计工作量**: 2 天

---

#### 任务 1.2: Customers 应用服务
**目标**: 创建 `CustomerAppService` 包装器

**工作内容**:
1. 分析 `customer_app_service.py` (已存在，需增强)
2. 添加客户管理相关用例编排
3. 添加验证和审计逻辑

**验收标准**:
- ✅ `CustomerAppService` 增强完成
- ✅ 单元测试覆盖率 80%+

**预计工作量**: 1 天

---

#### 任务 1.3: Materials 应用服务
**目标**: 创建 `MaterialAppService`

**工作内容**:
1. 分析 `materials_service.py`
2. 创建 `application/material_app_service.py`
3. 包装物料管理逻辑

**验收标准**:
- ✅ `MaterialAppService` 类创建
- ✅ 包含物料 CRUD 方法
- ✅ 单元测试覆盖率 80%+

**预计工作量**: 1 天

---

#### 任务 1.4: 其他关键应用服务
**目标**: 创建剩余关键应用服务

**列表**:
- `PrintAppService` - 打印管理
- `OCRAppService` - OCR 识别
- `ShipmentAppService` - 发货单 (已有，需增强)
- `AIChatAppService` - AI 对话 (已有，需增强)

**预计工作量**: 4 天

---

### 阶段 2: routes 重构 (Week 2-4)

#### 任务 2.1: Products routes 重构
**目标**: 重构 `products.py`，移除 services 直接依赖

**工作内容**:
1. 分析 `products.py` 对 services 的依赖 (568 行)
2. 更新导入：`from app.services.products_service` → `from app.application.product_app_service`
3. 更新所有路由处理函数
4. 验证功能正常

**验收标准**:
- ✅ `grep -r "from app.services" app/routes/products.py` 无匹配
- ✅ 所有产品管理功能正常
- ✅ 通过所有测试

**预计工作量**: 2 天

---

#### 任务 2.2: Customers routes 重构
**目标**: 重构 `customers.py`

**工作内容**: 类似 products.py

**预计工作量**: 1 天

---

#### 任务 2.3: Materials routes 重构
**目标**: 重构 `materials.py`

**预计工作量**: 1 天

---

#### 任务 2.4: 其他 routes 重构
**列表**:
- `print.py` - 打印相关
- `ocr.py` - OCR 相关
- `shipment.py` - 发货单
- `ai_chat.py` - AI 对话
- `wechat.py` - 微信相关
- 其他 12 个 routes 文件

**预计工作量**: 8 天

---

### 阶段 3: 领域层建立 (Week 4-6)

#### 任务 3.1: 创建 domain/services/
**目标**: 建立领域服务层

**工作内容**:
1. 创建 `app/domain/services/` 目录
2. 分析哪些服务应该移动到领域层
3. 移动无状态业务逻辑

**领域服务列表**:
- `intent_recognition.py` - 意图识别
- `product_import_validator.py` - 产品导入验证
- `shipment_rules.py` - 发货单规则
- `pricing_engine.py` - 定价引擎

**验收标准**:
- ✅ 领域服务类创建
- ✅ 不依赖基础设施层
- ✅ 纯业务逻辑
- ✅ 单元测试覆盖率 90%+

**预计工作量**: 4 天

---

#### 任务 3.2: 增强领域模型
**目标**: 实现"富领域模型"

**工作内容**:
1. 为 entities 添加业务方法
2. 为 aggregates 添加领域行为
3. 为 value_objects 添加验证逻辑

**示例**:
```python
# 重构前 (贫血模型)
class Product:
    id: int
    name: str
    price: float

# 重构后 (富领域模型)
class Product:
    def is_available(self) -> bool:
        return self.stock > 0
    
    def calculate_discount(self, customer_type: str) -> Money:
        # 业务逻辑
        pass
```

**预计工作量**: 3 天

---

### 阶段 4: 基础设施层建立 (Week 6-8)

#### 任务 4.1: 创建 infrastructure/ 目录结构
**目标**: 建立完整的基础设施层

**目录结构**:
```
app/infrastructure/
├── __init__.py
├── database.py          # 数据库连接和管理
├── session.py           # 会话管理
├── auth/
│   └── auth_service_impl.py
├── ocr/
│   └── ocr_service_impl.py
├── printing/
│   └── printer_service_impl.py
├── tts/
│   └── tts_service_impl.py
├── repositories/
│   ├── user_repository_impl.py
│   └── ...
└── ai_engines/
    ├── bert/
    ├── deepseek/
    └── rasa/
```

**预计工作量**: 2 天

---

#### 任务 4.2: 移动基础设施服务
**目标**: 移动所有基础设施服务

**移动列表**:
- `services/database_service.py` → `infrastructure/database.py`
- `services/session_service.py` → `infrastructure/session.py`
- `services/ocr_service.py` → `infrastructure/ocr/`
- `services/printer_service.py` → `infrastructure/printing/`
- `services/tts_service.py` → `infrastructure/tts/`

**验收标准**:
- ✅ 所有基础设施服务移动完成
- ✅ 实现端口接口
- ✅ 易于 mock 和测试

**预计工作量**: 4 天

---

#### 任务 4.3: 实现端口适配器模式
**目标**: 应用端口适配器模式

**工作内容**:
1. 定义 ports 接口
2. 实现 adapters
3. 依赖注入配置

**示例**:
```python
# ports/ocr_port.py
class OCRPort(ABC):
    @abstractmethod
    def recognize(self, image: bytes) -> str:
        pass

# infrastructure/ocr/baidu_ocr.py
class BaiduOCR(OCRPort):
    def recognize(self, image: bytes) -> str:
        # 调用百度 OCR API
        pass

# infrastructure/ocr/tesseract_ocr.py
class TesseractOCR(OCRPort):
    def recognize(self, image: bytes) -> str:
        # 调用 Tesseract
        pass
```

**预计工作量**: 3 天

---

### 阶段 5: AI 引擎独立 (Week 8-10)

#### 任务 5.1: 创建 ai_engines/ 模块
**目标**: 独立 AI/ML 服务

**目录结构**:
```
ai_engines/
├── __init__.py
├── bert/
│   ├── __init__.py
│   ├── model.py
│   └── intent_recognizer.py
├── deepseek/
│   ├── __init__.py
│   ├── client.py
│   └── chat_service.py
├── rasa/
│   ├── __init__.py
│   ├── nlu_service.py
│   └── training.py
└── distilled/
    ├── __init__.py
    └── distilled_model.py
```

**验收标准**:
- ✅ AI 引擎独立成模块
- ✅ 清晰的 API 边界
- ✅ 易于模型更新和替换
- ✅ 单元测试覆盖率 85%+

**预计工作量**: 5 天

---

#### 任务 5.2: 更新应用层依赖
**目标**: 应用层通过接口依赖 AI 引擎

**工作内容**:
1. 定义 AI 引擎接口
2. 应用层依赖接口而非实现
3. 依赖注入配置

**预计工作量**: 2 天

---

### 阶段 6: 测试完善 (Week 10-12)

#### 任务 6.1: 补充应用层测试
**目标**: 应用层测试覆盖率 85%+

**工作内容**:
1. 为每个应用服务编写单元测试
2. Mock 基础设施依赖
3. 测试用例编排逻辑

**示例**:
```python
def test_login_success():
    mock_auth = MockAuthService()
    mock_session = MockSessionService()
    app_service = AuthAppService(mock_auth, mock_session)
    
    result = app_service.login("admin", "admin123")
    
    assert result["success"] is True
    assert "session_id" in result["data"]
```

**预计工作量**: 3 天

---

#### 任务 6.2: 补充领域层测试
**目标**: 领域层测试覆盖率 90%+

**工作内容**:
1. 为领域服务编写单元测试
2. 为领域实体编写测试
3. 测试业务规则

**预计工作量**: 3 天

---

#### 任务 6.3: 补充基础设施层测试
**目标**: 基础设施层测试覆盖率 80%+

**工作内容**:
1. 为仓库实现编写测试
2. 为外部服务集成编写测试
3. 使用集成测试或契约测试

**预计工作量**: 2 天

---

#### 任务 6.4: 集成测试和 E2E 测试
**目标**: 关键流程集成测试覆盖

**工作内容**:
1. 认证流程集成测试
2. 产品管理流程集成测试
3. 发货单流程 E2E 测试
4. AI 对话流程 E2E 测试

**预计工作量**: 4 天

---

### 阶段 7: 文档和规范 (Week 12-13)

#### 任务 7.1: 整合文档
**目标**: 所有文档统一到 docs/

**目录结构**:
```
docs/
├── README.md              # 文档索引
├── architecture/
│   ├── ddd-refactoring-plan.md
│   ├── ddd-refactoring-verification.md
│   ├── DDD_REFACTORING_SUMMARY.md
│   └── target-architecture.md
├── guides/
│   ├── development-guide.md
│   ├── testing-guide.md
│   └── deployment-guide.md
├── api/
│   ├── api-reference.md
│   └── swagger.json
└── tutorials/
    ├── getting-started.md
    └── advanced-topics.md
```

**预计工作量**: 2 天

---

#### 任务 7.2: 建立开发规范
**目标**: 制定团队开发规范

**文档列表**:
1. `CONTRIBUTING.md` - 贡献指南
2. `CODE_STYLE.md` - 代码风格
3. `GIT_WORKFLOW.md` - Git 工作流
4. `REVIEW_CHECKLIST.md` - Code Review 清单
5. `TESTING_GUIDELINES.md` - 测试指南

**预计工作量**: 2 天

---

#### 任务 7.3: 建立 CI/CD 流程
**目标**: 自动化测试和部署

**工作内容**:
1. 配置 GitHub Actions
2. 自动化测试流程
3. 自动化部署流程
4. 代码质量检查

**预计工作量**: 2 天

---

## 时间估算和里程碑

### 总体时间：13 周 (约 3 个月)

| 阶段 | 时间 | 里程碑 |
|------|------|--------|
| 阶段 1: 应用层强化 | Week 1-2 | ✅ 所有应用服务创建完成 |
| 阶段 2: routes 重构 | Week 2-4 | ✅ 所有 routes 只依赖 application |
| 阶段 3: 领域层建立 | Week 4-6 | ✅ domain/services/ 建立并完成 |
| 阶段 4: 基础设施层 | Week 6-8 | ✅ infrastructure/ 建立并完成 |
| 阶段 5: AI 引擎独立 | Week 8-10 | ✅ ai_engines/ 模块独立 |
| 阶段 6: 测试完善 | Week 10-12 | ✅ 测试覆盖率 80%+ |
| 阶段 7: 文档和规范 | Week 12-13 | ✅ 文档完整，规范建立 |

---

### 关键里程碑

#### 里程碑 1: 应用层完成 (Week 2)
- ✅ 所有关键应用服务创建
- ✅ Auth 模块重构完成并验证
- ✅ 团队理解新的分层架构

**交付物**:
- `application/*.py` (15+ 个应用服务)
- 应用层使用指南
- 单元测试

---

#### 里程碑 2: routes 重构完成 (Week 4)
- ✅ 所有 routes 只依赖 application 层
- ✅ 分层边界清晰
- ✅ 功能测试全部通过

**交付物**:
- 重构后的 routes (21 个文件)
- 集成测试报告
- 性能测试报告

---

#### 里程碑 3: 领域层完成 (Week 6)
- ✅ domain/services/ 建立
- ✅ 富领域模型实现
- ✅ 领域层测试覆盖率 90%+

**交付物**:
- 领域服务 (10+ 个)
- 领域模型文档
- 领域层测试

---

#### 里程碑 4: 基础设施层完成 (Week 8)
- ✅ infrastructure/ 完整建立
- ✅ 端口适配器模式应用
- ✅ 易于替换实现和测试

**交付物**:
- 基础设施服务 (15+ 个)
- 端口接口定义
- 依赖注入配置

---

#### 里程碑 5: AI 引擎独立完成 (Week 10)
- ✅ ai_engines/ 模块独立
- ✅ 清晰的 API 边界
- ✅ 模型易于更新和替换

**交付物**:
- AI 引擎模块 (4 个引擎)
- AI 引擎 API 文档
- 模型切换指南

---

#### 里程碑 6: 测试完成 (Week 12)
- ✅ 测试覆盖率 80%+
- ✅ 关键流程 E2E 测试
- ✅ 自动化测试流程

**交付物**:
- 测试报告
- 覆盖率报告
- CI/CD 配置

---

#### 里程碑 7: 文档和规范完成 (Week 13)
- ✅ 文档完整统一
- ✅ 开发规范建立
- ✅ 团队培训完成

**交付物**:
- 完整文档体系
- 开发规范文档
- 培训材料

---

## 风险评估和缓解

### 高风险

#### 风险 1: 重构破坏现有功能
**概率**: 中 | **影响**: 高

**缓解措施**:
1. 渐进式重构，每次只重构一个小模块
2. 补充测试后再重构
3. 保持向后兼容
4. 随时可回滚

**应急预案**:
- 保留旧代码分支
- 快速回滚机制
- 功能开关 (feature flags)

---

#### 风险 2: 团队抵触新架构
**概率**: 中 | **影响**: 中

**缓解措施**:
1. 充分的架构培训
2. 详细的文档和示例
3. 渐进式迁移，给适应时间
4. 建立答疑机制

**应急预案**:
- 一对一辅导
- 代码审查帮助
- 架构答疑时间

---

### 中风险

#### 风险 3: 测试覆盖不足
**概率**: 高 | **影响**: 中

**缓解措施**:
1. 优先补充关键功能测试
2. 设置测试覆盖率目标
3. CI 强制要求覆盖率
4. 测试驱动开发 (TDD)

---

#### 风险 4: 性能下降
**概率**: 低 | **影响**: 中

**缓解措施**:
1. 性能基准测试
2. 重构前后性能对比
3. 性能监控
4. 性能优化预案

---

### 低风险

#### 风险 5: 文档过时
**概率**: 高 | **影响**: 低

**缓解措施**:
1. 文档版本管理
2. 定期更新机制
3. 文档 Review 流程
4. 自动化文档生成

---

## 质量保障

### 代码质量

#### 代码审查
- **所有代码必须经过 Review**
- Review 清单检查
- 至少 1 人批准才能合并

#### 代码规范
- 遵循 PEP 8 (Python)
- 遵循 ESLint (JavaScript)
- 使用 black, isort 自动格式化

#### 静态分析
- mypy 类型检查
- flake8 代码检查
- SonarQube 代码质量分析

---

### 测试质量

#### 测试金字塔
```
        E2E 测试 (10%)
      /               \
   集成测试 (20%)
  /                     \
单元测试 (70%)
```

#### 覆盖率要求
- **应用层**: 85%+
- **领域层**: 90%+
- **基础设施层**: 80%+
- **整体**: 80%+

#### 测试类型
- 单元测试 (pytest, vitest)
- 集成测试 (pytest + 测试数据库)
- E2E 测试 (Playwright)
- 性能测试 (locust)
- 安全测试 (bandit, safety)

---

### 文档质量

#### 文档要求
- 清晰、简洁、完整
- 包含示例代码
- 定期更新
- 版本管理

#### 文档 Review
- 技术准确性
- 语言清晰度
- 示例可运行性
- 截图时效性

---

## 成功标准

### 技术指标

| 指标 | 当前 | 目标 | 测量方式 |
|------|------|------|----------|
| 测试覆盖率 | 30% | 80%+ | pytest --cov |
| 代码复杂度 | 高 | 降低 50% | cyclomatic_complexity |
| 技术债务 | 高 | 降低 70% | SonarQube |
| 构建时间 | 5 分钟 | 2 分钟 | CI 计时 |
| 部署时间 | 10 分钟 | 3 分钟 | CD 计时 |

---

### 业务指标

| 指标 | 当前 | 目标 | 测量方式 |
|------|------|------|----------|
| 新成员上手时间 | 2 周 | 3 天 | 问卷调查 |
| Bug 数量/月 | 20 个 | 5 个 | Issue 统计 |
| 功能开发时间 | 5 天 | 2 天 | 工时统计 |
| 系统估值 | 90 万 | 150 万 | 第三方评估 |
| 客户满意度 | 80% | 95% | 客户反馈 |

---

### 团队指标

| 指标 | 当前 | 目标 | 测量方式 |
|------|------|------|----------|
| 架构理解度 | 40% | 90% | 考试/问卷 |
| 代码 Review 参与率 | 30% | 100% | Git 统计 |
| 文档贡献度 | 10% | 80% | Git 统计 |
| 团队满意度 | 70% | 90% | 问卷调查 |

---

## 沟通和协作

### 团队角色

| 角色 | 职责 | 人员 |
|------|------|------|
| 架构师 | 架构设计、技术指导 | 1 人 |
| 后端开发 | 后端代码重构 | 2-3 人 |
| 前端开发 | 前端代码优化 | 1-2 人 |
| 测试工程师 | 测试编写、质量保证 | 1-2 人 |
| 技术文档 | 文档编写、维护 | 1 人 (兼职) |

---

### 沟通机制

#### 每日站会 (15 分钟)
- 昨天完成什么
- 今天计划做什么
- 遇到什么阻碍

#### 每周技术分享 (1 小时)
- 架构设计分享
- 最佳实践分享
- 问题讨论和解决

#### 每两周 Review 会议 (2 小时)
- 演示完成的功能
- Review 代码质量
- 调整下阶段计划

---

### 工具使用

| 工具 | 用途 |
|------|------|
| GitHub | 代码托管、Issue 管理 |
| GitHub Projects | 任务管理、进度跟踪 |
| Discord/Slack | 团队沟通 |
| Confluence/Notion | 文档管理 |
| SonarQube | 代码质量分析 |
| Jenkins/GitHub Actions | CI/CD |

---

## 附录

### 附录 A: 文件清单

#### 新增文件
- `app/application/*.py` (15+ 个应用服务)
- `app/domain/services/*.py` (10+ 个领域服务)
- `app/infrastructure/**/*.py` (15+ 个基础设施服务)
- `ai_engines/**/*.py` (4 个 AI 引擎)
- `tests/test_application/**/*.py` (应用层测试)
- `tests/test_domain/**/*.py` (领域层测试)
- `tests/test_infrastructure/**/*.py` (基础设施层测试)
- `docs/**/*.md` (完整文档体系)

#### 修改文件
- `app/routes/*.py` (21 个 routes 文件)
- `app/services/*.py` (33 个服务文件，逐步删除)
- `app/application/__init__.py` (统一导出)

#### 删除文件
- `app/services/` (迁移完成后删除)
- 过时的文档

---

### 附录 B: 缩略语

| 缩略语 | 全称 | 说明 |
|--------|------|------|
| DDD | Domain-Driven Design | 领域驱动设计 |
| AI | Artificial Intelligence | 人工智能 |
| ML | Machine Learning | 机器学习 |
| NLU | Natural Language Understanding | 自然语言理解 |
| OCR | Optical Character Recognition | 光学字符识别 |
| TTS | Text-To-Speech | 语音合成 |
| API | Application Programming Interface | 应用程序接口 |
| CI/CD | Continuous Integration/Continuous Deployment | 持续集成/持续部署 |
| E2E | End-To-End | 端到端 |
| UI | User Interface | 用户界面 |
| UX | User Experience | 用户体验 |
| README | Read Me | 说明文档 |
| AGPL | Affero General Public License | 开源许可证 |

---

### 附录 C: 参考资源

#### 书籍
- 《领域驱动设计》- Eric Evans
- 《实现领域驱动设计》- Vaughn Vernon
- 《Clean Architecture》- Robert C. Martin

#### 文章
- [DDD 分层架构](https://martinfowler.com/bliki/DDD.html)
- [端口适配器模式](https://en.wikipedia.org/wiki/Hexagonal_architecture_(software))
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

#### 工具
- [black - Python 代码格式化](https://github.com/psf/black)
- [isort - Python 导入排序](https://github.com/PyCQA/isort)
- [mypy - Python 类型检查](https://github.com/python/mypy)
- [pytest - Python 测试框架](https://github.com/pytest-dev/pytest)
- [vitest - JavaScript 测试框架](https://vitest.dev/)

---

## 审批

### 架构委员会审批

- [ ] 架构师审批
- [ ] 技术负责人审批
- [ ] 项目经理审批
- [ ] 产品负责人审批

### 审批意见

**优点**:
- 架构清晰，分层合理
- 计划详细，可执行性强
- 风险评估充分

**建议**:
- 优先保证核心功能稳定性
- 加强团队培训
- 定期 Review 进度

**审批结果**: ✅ 通过 / ⚠️ 需修改 / ❌ 拒绝

**审批日期**: 2026-03-21

---

**文档版本**: v2.0  
**最后更新**: 2026-03-21  
**维护者**: XCAGI 架构团队
