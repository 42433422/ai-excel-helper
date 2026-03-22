# XCAGI HTML vs Vue 模块对照表

本文用于标记同功能在旧版 HTML 与新版 Vue 中的实现位置，并给出当前迁移状态。

状态定义：
- `vue`：主要交互与数据流在 Vue 组件内完成。
- `hybrid`：Vue 与 legacy JS 并行，存在双绑定或互相调用。
- `legacy`：Vue 仅提供结构壳，主要逻辑仍由 legacy JS 驱动。

| 功能模块 | Vue 位置 | HTML / Legacy 位置 | 状态 |
| --- | --- | --- | --- |
| 全局布局与导航 | `frontend/src/App.vue` `frontend/src/components/MainLayout.vue` `frontend/src/components/Sidebar.vue` | `templates/ai_assistant_console.html` + `static/js/modules/ui.js`(`switchView`) | hybrid |
| 智能对话(Chat) | `frontend/src/views/ChatView.vue` `frontend/src/api/chat.js` | `templates/ai_assistant_console.html` + `static/js/modules/chat.js` | hybrid |
| 工具表(Tools) | `frontend/src/views/ToolsView.vue` | `templates/ai_assistant_console.html` + `static/js/modules/tools.js` | hybrid |
| 出货单记录(Orders) | `frontend/src/views/OrdersView.vue` | `templates/ai_assistant_console.html` + `static/js/modules/orders.js` | legacy |
| 出货记录(ShipmentRecords) | `frontend/src/views/ShipmentRecordsView.vue` | `templates/ai_assistant_console.html` + `static/js/modules/shipment-records.js` | legacy |
| 微信联系人(WechatContacts) | `frontend/src/views/WechatContactsView.vue` | `templates/ai_assistant_console.html` + `static/js/modules/wechat_contacts.js` | legacy |
| 标签打印(Print) | `frontend/src/views/PrintView.vue` | `templates/ai_assistant_console.html` + `static/js/modules/ui.js` `static/js/modules/chat.js` | legacy |
| 系统设置(Settings) | `frontend/src/views/SettingsView.vue` | `templates/ai_assistant_console.html` + `static/js/modules/ui.js` | legacy |
| 产品管理(Products) | `frontend/src/views/ProductsView.vue` `frontend/src/api/products.js` | `templates/ai_assistant_console.html` + `static/js/modules/products.js` | hybrid |
| 原材料(Materials) | `frontend/src/views/MaterialsView.vue` `frontend/src/api/materials.js` | `templates/ai_assistant_console.html` + `static/js/modules/materials.js` | hybrid |
| 客户(Customers) | `frontend/src/views/CustomersView.vue` `frontend/src/api/customers.js` | `templates/ai_assistant_console.html` + `static/js/modules/customers.js` | hybrid |
| 专业模式(ProMode) | `frontend/src/components/ProMode.vue` | `templates/ai_assistant_console.html` + `static/js/modules/pro-mode.js` | hybrid |
| 导入与上传(FileImport) | `frontend/src/components/FileImport.vue`(组件存在，未作为主流程承载) | `templates/ai_assistant_console.html` + `static/js/modules/file-import.js` | legacy |

## 高优先迁移目标（本轮）

1. `orders`
2. `shipment-records`
3. `wechat-contacts`
4. `print`
5. `settings`
6. `chat/tools` 去除双绑定

## 依赖说明

- Vue 页面目前仍通过 `frontend/index.html` 注入 legacy 脚本：
  - `core/config.js`
  - `core/utils.js`
  - `modules/ui.js`
  - `modules/chat.js`
  - `modules/products.js`
  - `modules/materials.js`
  - `modules/orders.js`
  - `modules/shipment-records.js`
  - `modules/customers.js`
  - `modules/wechat_contacts.js`
  - `modules/tools.js`
  - `modules/file-import.js`
  - `modules/wechat.js`
  - `pro_feature_widget.js`
  - `modules/pro-mode.js`

后续迁移将按模块逐步移除对应注入，避免一次性切断导致功能回退。
