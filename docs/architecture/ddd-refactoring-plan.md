# DDD 架构重构计划

## 📊 当前问题分析

### 现状
```
app/
├── services/        # 33 个服务文件 - ❌ 职责混乱
│   ├── auth_service.py
│   ├── products_service.py
│   ├── intent_service.py
│   └── ... (30 个文件)
├── application/     # 8 个应用服务 - ✅ 符合 DDD
│   ├── shipment_app_service.py
│   ├── product_app_service.py
│   └── ... (8 个文件)
└── routes/          # ❌ 直接调用 services，绕过 application
```

### 问题
1. **分层边界模糊**: services 和 application 职责重叠
2. **路由绕过应用层**: routes 直接调用 services
3. **领域逻辑泄露**: 业务逻辑在 services 层，不在 domain 层

---

## 🎯 重构目标

### 目标架构
```
app/
├── domain/              # 领域层 (Entities + Aggregates + Domain Services)
│   ├── entities/        # 领域实体
│   ├── aggregates/      # 聚合根
│   ├── value_objects/   # 值对象
│   └── services/        # 领域服务 (无状态业务逻辑)
│
├── application/         # 应用层 (Application Services - 用例编排)
│   ├── ports/           # 端口接口 (Repository Ports)
│   ├── shipment/        # 按用例组织
│   ├── product/
│   ├── customer/
│   └── ai_chat/
│
├── infrastructure/      # 基础设施层 (实现端口接口)
│   ├── persistence/     # 数据持久化
│   ├── repositories/    # 仓库实现
│   └── external/        # 外部服务集成
│
├── routes/              # 接口层 (仅调用 application 层)
│   ├── shipment.py
│   ├── products.py
│   └── ...
│
└── services/            # ❌ 逐步迁移后删除
```

---

## 📝 服务分类策略

### 第一类：应用服务 (迁移到 application/)
这些服务负责**用例编排**，应该保留并强化:

```python
# ✅ 保留在 application/
- shipment_app_service.py       # 已存在
- product_app_service.py        # 已存在
- customer_app_service.py       # 已存在
- ai_chat_app_service.py        # 已存在
- wechat_contact_app_service.py # 已存在
```

**新增应用服务**:
```python
# 需要从 services/ 迁移过来
- auth_app_service.py           # 从 auth_service.py 提取
- user_app_service.py           # 从 user_service.py 提取
- material_app_service.py       # 从 materials_service.py 提取
- print_app_service.py          # 从 printer_service.py 提取
- ocr_app_service.py            # 从 ocr_service.py 提取
```

### 第二类：领域服务 (移动到 domain/services/)
这些是**无状态的业务逻辑**，符合 DDD 领域服务概念:

```python
# 移动到 domain/services/
- ai_product_parser.py          → domain/services/ai_product_parser.py
- ai_conversation_service.py    → domain/services/ai_conversation.py
- intent_service.py             → domain/services/intent_recognition.py
- hybrid_intent_service.py      → domain/services/hybrid_intent.py
- rule_engine.py                → domain/services/rule_engine.py
- product_import_service.py     → domain/services/product_import.py
```

### 第三类：基础设施服务 (移动到 infrastructure/)
这些是**技术实现细节**，应该属于基础设施层:

```python
# 移动到 infrastructure/
- database_service.py           → infrastructure/database.py
- session_service.py            → infrastructure/session.py
- auth_service.py (技术实现)    → infrastructure/auth/
- ocr_service.py                → infrastructure/ocr/
- printer_service.py            → infrastructure/printing/
- tts_service.py                → infrastructure/tts/
```

### 第四类：工具服务 (保留但重命名)
这些是**通用工具**，可以保留但需要重新组织:

```python
# 重命名并组织到 utils/ 或保留在 services/skills/
- skills/*                      → services/skills/ (保持不变)
- extract_log_service.py        → utils/log_extractor.py
- system_service.py             → utils/system_info.py
- task_context_service.py       → utils/task_context.py
```

### 第五类：AI/ML 服务 (独立模块)
这些是**AI 模型相关**，建议独立:

```python
# 保持独立，作为 AI 引擎模块
- bert_intent_service.py        → ai_engines/bert/
- deepseek_intent_service.py    → ai_engines/deepseek/
- rasa_nlu_service.py           → ai_engines/rasa/
- distilled_intent_service.py   → ai_engines/distilled/
- distillation_trainer.py       → ai_engines/trainer/
```

---

## 🔄 迁移步骤

### 阶段 1: 准备 (1-2 天)
1. ✅ 创建新的目录结构
2. ✅ 添加 `__init__.py` 和类型注解
3. ✅ 更新导入路径映射

### 阶段 2: 迁移应用服务 (2-3 天)
1. 创建新的应用服务接口
2. 迁移 auth, user, material 等服务
3. 更新 routes 调用

### 阶段 3: 迁移领域服务 (3-4 天)
1. 提取领域逻辑到 domain/services/
2. 确保领域服务无状态
3. 更新应用服务调用

### 阶段 4: 迁移基础设施 (2-3 天)
1. 移动技术实现到 infrastructure/
2. 实现端口接口
3. 更新依赖注入

### 阶段 5: 清理 (1-2 天)
1. 删除旧的 services/ 目录
2. 更新文档
3. 运行测试验证

---

## 📦 新目录结构

```
app/
├── domain/
│   ├── entities/
│   │   ├── user.py
│   │   ├── customer.py
│   │   ├── product.py
│   │   └── shipment.py
│   ├── aggregates/
│   │   └── shipment.py
│   ├── value_objects/
│   │   ├── money.py
│   │   ├── quantity.py
│   │   └── contact_info.py
│   └── services/
│       ├── intent_recognition.py
│       ├── ai_conversation.py
│       ├── product_import.py
│       └── rule_engine.py
│
├── application/
│   ├── ports/
│   │   ├── user_repository.py
│   │   ├── shipment_repository.py
│   │   └── ...
│   ├── auth/
│   │   └── auth_app_service.py
│   ├── user/
│   │   └── user_app_service.py
│   ├── shipment/
│   │   └── shipment_app_service.py
│   └── ...
│
├── infrastructure/
│   ├── database.py
│   ├── session.py
│   ├── auth/
│   │   └── auth_service_impl.py
│   ├── ocr/
│   │   └── ocr_service_impl.py
│   └── repositories/
│       ├── user_repository_impl.py
│       └── shipment_repository_impl.py
│
├── ai_engines/
│   ├── bert/
│   ├── deepseek/
│   ├── rasa/
│   └── __init__.py
│
├── services/
│   └── skills/              # 保留技能服务
│
└── routes/                  # 只调用 application 层
```

---

## 🔧 重构示例

### 示例 1: Auth 服务重构

**当前代码** (routes/auth.py):
```python
from app.services.auth_service import get_auth_service

@auth_bp.route("/login", methods=["POST"])
def login():
    auth_service = get_auth_service()
    result = auth_service.authenticate(username, password)
```

**重构后** (routes/auth.py):
```python
from app.application.auth.auth_app_service import get_auth_app_service

@auth_bp.route("/login", methods=["POST"])
def login():
    auth_app_service = get_auth_app_service()
    result = auth_app_service.login(username, password)
```

**应用服务** (application/auth/auth_app_service.py):
```python
from domain.services.intent_recognition import IntentRecognizer
from infrastructure.auth.auth_service_impl import AuthServiceImpl
from infrastructure.session.session_manager import SessionManager

class AuthAppService:
    def __init__(self, auth_impl: AuthServiceImpl, session_mgr: SessionManager):
        self._auth_impl = auth_impl
        self._session_mgr = session_mgr
    
    def login(self, username: str, password: str) -> dict:
        # 用例编排
        user = self._auth_impl.authenticate(username, password)
        session = self._session_mgr.create_session(user)
        return {"user": user, "session": session}
```

---

## ✅ 验证标准

重构完成后，检查以下标准:

1. ✅ **routes/ 只导入 application/** 
   ```bash
   grep -r "from app.services" app/routes/  # 应该无结果
   ```

2. ✅ **application/ 只导入 domain/ 和 ports/**
   ```bash
   grep -r "from app.infrastructure" app/application/  # 应该只通过 ports
   ```

3. ✅ **domain/ 无外部依赖**
   ```bash
   grep -r "from app.infrastructure" app/domain/  # 应该无结果
   ```

4. ✅ **所有测试通过**
   ```bash
   pytest tests/ -v
   ```

---

## 📅 时间估算

| 阶段 | 工作量 | 风险 |
|------|--------|------|
| 阶段 1: 准备 | 1-2 天 | 低 |
| 阶段 2: 应用服务 | 2-3 天 | 中 |
| 阶段 3: 领域服务 | 3-4 天 | 中 |
| 阶段 4: 基础设施 | 2-3 天 | 高 |
| 阶段 5: 清理 | 1-2 天 | 低 |
| **总计** | **9-14 天** | **中** |

---

## 🚨 风险评估

### 高风险
1. **基础设施迁移**: 可能影响现有功能
2. **依赖注入**: 需要仔细处理循环依赖

### 中风险
1. **领域服务提取**: 可能遗漏某些业务逻辑
2. **测试覆盖**: 需要补充测试

### 低风险
1. **目录结构调整**: 机械性工作
2. **导入路径更新**: 可自动化处理

---

## 📚 参考文档

- [DDD 分层架构](https://martinfowler.com/bliki/DDD.html)
- [端口适配器模式](https://en.wikipedia.org/wiki/Hexagonal_architecture_(software))
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

---

**下一步**: 开始执行阶段 1 - 准备新目录结构
