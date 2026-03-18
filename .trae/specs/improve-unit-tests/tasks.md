# Tasks

## Phase 1: 测试基础设施增强

- [x] **Task 1: 增强 conftest.py 测试工具**
  - [x] 添加数据库会话 fixture（每个测试自动回滚）
  - [x] 添加外部 API Mock fixture
  - [x] 添加文件系统 Mock fixture
  - [x] 创建测试数据工厂（sample_data_factory）
  - [x] 添加常用的断言辅助函数

- [x] **Task 2: 配置优化**
  - [x] 更新 pytest.ini 设置覆盖率门槛为 80%
  - [x] 添加 pytest-mock 依赖（如未安装）
  - [x] 配置覆盖率报告的排除规则

## Phase 2: 服务层测试（核心业务）

- [x] **Task 3: AI 服务测试** (`test_ai_services.py`)
  - [x] 测试 AIConversationService 的所有方法
  - [x] 测试意图识别逻辑
  - [x] Mock LLM API 调用
  - [x] 测试对话上下文管理

- [x] **Task 4: 产品服务测试增强** (`test_products_service.py`)
  - [x] 测试产品 CRUD 操作
  - [x] 测试批量导入功能
  - [x] 测试搜索和过滤逻辑
  - [x] 测试数据验证和错误处理

- [x] **Task 5: 发货单服务测试** (`test_shipment_service.py`)
  - [x] 测试订单创建流程
  - [x] 测试订单状态管理
  - [x] 测试订单编号生成
  - [x] 测试与产品、客户的关联

- [x] **Task 6: 微信服务测试** (`test_wechat_services.py`)
  - [x] 测试联系人同步功能
  - [x] 测试任务管理功能
  - [x] 测试消息处理逻辑
  - [x] Mock 微信 API 调用

- [x] **Task 7: 客户导入服务测试** (`test_customer_import_service.py`)
  - [x] 测试 Excel 文件解析
  - [x] 测试数据验证和清洗
  - [x] 测试批量导入逻辑
  - [x] 测试错误处理和回滚

- [x] **Task 8: OCR 和打印服务测试** (`test_ocr_printer_services.py`)
  - [x] 测试 OCR 识别功能（Mock）
  - [x] 测试打印机配置管理
  - [x] 测试打印任务队列
  - [x] 测试打印模板渲染

## Phase 3: 工具类测试

- [x] **Task 9: Excel 工具测试** (`test_excel_utils.py`)
  - [x] 测试 Excel 文件读取/写入
  - [x] 测试数据格式转换
  - [x] 测试模板填充功能
  - [x] 测试边界条件和错误处理

- [x] **Task 10: Excel 模板分析器测试** (`test_excel_template_analyzer.py`)
  - [x] 测试模板结构解析
  - [x] 测试字段映射识别
  - [x] 测试模板验证功能
  - [x] 测试多种模板格式

- [x] **Task 11: 路径和日志工具测试** (`test_utils_misc.py`)
  - [x] 测试 path_utils 的路径处理函数
  - [x] 测试 logging_utils 的日志配置
  - [x] 测试 print_utils 的打印辅助函数
  - [x] 测试 printer_automation 的自动化逻辑

## Phase 4: 数据库模型测试

- [x] **Task 12: ORM 模型测试增强** (`test_orm_models.py`)
  - [x] 测试 Product 模型的 CRUD
  - [x] 测试 Customer 模型的验证
  - [x] 测试 Shipment 模型的关系
  - [x] 测试 Wechat 相关模型
  - [x] 测试 Material 模型
  - [x] 测试数据完整性和约束

## Phase 5: 任务模块测试

- [x] **Task 13: Celery 任务测试** (`test_celery_tasks.py`)
  - [x] 测试 shipment_tasks 的异步执行
  - [x] 测试 wechat_tasks 的定时任务
  - [x] Mock Celery 执行环境
  - [x] 测试任务重试和错误处理

## Phase 6: 路由层测试增强

- [x] **Task 14: 路由测试质量提升**
  - [x] 增强 `test_products.py` 的断言（验证返回数据）
  - [x] 增强 `test_customers.py` 的边界测试
  - [x] 增强 `test_shipment.py` 的完整流程测试
  - [x] 增强 `test_wechat.py` 的 Mock 测试
  - [x] 增强 `test_ai_chat.py` 的对话场景测试
  - [x] 为 `test_materials.py` 添加完整测试
  - [x] 为 `test_ocr.py` 添加完整测试
  - [x] 为 `test_print.py` 添加完整测试
  - [x] 为 `test_excel_templates.py` 添加完整测试
  - [x] 为 `test_excel_extract.py` 添加完整测试
  - [x] 为 `test_tools.py` 添加完整测试

## Phase 7: 覆盖率验证和优化

- [ ] **Task 15: 覆盖率检查和优化**
  - [ ] 运行完整测试套件检查覆盖率
  - [ ] 识别覆盖率低的模块
  - [ ] 针对性补充测试用例
  - [ ] 生成 HTML 覆盖率报告
  - [ ] 验证所有模块达到覆盖率目标

---

# Task Dependencies

- **Task 1** 是所有其他任务的基础（提供测试基础设施）
- **Task 2** 需要在 Task 1 完成后进行
- **Task 3-8**（服务层测试）可以并行执行
- **Task 9-11**（工具类测试）可以并行执行
- **Task 12**（ORM 模型测试）可以独立并行执行
- **Task 13**（任务模块测试）依赖于 Task 1 的 Mock 工具
- **Task 14**（路由层增强）可以在 Task 3-8 之后进行（复用服务层测试经验）
- **Task 15** 必须在所有其他任务完成后执行

# 执行顺序建议

1. **Phase 1** (Task 1-2): 测试基础设施 - 1 天
2. **Phase 2** (Task 3-8): 服务层测试 - 3-4 天（可并行）
3. **Phase 3** (Task 9-11): 工具类测试 - 2 天（可并行）
4. **Phase 4** (Task 12): 数据库模型测试 - 1 天
5. **Phase 5** (Task 13): 任务模块测试 - 1 天
6. **Phase 6** (Task 14): 路由层增强 - 2-3 天
7. **Phase 7** (Task 15): 覆盖率验证 - 0.5 天

**预计总时间**: 10-12 天（并行执行可缩短至 6-7 天）
