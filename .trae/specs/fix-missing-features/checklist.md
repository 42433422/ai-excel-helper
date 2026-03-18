# Checklist

## Task 1: 前后端 API 路径统一
- [x] `/api/ai/chat-unified` 路由可正常访问
- [x] `/api/conversations/<session_id>` GET 返回会话详情
- [x] `/api/ai/message/save` 路由可正常访问
- [x] `/api/ai/conversation/new` 路由可正常访问

## Task 2: 客户管理 CRUD
- [x] `POST /api/customers` 可创建客户
- [x] `PUT /api/customers/<id>` 可更新客户
- [x] `DELETE /api/customers/<id>` 可删除客户

## Task 3: 产品管理接口
- [x] `GET /api/products/<id>` 返回产品详情
- [x] `/api/products/product_names` 返回产品名称列表
- [x] `/api/products/product_names/search` 支持搜索
- [x] 产品导出 Excel 功能正常

## Task 4: 原材料管理
- [x] `GET /api/materials` 返回原材料列表
- [x] `PUT /api/materials/<id>` 可更新原材料
- [x] `DELETE /api/materials/<id>` 可删除原材料
- [x] `POST /api/materials/batch-delete` 可批量删除
- [x] `GET /api/materials/low-stock` 返回低库存预警

## Task 5: 微信消息刷新
- [x] `/api/wechat_contacts/<id>/refresh_messages` 可刷新消息

## Task 6: 发货单管理
- [x] 清理出货记录功能正常
- [x] 设置订单序号功能正常
- [x] 重置订单序号功能正常
- [x] 更新出货记录功能正常
- [x] 删除出货记录功能正常
- [x] 导出出货记录功能正常

## Task 7: 产品批量添加
- [x] `/api/products/batch` 可批量添加产品

## Task 8: 工具管理
- [x] database 工具可实际操作数据库
- [x] system 工具可实际执行系统操作

## Task 9: 会话与偏好
- [x] 保存消息功能正常
- [x] 偏好设置功能正常

## 集成测试
- [x] 前端可正常调用所有 API
- [x] 所有 CRUD 操作通过单元测试
- [x] 数据库操作无错误
