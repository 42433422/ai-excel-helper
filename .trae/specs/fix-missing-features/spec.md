# XCAGI 系统功能完善 Spec

## Why
系统自检发现约 30% 的功能未完善或缺失，包括前后端 API 路径不一致、部分 CRUD 操作缺失、原材料管理功能不完整等问题，影响用户体验和系统完整性。

## What Changes
- 修复前后端 API 路径不一致问题
- 完善客户、产品、原材料管理的 CRUD 接口
- 实现标记为"只有框架"的功能
- 补充缺失的数据库表（如需要）
- 完善微信消息刷新功能

**BREAKING**: 部分 API 路径变更可能导致旧的前端调用失败

## Impact
- **Affected specs**: 
  - 客户管理能力
  - 产品管理能力
  - 原材料管理能力
  - 微信消息管理能力
  - Excel 导入导出能力
  - 会话管理能力
- **Affected code**:
  - `app/routes/customers.py`
  - `app/routes/products.py`
  - `app/routes/materials.py`
  - `app/routes/wechat_contacts.py`
  - `app/routes/shipment.py`
  - `app/routes/ai_chat.py`
  - `app/routes/conversations.py`
  - `app/services/*`

## ADDED Requirements

### Requirement: 前后端 API 路径统一
系统 SHALL 确保前端调用的 API 路径与后端路由完全匹配

#### Scenario: 前端调用 AI 聊天接口
- **WHEN** 前端调用 `/api/ai/chat-unified`
- **THEN** 后端能够正确处理请求并返回响应
- **WHEN** 前端调用 `/api/conversations/<sessionId>`
- **THEN** 后端返回会话详情而非消息列表

### Requirement: 客户管理完整 CRUD
系统 SHALL 提供完整的客户资源操作接口

#### Scenario: 创建单个客户
- **WHEN** 用户提交客户信息
- **THEN** 系统创建客户并返回成功响应

#### Scenario: 更新单个客户
- **WHEN** 用户修改客户信息并保存
- **THEN** 系统更新客户信息并返回成功响应

#### Scenario: 删除单个客户
- **WHEN** 用户删除单个客户
- **THEN** 系统删除指定客户并返回成功响应

### Requirement: 产品管理完整 CRUD
系统 SHALL 提供获取单个产品详情的接口

#### Scenario: 获取产品详情
- **WHEN** 用户查看产品详情
- **THEN** 系统返回指定产品的完整信息

### Requirement: 原材料管理完整功能
系统 SHALL 提供完整的原材料 CRUD 操作

#### Scenario: 查询原材料列表
- **WHEN** 用户访问原材料管理页面
- **THEN** 系统显示所有原材料及其库存信息

#### Scenario: 更新原材料
- **WHEN** 用户修改原材料信息
- **THEN** 系统保存修改并返回成功响应

#### Scenario: 低库存预警
- **WHEN** 用户查询低库存原材料
- **THEN** 系统返回库存低于阈值的原材料列表

### Requirement: 微信消息刷新
系统 SHALL 支持从微信数据库拉取消息并保存到上下文

#### Scenario: 刷新联系人消息
- **WHEN** 用户点击刷新消息按钮
- **THEN** 系统从微信数据库拉取最新消息并保存到聊天上下文

## MODIFIED Requirements

### Requirement: 产品导出功能
**原要求**: 产品导出功能只有框架
**修改后**: 系统 SHALL 支持将产品数据导出为 Excel 文件

### Requirement: 产品名称搜索
**原要求**: `/api/products/product_names` 返回空数据
**修改后**: 系统 SHALL 返回所有产品名称列表，支持关键词搜索

### Requirement: 发货单管理功能
**原要求**: 多个功能只有框架
**修改后**: 
- 系统 SHALL 支持清理指定购买单位的出货记录
- 系统 SHALL 支持设置和重置订单序号
- 系统 SHALL 支持更新和删除出货记录
- 系统 SHALL 支持导出出货记录为 Excel

## REMOVED Requirements
无

## Dependencies
- 依赖现有的数据库连接服务
- 依赖现有的服务层架构
- 依赖 Excel 处理服务（用于导出功能）

## Testing Strategy
- 单元测试：为新增的 CRUD 接口编写单元测试
- 集成测试：测试前后端 API 调用
- 手动测试：验证前端界面功能
