# 应用服务层使用指南

## 📚 什么是应用服务层？

应用服务层 (Application Layer) 位于 routes 层和 services 层之间，负责:
- **用例编排**: 协调多个 services 完成一个业务用例
- **事务管理**: 确保数据一致性
- **对外接口**: 为 routes 层提供统一的接口

## 🎯 为什么要引入应用服务层？

### 重构前 (问题)
```python
# routes/auth.py - 直接调用 services
from app.services.auth_service import get_auth_service
from app.services.user_service import get_user_service
from app.services.session_service import get_session_service

# 问题：
# 1. routes 层知道太多实现细节
# 2. 业务逻辑分散，难以维护
# 3. 分层边界模糊
```

### 重构后 (优势)
```python
# routes/auth.py - 只调用 application 层
from app.application.auth_app_service import get_auth_app_service

# 优势：
# 1. routes 层只需关心 HTTP 请求
# 2. 业务逻辑集中在 application 层
# 3. 分层清晰，易于测试
```

---

## 📦 可用的应用服务

### 已实现的应用服务

| 应用服务 | 文件路径 | 功能 |
|---------|---------|------|
| `AuthAppService` | `application/auth_app_service.py` | 用户认证、授权、密码管理 |
| `ShipmentApplicationService` | `application/shipment_app_service.py` | 发货单创建、查询、管理 |
| `ProductAppService` | `application/product_app_service.py` | 产品管理、导入 |
| `CustomerAppService` | `application/customer_app_service.py` | 客户管理 |
| `AIChatAppService` | `application/ai_chat_app_service.py` | AI 对话 |
| `WeChatContactAppService` | `application/wechat_contact_app_service.py` | 微信联系人管理 |
| `TemplateAppService` | `application/template_app_service.py` | 模板管理 |
| `FileAnalysisAppService` | `application/file_analysis_app_service.py` | 文件分析 |
| `UnitProductsImportAppService` | `application/unit_products_import_app_service.py` | 产品导入 |

### 计划中的应用服务

- [ ] `MaterialAppService` - 物料管理
- [ ] `PrintAppService` - 打印管理
- [ ] `OCRAppService` - OCR 识别
- [ ] `UserAppService` - 用户管理

---

## 🔧 如何使用应用服务

### 示例 1: 用户认证

```python
from flask import Blueprint, request, jsonify
from app.application.auth_app_service import get_auth_app_service

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    
    # 获取应用服务实例
    auth_app_service = get_auth_app_service()
    
    # 调用应用服务方法
    result = auth_app_service.login(username, password)
    
    # 返回结果
    return jsonify(result)
```

### 示例 2: 创建发货单

```python
from flask import Blueprint, request, jsonify
from app.application.shipment_app_service import get_shipment_application_service

shipment_bp = Blueprint("shipment", __name__, url_prefix="/api/shipment")

@shipment_bp.route("/create", methods=["POST"])
def create_shipment():
    data = request.get_json(silent=True) or {}
    unit_name = data.get("unit_name")
    items = data.get("items", [])
    
    # 获取应用服务实例
    app_service = get_shipment_application_service()
    
    # 调用应用服务方法
    result = app_service.create_shipment(
        unit_name=unit_name,
        items_data=items
    )
    
    return jsonify(result)
```

---

## 🏗️ 架构分层说明

### 完整分层架构

```
┌─────────────────────────────────────────┐
│           routes/ (接口层)               │
│  负责：HTTP 请求处理、参数验证、响应返回   │
└────────────────┬────────────────────────┘
                 │ 调用
                 ▼
┌─────────────────────────────────────────┐
│      application/ (应用服务层) ⭐        │
│  负责：用例编排、事务管理、权限检查       │
└────────────────┬────────────────────────┘
                 │ 协调
                 ▼
┌─────────────────────────────────────────┐
│        services/ (业务逻辑层)            │
│  负责：具体业务逻辑实现                   │
└────────────────┬────────────────────────┘
                 │ 使用
                 ▼
┌─────────────────────────────────────────┐
│      infrastructure/ (基础设施层)        │
│  负责：数据库访问、外部 API 调用、文件 IO  │
└─────────────────────────────────────────┘
```

### 各层职责

#### 1. routes/ (接口层)
```python
# ✅ 应该做的
- 接收 HTTP 请求
- 验证请求参数
- 调用 application 层
- 返回 HTTP 响应

# ❌ 不应该做的
- 直接调用 services 层
- 包含业务逻辑
- 直接访问数据库
```

#### 2. application/ (应用服务层) ⭐
```python
# ✅ 应该做的
- 编排多个 services 完成用例
- 处理事务
- 权限检查
- 日志记录
- 事件发布

# ❌ 不应该做的
- 包含核心业务逻辑 (应该在 domain 层)
- 直接访问数据库 (应该通过 ports)
- 依赖具体实现 (应该依赖抽象接口)
```

#### 3. services/ (业务逻辑层)
```python
# ✅ 应该做的
- 实现具体业务逻辑
- 调用 infrastructure 层
- 处理数据转换

# ⚠️ 注意
- 这是临时层，后续会拆分为:
  - domain/services/ (领域服务)
  - infrastructure/ (基础设施)
```

---

## 📝 最佳实践

### 1. 命名规范

```python
# 应用服务类名：XxxAppService
class AuthAppService:
    pass

# 获取函数：get_xxx_app_service
def get_auth_app_service() -> AuthAppService:
    pass

# 方法名：动词 + 名词
auth_app_service.login(username, password)
auth_app_service.logout(session_id)
auth_app_service.change_password(user_id, old, new)
```

### 2. 错误处理

```python
from app.application.auth_app_service import get_auth_app_service

@auth_bp.route("/login", methods=["POST"])
def login():
    auth_app_service = get_auth_app_service()
    result = auth_app_service.login(username, password)
    
    # 应用服务已经处理了错误，直接返回结果
    if not result["success"]:
        return jsonify(result), 401
    
    return jsonify(result)
```

### 3. 依赖注入

```python
# 测试时使用依赖注入
def test_auth_app_service():
    mock_auth = MockAuthService()
    mock_session = MockSessionService()
    
    app_service = AuthAppService(
        auth_service=mock_auth,
        session_service=mock_session
    )
    
    # 运行测试
```

---

## 🧪 测试示例

### 单元测试

```python
import pytest
from unittest.mock import Mock
from app.application.auth_app_service import AuthAppService

def test_login_success():
    # 准备 mock 对象
    mock_auth = Mock()
    mock_auth.authenticate.return_value = {
        "success": True,
        "user": {"id": 1, "username": "test"},
        "session_id": "abc123"
    }
    
    mock_session = Mock()
    
    # 创建应用服务
    app_service = AuthAppService(
        auth_service=mock_auth,
        session_service=mock_session
    )
    
    # 执行测试
    result = app_service.login("test", "password")
    
    # 验证结果
    assert result["success"] is True
    assert result["data"]["user"]["username"] == "test"
```

### 集成测试

```python
def test_login_integration(client):
    response = client.post("/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert "session_id" in data["data"]
```

---

## 🔄 迁移指南

### 从旧 services 迁移到新 application

#### 步骤 1: 创建应用服务包装器

```python
# application/auth_app_service.py
from app.services.auth_service import AuthService

class AuthAppService:
    def __init__(self, auth_service: AuthService = None):
        self._auth_service = auth_service or AuthService()
    
    def login(self, username: str, password: str):
        # 用例编排
        result = self._auth_service.authenticate(username, password)
        # 可以添加额外的逻辑，如日志、事件发布等
        return result
```

#### 步骤 2: 更新 routes 导入

```python
# 旧代码
from app.services.auth_service import get_auth_service

# 新代码
from app.application.auth_app_service import get_auth_app_service
```

#### 步骤 3: 更新调用代码

```python
# 旧代码
auth_service = get_auth_service()
result = auth_service.authenticate(username, password)

# 新代码
auth_app_service = get_auth_app_service()
result = auth_app_service.login(username, password)
```

---

## ❓ 常见问题

### Q1: 为什么不直接使用 services，要加一层 application？

**A**: 
1. **分层清晰**: routes 只关心 HTTP，不关心业务逻辑
2. **易于测试**: 可以 mock application 层测试 routes
3. **用例编排**: 一个用例可能涉及多个 services，application 层负责协调
4. **演进性**: 未来可以方便地替换 services 实现

### Q2: application 层和 services 层有什么区别？

**A**:
- **application 层**: 用例编排，告诉系统"做什么"
- **services 层**: 业务逻辑，告诉系统"怎么做"

例如:
```python
# application 层：编排登录流程
def login(self, username, password):
    user = self._auth.authenticate(username, password)  # 认证
    session = self._session.create(user)  # 创建会话
    self._logger.log_login(user)  # 记录日志
    return {"user": user, "session": session}

# services 层：具体认证逻辑
def authenticate(self, username, password):
    user = db.query(User).filter_by(username=username).first()
    if not user or not check_password(user.password, password):
        return None
    return user
```

### Q3: 所有 services 都需要包装吗？

**A**: 不是。分类处理:
- **应用服务**: 需要包装 (Auth, User, Product 等)
- **领域服务**: 移动到 domain/services/
- **基础设施**: 移动到 infrastructure/
- **工具服务**: 保留 (Skills)

---

## 📚 相关文档

- [DDD 重构计划](ddd-refactoring-plan.md)
- [DDD 重构验证报告](ddd-refactoring-verification.md)
- [DDD 重构总结](DDD_REFACTORING_SUMMARY.md)

---

**最后更新**: 2026-03-21  
**维护者**: XCAGI 开发团队
