# Tasks

- [x] Task 1: 创建系统架构设计文档 (architecture.md) ✅
  - [x] SubTask 1.1: 编写概述部分（项目背景、技术选型、系统目标） ✅
  - [x] SubTask 1.2: 绘制整体架构图（使用 Mermaid） ✅
  - [x] SubTask 1.3: 编写后端架构说明（Flask 应用工厂、蓝图路由、服务层、数据访问层） ✅
  - [x] SubTask 1.4: 编写前端架构说明（Vue 3、组件化、状态管理、路由） ✅
  - [x] SubTask 1.5: 编写异步任务架构（Celery、Redis Broker） ✅
  - [x] SubTask 1.6: 编写数据流说明（请求处理、任务调度、数据库操作） ✅
  - [x] SubTask 1.7: 编写部署架构（开发/生产环境配置） ✅

- [x] Task 2: 创建数据库 ER 图文档 (database-er.md) ✅
  - [x] SubTask 2.1: 编写数据库概述（SQLite、文件位置、Alembic 迁移） ✅
  - [x] SubTask 2.2: 整理所有数据表结构（users, sessions, products, shipment_records, wechat_contacts, wechat_tasks, ai_* 等） ✅
  - [x] SubTask 2.3: 绘制 Mermaid ER 关系图 ✅
  - [x] SubTask 2.4: 编写索引设计说明 ✅
  - [x] SubTask 2.5: 编写数据字典（字段说明、约束条件） ✅

- [x] Task 3: 创建开发规范指南 (development-guide.md) ✅
  - [x] SubTask 3.1: 编写代码风格规范（Python PEP8、Vue 组件规范） ✅
  - [x] SubTask 3.2: 编写命名规范（变量、函数、类、文件） ✅
  - [x] SubTask 3.3: 编写 Git 规范（分支策略、Commit Message 格式） ✅
  - [x] SubTask 3.4: 编写测试规范（单元测试、集成测试、覆盖率目标） ✅
  - [x] SubTask 3.5: 编写日志规范（级别、格式、管理） ✅
  - [x] SubTask 3.6: 编写 API 设计规范（RESTful、错误处理、Swagger） ✅
  - [x] SubTask 3.7: 编写性能优化指南（数据库、缓存、前端） ✅

- [x] Task 4: 创建故障排查手册 (troubleshooting-guide.md) ✅
  - [x] SubTask 4.1: 编写排查基础（日志位置、调试工具、监控指标） ✅
  - [x] SubTask 4.2: 整理常见问题（数据库、缓存、异步任务、前端、API） ✅
  - [x] SubTask 4.3: 编写性能问题排查（慢查询、内存泄漏、接口响应慢） ✅
  - [x] SubTask 4.4: 整理典型错误及解决方案 ✅
  - [x] SubTask 4.5: 编写应急处理流程（回滚、数据恢复、服务重启） ✅

# Task Dependencies

- Task 2 依赖 Task 1（需要先理解整体架构才能编写 ER 图）
- Task 3 依赖 Task 1（需要理解架构才能制定开发规范）
- Task 4 依赖 Task 1 和 Task 2（需要理解架构和数据库才能编写排查手册）

# Implementation Notes

## 优先级
1. 系统架构设计文档（最高优先级，其他文档的基础）
2. 数据库 ER 图（重要，帮助理解数据结构）
3. 开发规范指南（重要，统一开发标准）
4. 故障排查手册（重要，提高问题处理效率）

## 文档格式要求
- 使用 Markdown 格式
- 使用 Mermaid 绘制图表
- 包含代码示例
- 使用中文编写
- 结构清晰，层次分明

## 验证方法
- 文档语法检查（Markdown 格式正确）
- Mermaid 图表可正常渲染
- 内容准确性（与实际代码一致）
- 完整性检查（覆盖所有要求的模块）
