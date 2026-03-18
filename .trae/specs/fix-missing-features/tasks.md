# Tasks

- [x] Task 1: 修复前后端 API 路径不一致
  - [x] Subtask 1.1: 添加 `/api/ai/chat-unified` 路由（兼容旧版）
  - [x] Subtask 1.2: 修改 `/api/conversations/<session_id>` 支持 GET 获取会话详情
  - [x] Subtask 1.3: 添加 `/api/ai/message/save` 路由（兼容旧版）
  - [x] Subtask 1.4: 添加 `/api/ai/conversation/new` 路由

- [x] Task 2: 完善客户管理 CRUD 接口
  - [x] Subtask 2.1: 添加 `POST /api/customers` 创建单个客户
  - [x] Subtask 2.2: 添加 `PUT /api/customers/<id>` 更新单个客户
  - [x] Subtask 2.3: 添加 `DELETE /api/customers/<id>` 删除单个客户

- [x] Task 3: 完善产品管理接口
  - [x] Subtask 3.1: 添加 `GET /api/products/<id>` 获取单个产品详情
  - [x] Subtask 3.2: 实现 `/api/products/product_names` 返回产品名称列表
  - [x] Subtask 3.3: 实现 `/api/products/product_names/search` 搜索产品名称
  - [x] Subtask 3.4: 实现产品导出 Excel 功能

- [x] Task 4: 完善原材料管理功能
  - [x] Subtask 4.1: 实现 `GET /api/materials` 从数据库查询原材料列表
  - [x] Subtask 4.2: 实现 `PUT /api/materials/<id>` 更新原材料
  - [x] Subtask 4.3: 实现 `DELETE /api/materials/<id>` 删除原材料
  - [x] Subtask 4.4: 实现 `POST /api/materials/batch-delete` 批量删除
  - [x] Subtask 4.5: 实现 `GET /api/materials/low-stock` 低库存查询

- [x] Task 5: 完善微信联系人功能
  - [x] Subtask 5.1: 实现 `/api/wechat_contacts/<id>/refresh_messages` 刷新消息功能

- [x] Task 6: 完善发货单管理功能
  - [x] Subtask 6.1: 实现清理指定购买单位的出货记录功能
  - [x] Subtask 6.2: 实现设置订单序号功能
  - [x] Subtask 6.3: 实现重置订单序号功能
  - [x] Subtask 6.4: 实现更新出货记录功能
  - [x] Subtask 6.5: 实现删除出货记录功能
  - [x] Subtask 6.6: 实现导出出货记录功能

- [x] Task 7: 完善产品批量添加功能
  - [x] Subtask 7.1: 实现 `/api/products/batch` 批量添加产品

- [x] Task 8: 完善工具管理功能
  - [x] Subtask 8.1: 完善 database 工具的实际操作逻辑
  - [x] Subtask 8.2: 完善 system 工具的实际操作逻辑

- [x] Task 9: 完善会话与偏好功能
  - [x] Subtask 9.1: 完善 `/api/conversations/message` 保存消息功能
  - [x] Subtask 9.2: 完善 `/api/preferences` 偏好设置功能

# Task Dependencies
- Task 1 独立，可并行执行
- Task 2-3 依赖现有服务层，可并行执行
- Task 4 依赖原材料服务层，可独立执行
- Task 5 依赖微信服务层，可独立执行
- Task 6 依赖发货单服务层，可独立执行
- Task 7-9 依赖现有架构，可并行执行
