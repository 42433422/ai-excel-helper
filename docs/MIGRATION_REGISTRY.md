# 迁移总登记册（Migration Registry）

> **用途**：一条目录看清「迁了什么、权威代码在哪、旧物在哪、还能不能动」。  
> **维护**：新增/完成一条迁移时，更新下文 **§1 总览表** 与 **§5 待办**；细节仍写在专题报告里，本文件只登记与链接。

---

## 结论（给管理者）


| 项目                                     | 说明                                                                                                                                                                                                                    |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **唯一推荐 HTTP 入口**                       | `XCAGI/run.py` → `**app.fastapi_app:get_fastapi_app`**（`factory=True`），默认 `**http://127.0.0.1:5000**`                                                                                                                 |
| **OpenAPI**                            | `/docs`、`/redoc`                                                                                                                                                                                                      |
| **新功能 / 新接口**                          | 在仓库根 `**app/`** 下扩展（路由全部挂在 `**app/fastapi_routes/`**,由 `register_all_routes` 统一注册）                                                                                                                                  |
| **根目录 `backend/http_app.py`（常见 8000）** | **已删除**(2026-04-20,随 `backend/` 一同下线);备份见 `.archive/legacy-backend-2026-04-final/`                                                                                                                                    |
| **根目录 `backend/` Python 包**            | **已删除**(2026-04-20 全量迁出);路由迁至 `app/fastapi_routes/`,支持模块迁至 `app/legacy/` 与 `app/shell/`,详见本登记册 §5                                                                                                                     |
| **根目录 Flask `app/routes/`**            | **已删除**，备份在 `.archive/flask-routes-2026-04/`                                                                                                                                                                          |
| **环境变量模板**                             | 仓库根 `**[.env.example](../.env.example)`**（端口、数据库、LLM、Neuro、Mods 等默认值与说明）                                                                                                                                              |
| `**XCAGI/app` 与根 `app/**`              | 权威代码仅在仓库根 `**app/**`；本地可用 `[scripts/ensure_xcagi_app_link.ps1](../scripts/ensure_xcagi_app_link.ps1)` / `[.sh](../scripts/ensure_xcagi_app_link.sh)` 在 `XCAGI/` 下生成指向 `../app` 的链接（已被 `XCAGI/.gitignore` 的 `/app` 忽略） |
| **Alembic**                            | 单一迁移链：仓库根 `**alembic/versions/`**；`XCAGI/alembic.ini` 的 `script_location` 指向 `**../alembic**`；当前 `**alembic heads**` 应为 `**xcagi_v5_approval_system**`                                                                |


---

## 1. 迁移条线总览


| 条线                                           | 状态                                           | 权威落点                                                                                                         | 遗留 / 归档                                                                                   | 详细文档                                                                                                                                                |
| -------------------------------------------- | -------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| **A. 主 API 入口统一**（`backend/http_app` → 主栈）   | **已完成**(2026-04-20 `backend/` 目录整体删除)        | `**XCAGI/run.py`**、仓库根 `**app/fastapi_app.py**`、`**app/fastapi_routes/**`、`**app/legacy/**`、`**app/shell/**` | 备份见 `[.archive/legacy-backend-2026-04-final/](../.archive/legacy-backend-2026-04-final/)` | 本登记册 §5                                                                                                                                             |
| **B. Flask 路由拆除**（`app/routes` → FastAPI）    | **已完成**（目录已删，已归档）                            | `**app/fastapi_routes/`**                                                                                    | `.archive/flask-routes-2026-04/`                                                          | `[MIGRATION_CLEANUP_COMPLETE.md](reports/_completed/MIGRATION_CLEANUP_COMPLETE.md)`、`[FLASK_TO_FASTAPI_MIGRATION_FINAL.md](reports/_completed/FLASK_TO_FASTAPI_MIGRATION_FINAL.md)` |
| **C. Neuro-DDD 接入**（事件/领域/服务instrumentation） | 报告声明 Routes+Services 等范围已完成；路线图保留「质量定义」      | `**app/domain/`**、`**app/application/**`、`**app/infrastructure/**`、`**app/neuro_bus/**`                      | 评估/路线图文档                                                                                  | `[NEURO_MIGRATION_FINAL_COMPLETE.md](../NEURO_MIGRATION_FINAL_COMPLETE.md)`、`[NEURO_MIGRATION_ROADMAP.md](../NEURO_MIGRATION_ROADMAP.md)`           |
| **D. 数据库 schema（Alembic）**                   | 指南随子工程维护                                     | `XCAGI/` 与仓库根各自指南                                                                                            | —                                                                                         | `[ALEMBIC_MIGRATION_GUIDE.md](../ALEMBIC_MIGRATION_GUIDE.md)`、`[XCAGI/ALEMBIC_MIGRATION_GUIDE.md](../XCAGI/ALEMBIC_MIGRATION_GUIDE.md)`             |
| **E. 前端 dev 端口 / API 基址**                    | 已统一到后端 5000 叙事；**唯一前端根**为仓库根 `**frontend/`** | `**frontend/vite.config.js**`、`**frontend/.env.example**`                                                    | 历史副本：`.archive/xcagi-frontend-dup-2026-04/frontend`                                       | `[FRONTEND_PORT_MIGRATION.md](FRONTEND_PORT_MIGRATION.md)`、`[XCAGI/FRONTEND.md](../XCAGI/FRONTEND.md)`                                              |


**说明**:条线 A 的「端点级别」清单以本登记册 §5 与 OpenAPI(`/docs`)为准。历史的 `backend/DEPRECATED.md`、`backend/INVENTORY.md`、`backend/MIGRATION_SUMMARY.md` 已随目录下线归档至 [.archive/legacy-backend-2026-04-final/](../.archive/legacy-backend-2026-04-final/)。

---

## 2. 归档与只读目录（勿当生产依赖）


| 路径                                             | 内容                                             |
| ---------------------------------------------- | ---------------------------------------------- |
| `.archive/flask-routes-2026-04/`               | 原 Flask 蓝图路由备份                                 |
| `.archive/flask-app-factory-2026-04/` 等        | 应用工厂 / 控制路由等历史备份（见各 `FLASK_TO_FASTAPI_*` 报告）   |
| `.archive/legacy-backend-2026-04/`             | 旧后端片段备份(早期)                                         |
| `.archive/legacy-backend-2026-04-final/`       | **2026-04-20 `backend/` 全目录下线最终备份**(`DEPRECATED.md`、`INVENTORY.md`、`MIGRATION_SUMMARY.md`、`__init__.py`) |
| `.archive/xcagi-frontend-dup-2026-04/frontend` | 原 `XCAGI/frontend/` 重复副本（权威代码在仓库根 `frontend/`） |


---

## 3. 维护公约（简短）

1. **新代码**：后端与共享 `**app/`** 包在**仓库根**维护；`**XCAGI/`** 为子工程入口（`run.py`）、Docker 上下文、`mods/` 等。禁止新建「第二套」`app/` 目录。
2. **禁止**:新建 `backend/` 目录或恢复已删 Flask 目录。
3. **文档**:入口与迁移状态以 **本登记册** 为唯一索引;专题报告只补充细节,不重复造「唯一真相」。
4. **验收**：合并迁移相关 PR 时，至少更新 **§1 / §5** 中对应行。

---

## 4. 专题报告索引（按文件名）

**Flask / FastAPI 与清理**

-- `reports/_completed/MIGRATION_CLEANUP_COMPLETE.md`
-- `reports/_completed/FLASK_TO_FASTAPI_MIGRATION_COMPLETE.md`
-- `reports/_completed/FLASK_TO_FASTAPI_MIGRATION_FINAL.md`

**Neuro-DDD**

-- `reports/_completed/NEURO_MIGRATION_FINAL_COMPLETE.md`
-- `NEURO_MIGRATION_ROADMAP.md`
-- `reports/_completed/NEURO_CORE_MIGRATION_COMPLETE.md`
-- `reports/_completed/NEURO_MIGRATION_COMPLETE_SUMMARY.md`
-- `reports/_completed/NEURO_MIGRATION_EXECUTION_SUMMARY.md`
-- `reports/_completed/NEURO_MIGRATION_EXECUTION_REPORT.md`
- `NEURO_DDD_MIGRATION_COMPLETE_DEFINITION.md`
- `NEURO_DDD_MIGRATION_ASSESSMENT.md`

**数据库**

- `ALEMBIC_MIGRATION_GUIDE.md`
- `XCAGI/ALEMBIC_MIGRATION_GUIDE.md`

**其他**

- `docs/FRONTEND_PORT_MIGRATION.md`（原端口迁移记录；含归档路径说明）
- `NEURO_OPERATIONS.md`（运维与自检入口，含 `GET /api/neuro/migration-smoke` 等）

**专项（子项目迁入 XCAGI）**

- `docs/migration_report.md`（例：原「AI 助手」Excel 等能力并入 XCAGI 的记录）

---

## 5. `backend/` → `app/` 全量迁移(2026-04-20 **已完成**)

**状态**:阶段 0–5 全部落地,`backend/` 目录已物理删除,备份保留在
[.archive/legacy-backend-2026-04-final/](../.archive/legacy-backend-2026-04-final/)
(含 `DEPRECATED.md`、`INVENTORY.md`、`MIGRATION_SUMMARY.md`、`__init__.py`)。
路由注册与支持模块均以 `app/` 为权威落点,FastAPI 启动冒烟通过(535 条路由)。

### 5.1 路由迁移清单(22 + `template_api`)


| 源(`backend/routers/*.py`)           | 体积     | 目标(`app/fastapi_routes/*.py`)                  | 阶段  | 状态  |
| ----------------------------------- | ------ | ---------------------------------------------- | --- | --- |
| `fhd_meta.py`                       | 868 B  | `app/fastapi_routes/fhd_meta.py`               | 2   | 已完成 |
| `debug_client_log_compat.py`        | 708 B  | `app/fastapi_routes/debug_client_log.py`       | 2   | 已完成 |
| `xcagi_startup.py`                  | 521 B  | `app/fastapi_routes/xcagi_startup.py`          | 2   | 已完成 |
| `document_templates.py`             | 961 B  | `app/fastapi_routes/document_templates.py`     | 2   | 已完成 |
| `state_compat.py`                   | 1.9 KB | `app/fastapi_routes/state.py`                  | 2   | 已完成 |
| `archive_explicit_proxy_routes.py`  | 2.0 KB | `app/fastapi_routes/archive_explicit_proxy.py` | 2   | 已完成 |
| `health_k8s.py`                     | 3.0 KB | `app/fastapi_routes/health_k8s.py`             | 2   | 已完成 |
| `upload_compat.py`                  | 3.9 KB | `app/fastapi_routes/upload.py`                 | 2   | 已完成 |
| `excel_vector_compat.py`            | 4.5 KB | `app/fastapi_routes/excel_vector.py`           | 2   | 已完成 |
| `ocr_compat.py`                     | 5.2 KB | `app/fastapi_routes/ocr.py`                    | 2   | 已完成 |
| `materials_compat.py`               | 6.5 KB | `app/fastapi_routes/materials.py`              | 2   | 已完成 |
| `code_editor.py`                    | 6.9 KB | `app/fastapi_routes/code_editor.py`            | 2   | 已完成 |
| `backend/template_api.py`           | 5.0 KB | `app/fastapi_routes/template_api.py`           | 2   | 已完成 |
| `ai_assistant_compat.py`            | 12 KB  | `app/fastapi_routes/ai_assistant.py`           | 3   | 已完成 |
| `model_payment_compat.py`           | 13 KB  | `app/fastapi_routes/model_payment.py`          | 3   | 已完成 |
| `print_compat.py`                   | 14 KB  | `app/fastapi_routes/print_routes.py`           | 3   | 已完成 |
| `excel_extract_compat.py`           | 15 KB  | `app/fastapi_routes/excel_extract.py`          | 3   | 已完成 |
| `shipment_orders_fastapi_compat.py` | 15 KB  | `app/fastapi_routes/shipment_orders.py`        | 3   | 已完成 |
| `excel_templates_compat.py`         | 22 KB  | `app/fastapi_routes/excel_templates.py`        | 3   | 已完成 |
| `miniprogram_api.py`                | 22 KB  | `app/fastapi_routes/miniprogram.py`            | 3   | 已完成 |
| `approval_compat.py`                | 30 KB  | `app/fastapi_routes/approval.py`               | 3   | 已完成 |
| `archive_gap_batch1.py`             | 82 KB  | `app/fastapi_routes/archive_gap_batch1.py`     | 4   | 已完成 |
| `archive_gap_batch2.py`             | 95 KB  | `app/fastapi_routes/archive_gap_batch2.py`     | 4   | 已完成 |
| `xcagi_compat.py`                   | 147 KB | `app/fastapi_routes/xcagi_compat.py`           | 4   | 已完成 |


死文件(阶段 4 直接删除):`backend/routers/xcagi_compat.py.bak2`、`backend/routers/fix_compat.py`。

### 5.2 支持模块迁移清单(阶段 1)


| 源(`backend/<file>.py`)                                                                                                                                                                    | 目标                                             |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| `tools.py`                                                                                                                                                                                | `app/legacy/tools.py`                          |
| `planner.py`                                                                                                                                                                              | `app/legacy/planner.py`                        |
| `runtime_context.py`                                                                                                                                                                      | `app/legacy/runtime_context.py`                |
| `database.py`                                                                                                                                                                             | `app/legacy/database.py`                       |
| `llm_config.py`、`llm_circuit_breaker.py`、`chat_idempotency.py`、`ai_tier.py`、`ai_model_registry.py`                                                                                        | `app/legacy/` 同名                               |
| `schema_auto_init.py`、`shared_utils.py`、`workspace.py`、`_fix_thinking.py`、`tools_directory_compat.py`                                                                                     | `app/legacy/` 同名                               |
| `http_rate_limit.py`、`http_request_context.py`、`db_read_auth.py`、`db_write_auth.py`、`mod_database_url.py`、`request_active_mod_ctx.py`、`request_client_mods_ctx.py`、`torch_runtime_env.py` | `app/legacy/` 同名                               |
| `attendance_paths.py`、`attendance_convert.py`                                                                                                                                             | `app/legacy/` 同名                               |
| `price_list_docx_export.py`、`sales_contract_excel_generate.py`                                                                                                                            | `app/infrastructure/documents/`                |
| `customers_excel_import.py`、`products_bulk_import.py`                                                                                                                                     | `app/infrastructure/importers/`                |
| `product_db_read.py`                                                                                                                                                                      | `app/infrastructure/repositories/`             |
| `excel_schema_understanding_service.py`、`excel_text_to_pandas.py`、`document_template_service.py`                                                                                          | `app/services/`                                |
| `shell/` 整个包                                                                                                                                                                              | `app/shell/`                                   |
| `services/model_payment_*.py`(已是 shim)                                                                                                                                                    | 阶段 3 直接删除,调用方改引 `app.infrastructure.payment.`* |


### 5.3 阶段闸门


| 阶段  | 目标                                                                                         | 验收门                                                                                                                                                  |
| --- | ------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0   | 预备包与文档修正                                                                                   | 本表落地、README ASCII 对齐 12 域、XCAGI 次级文档"11→12"                                                                                                          |
| 1   | 迁走所有被 `app/` 硬依赖的支持模块                                                                      | `rg "from backend\\." app/ --glob '!app/fastapi_compat_routes/**'` 为 0                                                                               |
| 2   | 12 个小路由 + `template_api` 搬家                                                                | `fastapi_compat_routes/__init__.py` 不再 `from backend.routers.<小路由>`,[app/routes/state.py](../app/routes/state.py) 不再引 `backend.routers.state_compat` |
| 3   | 8 个中等路由 + `shell/` + 删 payment shim                                                        | `mods/taiyangniao-pro`、`XCAGI/mods/taiyangniao-pro` 的 `from backend.*` 清空                                                                            |
| 4   | 3 个大路由(含 147KB `xcagi_compat`)                                                             | [app/fastapi_app.py](../app/fastapi_app.py) 中 `archive_explicit_proxy_routes`、`gap_batch2` 引用改为 `app.*`                                              |
| 5   | `app/fastapi_compat_routes/` 并入 `register_all_routes`、删 `backend/` 整目录、tests 迁入、scripts 更新 | `rg "backend\\." app/ scripts/ tests/ XCAGI/ mods/` 为 0,pytest 全绿,`/api/startup/status` 烟雾通过                                                         |


---

## 6. 待办与风险(从现有文档汇总)


| 项                   | 说明                                                                                 | 跟踪                                                    |
| ------------------- | ---------------------------------------------------------------------------------- | ----------------------------------------------------- |
| **`app/legacy/` 再细拆**       | 阶段 1 把 33 个支持模块集中落在 `app/legacy/`,后续按 DDD 分层再拆到 `app/application` / `app/infrastructure`。 | 开新 issue 跟踪;不影响运行,不赶时间 |
| **服务装配 / DI**              | 首批单例已收敛到 `app/di/registry.py` 的 `ServiceContainer`（session/auth/user/preference、customer/ai_chat/unit_import/file_analysis/wechat_contact、发货全量 wiring）；`app.bootstrap` 与上述 application `get_*` 对齐；FastAPI `app.state.services`；测试用 `set_service_registry` / `reset_service_registry` 或 `invalidate_shipment_wiring` / `invalidate_customer_application_service`。其余 `application/*`、`services/*` 内零散 `global` 单例可按需迁入同一容器。 | 本登记册；`app/di/fastapi_deps.py` |
| **`scripts/dev/tests_adhoc/` 死脚本** | 5 个文件引用的 `backend.unified_ai` 从未存在过(迁移前即是坏引用);保留作历史痕迹或整体删除。                        | 本次已确认不阻塞运行                                             |
| **历史报告**              | `docs/reports/` 下 8+ 份旧报告仍提及 `backend/...`,是迁移前状态的快照,属于只读档案。                       | 不动;参考时以本登记册 §5 为准                                      |


---

**最后更新**：登记册随仓库维护；若未改本文件，以各专题报告日期为准。