# 核心工作流 Mod — 现网验收脚本

> **Mod（房子）**：`xcagi-core-workflow-employees`  
> **员工（家具）**：下表四个 `id`，须全部出现在已安装 Mod 的 `workflow_employees` 中。

前置：FHD 已启动；本 Mod 已同步到 `XCAGI/mods/xcagi-core-workflow-employees/` 并重新加载 Mod；智能对话页可打开副窗。

---

## 1. label_print（标签打印 AI 员工）

1. 副窗打开 **标签打印 AI 员工** 开关（`xcagi_workflow_ai_employees.label_print = true`）。
2. 智能对话勾选 **星标聊天自动刷新**。
3. 用星标联系人发送含「打印」「标签」类话术；或等待轮询命中意图。
4. **期望**：派发 `xcagi:workflow-label-print-signal`；工作流条目推进；对话中可补充型号/张数走打印链路。
5. **API（可选）**：`POST /api/mod/xcagi-core-workflow-employees/employees/label_print/run` body `{"action":"status"}` 返回 `ok: true` 与 `employee_id: label_print`。

---

## 2. shipment_mgmt（出货管理 AI 员工）

1. 副窗打开 **出货管理 AI 员工**。
2. 对话触发生成发货单：预览 → 确认执行 → 写库。
3. 触发 **开始打印**。
4. **期望**：打印成功后工作流展示出货记录审计建议（条数/今日增量类文案）；副窗推送更新。
5. **API（可选）**：`POST .../employees/shipment_mgmt/run` body `{"action":"audit_summary"}` 返回审计占位或宿主出货列表摘要字段。

---

## 3. receipt_confirm（收货确认 AI 员工）

1. 副窗打开 **收货确认 AI 员工**。
2. 保持星标自动刷新；星标联系人发送收货/到货/签收/对账类消息。
3. **期望**：命中后派发 `xcagi:workflow-receipt-feedback-signal`；工作流面板展示客户业务进程摘要。
4. 仅开收货、未开微信时：仍跑星标意图，但不写入「微信消息处理」列表项（与 [workflow-employee-docs.json](E:\XCMAX\FHD\frontend\src\data\workflow-employee-docs.json) 一致）。

---

## 4. wechat_msg（微信消息处理 AI 员工）

1. 副窗打开 **微信消息处理 AI 员工**。
2. 勾选星标自动刷新；等待约 1 分钟轮询。
3. **期望**：有新消息时副窗推送；意图预处理（专业模式可走 `/api/ai/intent/test`，否则本地规则）；派发 `xcagi:wechat-ai-task-enqueue`，右侧出现「微信消息处理 · 联系人」任务。
4. **API（可选）**：`POST .../employees/wechat_msg/run` body `{"action":"status"}`。

---

## Mod 级检查

- `GET /api/mods/` 列表含 `xcagi-core-workflow-employees`，且 `workflow_employees` 长度为 4。
- 未安装本 Mod 时：副窗不显示上述四行（或提示安装核心工作流包）；`wechat_phone` / `real_phone` 固定扩展行不受影响。

---

## Phase 2（解耦调度）补充验收

1. **前端模块**：`frontend/src/workflow/` 下存在 `coreWorkflowDispatcher.ts`、`coreWorkflowMonitor.ts`；`useChatView.ts` 对四名核心员工不再散落 `empId === '…'` 分支（电话员工逻辑仍留在宿主）。
2. **Mod run 与宿主事件链**：安装 Mod 后，星标命中标签/收货信号或微信入队、打印后审计时，浏览器网络面板应出现  
   `POST /api/mod/xcagi-core-workflow-employees/employees/<id>/run`（action 分别为 `signal_ack` / `feedback_ack` / `enqueue_ack` / `audit_summary`）；同时仍应派发原有 `xcagi:workflow-*` / `xcagi:wechat-ai-task-enqueue` 事件（宿主 fallback）。
3. **自动化**：在 `FHD` 根目录执行 `python -m pytest tests/test_core_workflow_mod.py` 全部通过；在 `FHD/frontend` 执行 `npm run test -- src/workflow/coreWorkflowMonitor.test.ts` 通过。
