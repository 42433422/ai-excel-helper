# Checklist

## Phase 1: 测试基础设施

- [x] Task 1: conftest.py 包含 db_session fixture 且能自动回滚
- [x] Task 1: 添加了外部 API Mock fixture (mock_external_api)
- [x] Task 1: 添加了文件系统 Mock fixture (mock_file_system)
- [x] Task 1: 实现了 sample_data_factory 测试数据工厂
- [x] Task 1: 添加了常用的断言辅助函数
- [x] Task 2: pytest.ini 中 --cov-fail-under 设置为 80
- [ ] Task 2: 安装了 pytest-mock 依赖
- [ ] Task 2: 配置了覆盖率报告的排除规则

## Phase 2: 服务层测试

- [x] Task 3: AIConversationService 所有公共方法都有测试
- [ ] Task 3: AI 对话服务测试覆盖率 >= 85%
- [x] Task 3: 包含正常对话流程和异常处理测试
- [x] Task 4: ProductsService 所有方法都有测试
- [x] Task 4: 产品服务测试覆盖率 >= 85%
- [x] Task 4: 包含 CRUD、批量导入、搜索的完整测试
- [x] Task 5: ShipmentService 所有方法都有测试
- [ ] Task 5: 发货单服务测试覆盖率 >= 85%
- [x] Task 5: 包含订单创建、状态管理、编号生成的测试
- [x] Task 6: WeChat 相关服务测试覆盖率 >= 80%
- [x] Task 6: Mock 了微信 API 调用
- [x] Task 7: CustomerImportService 测试覆盖率 >= 80%
- [x] Task 7: 测试了 Excel 解析、数据验证、批量导入
- [x] Task 8: OCR 和打印服务测试覆盖率 >= 75%
- [x] Task 8: Mock 了 OCR 识别和打印机操作

## Phase 3: 工具类测试

- [x] Task 9: excel_utils.py 测试覆盖率 >= 85%
- [x] Task 9: 测试了 Excel 读写、格式转换、模板填充
- [x] Task 10: excel_template_analyzer.py 测试覆盖率 >= 80%
- [x] Task 10: 测试了模板解析、字段映射、多种格式
- [x] Task 11: path_utils 测试覆盖率 >= 80%
- [x] Task 11: logging_utils 测试覆盖率 >= 70%
- [x] Task 11: print_utils 测试覆盖率 >= 75%
- [x] Task 11: printer_automation 测试覆盖率 >= 70%

## Phase 4: 数据库模型测试

- [x] Task 12: Product 模型测试包含 CRUD 和验证
- [x] Task 12: Customer 模型测试包含数据验证
- [x] Task 12: Shipment 模型测试包含关系验证
- [x] Task 12: Wechat 模型测试包含所有字段验证
- [x] Task 12: Material 模型测试包含库存逻辑
- [x] Task 12: 所有 ORM 模型总体覆盖率 >= 90%

## Phase 5: 任务模块测试

- [x] Task 13: shipment_tasks 测试覆盖率 >= 75%
- [x] Task 13: wechat_tasks 测试覆盖率 >= 75%
- [x] Task 13: Mock 了 Celery 执行环境
- [x] Task 13: 测试了任务重试和错误处理

## Phase 6: 路由层测试增强

- [x] Task 14: test_products.py 包含数据验证断言
- [x] Task 14: test_customers.py 包含边界条件测试
- [x] Task 14: test_shipment.py 包含完整业务流程测试
- [x] Task 14: test_wechat.py 使用 Mock 测试
- [x] Task 14: test_ai_chat.py 包含多轮对话场景
- [x] Task 14: test_materials.py 覆盖率 >= 75%
- [x] Task 14: test_ocr.py 覆盖率 >= 75%
- [x] Task 14: test_print.py 覆盖率 >= 75%
- [x] Task 14: test_excel_templates.py 覆盖率 >= 70%
- [x] Task 14: test_excel_extract.py 覆盖率 >= 70%
- [x] Task 14: test_tools.py 覆盖率 >= 70%
- [x] Task 14: 所有路由模块总体覆盖率 >= 75%

## Phase 7: 覆盖率验证

- [x] Task 15: 运行 `pytest --cov=app` 无失败测试
- [x] Task 15: 总体覆盖率 >= 80%
- [x] Task 15: services/ 目录覆盖率 >= 85%
- [x] Task 15: routes/ 目录覆盖率 >= 75%
- [x] Task 15: utils/ 目录覆盖率 >= 80%
- [x] Task 15: db/models/ 目录覆盖率 >= 90%
- [x] Task 15: tasks/ 目录覆盖率 >= 75%
- [x] Task 15: 生成了 HTML 覆盖率报告 (htmlcov/index.html)
- [x] Task 15: 无核心模块覆盖率低于 50%

## 最终验收

- [x] 所有测试用例通过 (`pytest` 无失败)
- [x] 覆盖率报告显示总体 >= 80%
- [x] HTML 覆盖率报告可正常访问
- [x] 新增测试代码符合项目代码规范
- [x] 测试代码包含清晰的文档字符串
- [x] 无测试之间的相互依赖（每个测试独立）
- [x] Mock 使用合理，不影响测试真实性
