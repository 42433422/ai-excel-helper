# 阶段 3d：Planner 对话门面 Mod

## Mod（房子）

- id：`xcagi-planner-bridge`
- 安装：`mods/xcagi-planner-bridge/`

## 对外 API（与宿主等价）

| Mod 门面 | 宿主（兼容保留） |
|----------|------------------|
| `POST /api/mod/xcagi-planner-bridge/chat` | `POST /api/ai/chat` |
| `POST .../chat/stream` | `POST /api/ai/chat/stream` |
| `POST .../chat/batch` | `POST /api/ai/chat/batch` |
| `POST .../unified_chat` | `POST /api/ai/unified_chat` |
| `POST .../intent/test` | `POST /api/ai/intent/test` |
| `GET .../tools/registry` | Planner 工具清单（含 Mod 扩展项） |
| `POST .../tools/execute` | 里程碑 B/F4：工具执行门面（Mod native 优先，宿主 fallback） |

请求体与响应契约与 `XcagiCompatChatBody` 一致。

## 执行链

```
前端 chatApi → Mod 路由 → app.mod_sdk.planner_compat → app.application.planner_compat_service → legacy_chat_adapter
```

## 前端切换

- 检测到已安装 `xcagi-planner-bridge` 时，`localStorage.xcagi_planner_mod_facade_enabled=1`
- `resolvePlannerChatPath()` 等见 `@/utils/plannerChatPaths`
- 关闭门面：清除上述 localStorage 或卸载 Mod

## 验收

1. `GET /api/mod/xcagi-planner-bridge/status` → `role: planner_facade`
2. 安装 Mod 后发一条智能对话，网络面板应走 `/api/mod/xcagi-planner-bridge/chat` 或 `/chat/stream`
3. 卸载 Mod 并刷新 → 回退 `/api/ai/chat`

## 里程碑 B（工具插件化边界）

- `manifest.config.planner_tools_execution: true`
- `config/planner_tools.json` 声明 `host_delegated_tools` 与门面端点
- 对话链 `legacy_chat_adapter` 经 `app.mod_sdk.planner_tools.resolve_planner_tool_executor`
- 强制门面：`XCAGI_PLANNER_TOOLS_VIA_MOD=1`；关闭：`XCAGI_DISABLE_PLANNER_MOD_TOOLS=1`

## 里程碑 F（原生工具 handler）

| Mod | 工具 |
|-----|------|
| `xcagi-planner-excel-tools` | 见下表 |

| 工具 | F 阶段 | 说明 |
|------|--------|------|
| `excel_chart_recommend` | F | Mod 内纯逻辑 |
| `excel_schema_understand` | F | Mod handler + 宿主 schema 服务 |
| `excel_analysis` | F2 | Mod 包装 `handle_excel_analysis` |
| `excel_join_compare` | F2 | Mod 内 join/diff 实现 |
| `import_excel_to_database` | F3 | Mod 包装 `_handle_import_excel_to_database` |
| `generate_office_document` | F3 | Mod 内编排 kitten 文档生成 |
| `products_bulk_import` | F4 | Mod + `run_bulk_import`（需 `FHD_DB_WRITE_TOKEN`） |
| `excel_vector_index` | F4 | Mod + `ExcelVectorIngestApplicationService.ingest_excel` |

分派链：`execute_workflow_tool` → `planner_native_tools` → Mod `tool_handlers.py`；未安装 Mod 或禁用时走宿主 `workflow` 同名分支（含 `excel_vector_index` 宿主 fallback，修复此前 `unknown_tool`）。

`planner_tools.json`：`host_delegated_tools` 仅剩 `excel_prophet`（未迁移项）。

环境变量：`XCAGI_PLANNER_NATIVE_TOOLS=1` / `XCAGI_DISABLE_PLANNER_NATIVE_TOOLS=1`
