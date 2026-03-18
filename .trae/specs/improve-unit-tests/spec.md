# 完善单元测试 Spec

## Why
当前项目单元测试覆盖率仅为 30.33%，多个关键模块覆盖率极低或为零测试。需要系统性地完善单元测试，提高代码质量和可维护性，确保功能稳定性和回归测试能力。

## What Changes
- **新增测试模块**：为未测试的核心服务、工具类、数据库模型添加完整的单元测试
- **增强现有测试**：改进现有测试用例的断言质量，从简单的状态码检查升级为完整的功能验证
- **添加 Mock 测试**：为外部依赖（数据库、文件系统、第三方 API）添加 Mock 支持
- **提高覆盖率目标**：将整体覆盖率从 30.33% 提升至 80%+
- **改进测试工具**：增强 conftest.py 中的 fixtures，提供更多测试辅助功能

## Impact
- **受影响的服务**：所有服务层模块（services/）、工具模块（utils/）、任务模块（tasks/）
- **受影响的代码**：测试目录结构（tests/）、测试配置（pytest.ini）
- **测试框架**：pytest, pytest-cov, pytest-mock

## 核心 Requirements

### Requirement: 服务层测试
系统 SHALL 为所有服务类提供完整的单元测试：
- `ai_conversation_service.py` - AI 对话服务
- `customer_import_service.py` - 客户导入服务
- `intent_service.py` - 意图识别服务
- `ocr_service.py` - OCR 识别服务
- `printer_service.py` - 打印机服务
- `products_service.py` - 产品服务
- `shipment_service.py` - 发货单服务
- `wechat_contact_service.py` - 微信联系人服务
- `wechat_task_service.py` - 微信任务服务

#### Scenario: 服务层测试成功
- **WHEN** 运行服务层测试
- **THEN** 所有服务方法的覆盖率 >= 85%
- **AND** 包含正常流程和异常流程的测试用例

### Requirement: 工具类测试
系统 SHALL 为所有工具函数提供单元测试：
- `excel_utils.py` - Excel 处理工具
- `excel_template_analyzer.py` - Excel 模板分析器
- `logging_utils.py` - 日志工具
- `path_utils.py` - 路径工具
- `print_utils.py` - 打印工具
- `printer_automation.py` - 打印机自动化

#### Scenario: 工具类测试成功
- **WHEN** 运行工具类测试
- **THEN** 所有工具函数的覆盖率 >= 80%
- **AND** 包含边界条件和错误处理的测试

### Requirement: 数据库模型测试
系统 SHALL 为所有 ORM 模型提供测试：
- 模型的 CRUD 操作
- 模型关系验证
- 数据验证和约束

#### Scenario: 模型测试成功
- **WHEN** 运行数据库模型测试
- **THEN** 所有模型的覆盖率 >= 90%
- **AND** 验证数据完整性和约束

### Requirement: 任务模块测试
系统 SHALL 为 Celery 任务提供测试：
- `shipment_tasks.py` - 发货单异步任务
- `wechat_tasks.py` - 微信异步任务

#### Scenario: 任务测试成功
- **WHEN** 运行任务模块测试
- **THEN** 所有任务的覆盖率 >= 75%
- **AND** 验证异步执行和错误处理

### Requirement: 路由层测试增强
系统 SHALL 改进现有路由测试的质量：
- 从简单的状态码检查升级为完整的功能验证
- 添加请求/响应数据的详细断言
- 测试边界条件和错误场景

#### Scenario: 路由测试增强成功
- **WHEN** 运行路由层测试
- **THEN** 所有路由的覆盖率 >= 75%
- **AND** 包含完整的业务逻辑验证

### Requirement: 覆盖率目标
系统 SHALL 达到以下覆盖率指标：
- 整体行覆盖率 >= 80%
- 核心业务模块（services/）覆盖率 >= 85%
- 路由模块（routes/）覆盖率 >= 75%
- 工具模块（utils/）覆盖率 >= 80%

#### Scenario: 覆盖率检查成功
- **WHEN** 运行 `pytest --cov=app`
- **THEN** 总体覆盖率显示 >= 80%
- **AND** 无覆盖率低于 50% 的核心模块

## MODIFIED Requirements

### Requirement: 测试配置
修改 `pytest.ini` 中的覆盖率要求：
```ini
[pytest]
addopts = -v --tb=short --cov=app --cov-report=term-missing --cov-report=html --cov-fail-under=80
```

**原因**：设置最低覆盖率门槛，确保新增代码不会降低整体覆盖率

### Requirement: 测试工具增强
增强 `conftest.py` 提供更多 fixtures：
- `db_session` - 独立的数据库会话（每个测试回滚）
- `mock_external_api` - Mock 外部 API 调用
- `mock_file_system` - Mock 文件系统操作
- `sample_data_factory` - 测试数据工厂

**原因**：提供更好的测试基础设施，简化测试编写

## REMOVED Requirements

无

## 测试策略

### 1. 单元测试优先
- 每个服务方法至少一个测试用例
- 测试正常流程、边界条件、异常情况
- 使用 Mock 隔离外部依赖

### 2. 分层测试
- **单元测试**：测试单个函数/方法
- **集成测试**：测试模块间交互
- **端到端测试**：测试完整业务流程

### 3. 测试数据管理
- 使用 fixtures 提供测试数据
- 测试数据与测试用例分离
- 每个测试独立，不相互依赖

### 4. Mock 策略
- Mock 数据库操作（避免污染生产数据）
- Mock 文件系统（避免 IO 依赖）
- Mock 第三方 API（避免网络依赖）

## 验收标准

1. ✅ 运行 `pytest --cov=app` 显示总体覆盖率 >= 80%
2. ✅ 所有核心服务模块覆盖率 >= 85%
3. ✅ 所有路由模块覆盖率 >= 75%
4. ✅ 所有工具模块覆盖率 >= 80%
5. ✅ 数据库模型覆盖率 >= 90%
6. ✅ 任务模块覆盖率 >= 75%
7. ✅ 所有测试用例通过（无失败）
8. ✅ HTML 覆盖率报告清晰展示各模块覆盖情况
