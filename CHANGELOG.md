# XCAGI 版本更新日志

> 从 v1.0 到 v8.0 的演进历程

---

## 版本总览

| 版本 | 状态 | 核心升级 |
|------|------|----------|
| **v1.0** | 稳定 | Excel 解析 + 标签打印 |
| **v2.0** | 稳定 | Vue 3 + AI 对话 + OCR |
| **v3.0** | 稳定 | 混合意图引擎 + TTS + 任务 Agent |
| **v4.0** | 稳定 | AI 员工定位 + 全自动流程 + 多模态交互 |
| **v5.0** | 稳定 | Neuro-DDD 架构 + 小程序 + 性能监控 + 审批流 |
| **v6.0** | 稳定 | **商业模式明确 + 三层收入 + Mod 生态** |
| **v7.0** | 稳定 | **Windows/macOS 桌面版 + Web 版并行交付 + 自动更新** |
| **v8.0** | 🚀 当前最新 | **跨行业 UI 适配 + Mod 制作端行业选择 + 平台壳 V8** |

---

## v8.0.0 (2026-05-21) - 跨行业适配

- **行业预设**：宿主与 Mod 制作端共用 `industryPresets`（通用、涂料、考勤、烤禽、批发等），菜单/欢迎语/快捷按钮随所选行业切换。
- **Mod 源码库**：新建 Mod 与制作页可指定目标行业，写入 `manifest.industry` 与 `config/industry_card.json`。
- **版本锚点**：前后端与桌面壳统一为 `8.0.0`；Mod 依赖基线 `>=8.0.0`。

---

## Unreleased

### 🧹 技术债务清理 — Legacy 与 Archive 代码分期拆除

- **Phase 0（已完成）** 基础设施 + 修复幽灵引用
  - 修复 `app/fastapi_routes/xcagi_compat.py` 对不存在的 `app.legacy.product_name_resolve`
    的惰性 import 分支，改为返回 501。
  - 新增 `app/legacy/_deprecation.py`：`emit_legacy_usage` + Prometheus counter
    `fhd_legacy_module_usage_total` + JSONL 日志 `logs/legacy_usage.log`。
  - `app/legacy/__init__.py` 增加 `__getattr__` 钩子，首次属性访问触发遥测。
  - `archive_gap_batch1/2.py` 启动阶段输出承载路由数的 `[legacy-cleanup]` 日志。
  - 新增 `scripts/dev/legacy_usage_report.py`：解析 JSONL 出报告，支持 `--since` / `--json`。
  - 新增 `docs/reports/LEGACY_CLEANUP_TRACKING.md` 跟踪看板。
- **Phase 1（已完成）** 零引用 legacy 文件删除
  - 删除 `app/legacy/_fix_thinking.py`、`ai_model_registry.py`、`chat_idempotency.py`、
    `http_rate_limit.py`、`http_request_context.py`、`llm_circuit_breaker.py`、
    `torch_runtime_env.py`、`template_api.py`（共 8 个，全部确认零引用）。
- **Phase 2（已完成）** `archive_*` 命名工程上全部清除 + 按业务域拆分
  - 新增 `app/fastapi_routes/ai_intent.py`（intent/chat-unified/test）、
    `ai_kitten.py`（Kitten 分析 13 条路由）、`ai_qclaw.py`（Qclaw 7 条路由 + `_QCLOW_RUNTIME_STATE` 权威位置）、
    `spa_fallback.py`（Vue SPA history fallback）。
  - `app/utils/openapi_path.py`：`url_rule_to_openapi_path` / `normalize_path_template`
    搬出 archive_explicit_proxy。
  - 删除 `app/fastapi_routes/archive_explicit_proxy.py`（工具函数已搬走）；
  - 重命名 `app/routes/archive_templates_compat.py` → `app/routes/document_templates_compat.py`；
  - 重命名 `app/services/archive_templates_legacy.py` → `app/services/document_templates_service.py`；
  - 重命名 `app/fastapi_routes/archive_gap_batch1/2.py` → `app/fastapi_routes/legacy_gaps_batch1/2.py`，
    router tag 同步更新为 `legacy-gaps-batch1/2`；
  - 调用方同步更新：`scripts/route_inventory_diff.py`、`scripts/check_openapi_consistency.py`、
    `scripts/dev/smoke_all.py`、`tests/test_routes/test_ai_chat.py`、`app/fastapi_app.py`、
    `app/routes/wechat_miniprogram.py`、`app/services/tools_execution_service.py`、
    `app/routes/template_grid_core.py`。
  - **总路由数从 536 → 536**，前端 URL 契约零变化。
- **Phase 3 / 4 / 5（已完成）** 按分层建立适配层 facade，xcagi_compat 不再直接依赖 `app.legacy.*` 枢纽
  - `app/infrastructure/workspace.py`、`app/infrastructure/request_context/client_mods.py`、
    `app/domain/ai/tier.py`、`app/domain/ai/tools_directory.py`、
    `app/domain/context/session_context.py`、`app/application/workflow/legacy_chat_adapter.py`、
    `app/application/tools/__init__.py`（含 `handle_price_list_export` lazy 转发）、
    `app/infrastructure/db/sync_engine.py`、`app/infrastructure/auth/db_token.py`、
    `app/infrastructure/llm/client.py`。
  - `app/legacy/request_active_mod_ctx.py` 直接删除（其余 5 处引用切到 `app.request_active_mod_ctx`）。
  - `app/services/archive_tools_legacy.py` → `app/services/tools_execution_service.py`
    （最后一个 `archive_*` 命名运行时模块消失）。
  - 路由与脚本调用点同步切到新位置，`app/legacy/*` 残留文件转为 shim 留待 Phase 6 后续批次删除。
- **Phase 6（已完成）** 看守规则 + 发布说明
  - 新增 `.cursor/rules/no-legacy-archive-names.mdc`：在 Cursor 中硬性禁止再添加
    `app/legacy/*` 新模块、`archive_*` 前缀文件、`from app.legacy.*` import 等。
- **终态吸收（已完成）** 实现搬入目标层 + 目录整除
  - 所有 legacy 枢纽与基础设施的实现 **真正从 `app/legacy/` 搬到目标层**：
    `app/application/tools/workflow.py`（吸收 `tools.py`）、
    `app/application/workflow/legacy_chat_adapter.py`（吸收 `planner.py`）、
    `app/domain/context/session_context.py`（吸收 `runtime_context.py`）、
    `app/infrastructure/db/sync_engine.py`（吸收 `database.py` + `mod_database_url.py`）、
    `app/infrastructure/auth/db_token.py`（吸收 `db_read_auth.py` + `db_write_auth.py`）、
    `app/infrastructure/llm/client.py`（吸收 `llm_config.py`）、
    `app/infrastructure/documents/{template_registry,sales_contract_excel,price_list_export}.py`、
    `app/infrastructure/products/{db_read,customer_matching}.py`、
    `app/infrastructure/excel/{schema_service,text_to_pandas}.py`、
    `app/infrastructure/attendance/{dingtalk_convert,workspace_paths}.py`、
    `app/infrastructure/workspace.py`、`app/infrastructure/request_context/client_mods.py`、
    `app/infrastructure/db/schema_auto_init.py`（修复 `parents[1]/scripts` 的路径漂移）、
    `app/domain/ai/{tier,tools_directory}.py`、`app/application/excel_imports.py`。
  - **删除整个 `app/legacy/` 目录**（24 个 shim + `__init__.py` + `_deprecation.py`）。
  - **删除整个 `tests/backend_legacy/` 目录**（35 个测试文件，其验证对象已随 legacy 一同下线）。
  - 本次清理的详细进度与完整度量见 `docs/reports/LEGACY_CLEANUP_TRACKING.md`。

### 🩺 API 文档 / 路由一致性守护

- **新增** `scripts/check_openapi_consistency.py`：对 FastAPI 运行时路由与
  `/openapi.json` 双向 diff，分级（error/warn/info）输出，支持 `--md-out` /
  `--json-out` / `--ignore-regex` / `--strict`。
- **新增** `tests/test_openapi_consistency.py`：将 error 级发现纳入 pytest，
  作为 CI 守门员，并单独覆盖 "`app.openapi()` 能否无 PydanticUserError 地生成
  schema" 的回归场景。
- **新增** `docs/guides/OPENAPI_CONSISTENCY.md` 使用指南 & 修复套路。
- **修复** `app/neuro_bus/route_event_publisher.py::publish_route_event`：
  在 `from __future__ import annotations` 语义下，装饰器把 BaseModel 参数退化
  为 Query 导致 OpenAPI 生成抛 `PydanticUserError` 的问题。方法是在包装时用
  `typing.get_type_hints()` 预解析并回写到 wrapper 与原函数的 `__annotations__`。
- **修复** 4 处 `(method, path)` 跨模块重复注册（隐藏兼容 stub，不改变运行时
  行为）：
  - `/api/system/industries`、`/api/system/industry` GET/POST —
    `app/fastapi_routes/xcagi_compat.py` 中的兜底 stub 改为
    `include_in_schema=False`，业务实现保留在 `system_routes.py`。
  - `/api/health` — `ai_assistant.py::compat_health` 改为
    `include_in_schema=False`，文档版本由 `fastapi_routes/__init__.py` 提供。
  - `/api/lan/admin/settings` GET/POST/PUT — `lan_admin_routes.py` 中的
    被覆盖版本改为 `include_in_schema=False`，保留 `lan_settings_routes.py`
    中带 `LanSettingsView` 响应模型的规范实现。
- **效果**：`error=0`（之前 OpenAPI 根本生成失败）、FastAPI
  `Duplicate Operation ID` 警告全部消除。

---

## v7.0.0 (2026-04-29) - 🖥️ 桌面化时代

### 🎯 重大定位升级

**从「Web 企业 AI 员工平台」升级为「桌面版 + Web 版并行的企业 AI 员工平台」**

- **桌面版**：新增 [desktop/](desktop/) Electron 壳，启动本地 FastAPI 子进程，Windows / macOS 双平台交付。
- **Web 版保留**：Docker Compose / Nginx / 局域网部署路径不下线，继续服务企业自托管和开发调试。
- **混合模式**：本地处理 Excel、出货、打印、OCR 与核心业务；云端继续承载 Token 钱包、Mod 商店和重型 AI。
- **自动更新**：接入 electron-updater 自建 update server 模板，支持差量包、通道、灰度、强制升级和失败回滚设计。

### 🆕 新增核心能力

| 能力 | 说明 |
|------|------|
| Windows / macOS 桌面壳 | `desktop/main.ts` 管理窗口、托盘、菜单、后端子进程、自动更新入口 |
| 桌面运行时 | `app/desktop_runtime/` 提供 userData 路径、SQLite 默认、内存缓存、线程队列、模型下载、数据迁移入口 |
| 桌面 API | `/api/desktop/status`、`/api/desktop/models`、`/api/desktop/models/download` |
| 桌面运行时页面 | `frontend/src/views/DesktopRuntimeView.vue`，web 与桌面共用 |
| 打包脚本 | `scripts/package/build-backend.*`、`build-installer.*`、`release-web.ps1` |
| CI 发布 | `.github/workflows/release-desktop.yml` 与 `release-web.yml` |
| update server 模板 | `update-server/` 提供 Nginx 与 latest.yml/latest-mac.yml 模板 |

### 🔧 技术升级

```bash
# Windows 桌面安装包
powershell -ExecutionPolicy Bypass -File scripts/package/build-installer.ps1 -Version 7.0.0

# macOS 桌面安装包
bash scripts/package/build-installer.sh 7.0.0

# Web 版继续走 Docker
docker-compose pull && docker-compose up -d
```

### ⚠️ 注意事项

- 桌面安装包正式发布前必须准备 Windows 代码签名证书与 Apple Developer ID；无证书构建可用于内部验证，但会触发系统信任提示。
- AI 大模型不放进安装包，仍按需下载到系统 userData 目录。
- `XCAGI_DESKTOP_MODE=1` 才会启用 SQLite / 内存缓存 / 本地线程队列；默认 web 模式保持 PostgreSQL + Redis + Celery。

---

## v6.0.0 (2026-04-17) - 💰 商业时代

### 🎯 重大定位升级

**从「AI 单据智能处理系统」升级为「企业 AI 员工平台」**

- 💰 **商业模式明确** - 本地部署 + Mod 商店 + Token 付费
- 🏪 **员工商店** - 第三方/官方行业 Mod 付费下载平台
- 🔑 **认证钱包** - AI 能力按量计费，持续性收入
- 🔄 **生态飞轮** - Mod 越多 → 用户越多 → Token 消耗越多 → 开发者越多

### 🆕 新增核心能力

| 能力 | 说明 | 重要性 |
|------|------|--------|
| **三层收入结构** | 本地部署授权 + Mod 商店分成 + Token 消耗 | ⭐⭐⭐⭐⭐ |
| **Mod 生态系统** | 热插拔、行业配置覆盖、Manifest 清单 | ⭐⭐⭐⭐⭐ |
| **Token 认证钱包** | 按量计费、套餐管理、用量监控 | ⭐⭐⭐⭐⭐ |
| **防绕过机制** | 核心 AI 云端化、License 验证、签名校验 | ⭐⭐⭐⭐ |
| **开发者激励计划** | 70% 分成、新人奖励、畅销奖励 | ⭐⭐⭐⭐ |
| **客户成功体系** | 标杆客户、ROI 证明、NPS 评分 | ⭐⭐⭐⭐ |

### 💰 商业模式

**类比**: VSCode + App Store + OpenAI

| 模式 | 对标 | 说明 |
|------|------|------|
| 本地部署 | VSCode | 免费/低价获客，降低入门门槛 |
| Mod 商店 | App Store | 第三方插件付费下载，平台抽成 30% |
| Token 付费 | OpenAI | AI 调用按量计费，持续性收入 |

### 📊 定价策略（参考）

| 版本 | 价格 | 包含内容 |
|------|------|---------|
| **社区版** | 免费 | AGPL 协议，功能受限 |
| **标准版** | ¥10,000–30,000/年 | 完整功能，单实例 |
| **企业版** | ¥50,000–100,000/年 | 多实例、优先支持、定制开发 |

| Token 套餐 | 价格 | 包含调用次数 |
|-----------|------|------------|
| **基础包** | ¥999/月 | 10,000 次 |
| **专业包** | ¥2,999/月 | 50,000 次 |
| **企业包** | ¥9,999/月 | 200,000 次 |

### 🏪 Mod 生态

**已有 Mod**:

- `sz-qsm-pro` - 奇士美 PRO 行业定制版（¥1,999）
- `taiyangniao-pro` - 太阳鸟 PRO 相关扩展（¥1,499）

**开发者分成**: 70% 开发者 / 30% 平台

### ⚡ 性能提升（目标取向，非第三方审计 SLA）

| 指标 | v5.0 | v6.0 | 提升 |
|------|------|------|------|
| 前端加载时间 | ~0.8s | ~0.6s | ⬆️ **25%** |
| 意图识别准确率 | ~99% | ~99.5% | ⬆️ **0.5%** |
| 可用性 | 99.5% | 99.9% | ⬆️ **0.4%** |
| 并发能力 | 1000 QPS | 2000 QPS | ⬆️ **100%** |

### 🔧 技术升级

| 组件 | v5.0 | v6.0 | 改进 |
|------|------|------|------|
| 商业模式 | 未明确 | **三层收入** | 可持续变现 |
| Mod 系统 | 基础 | **完整生态** | 开发者激励 |
| Token 计费 | 无 | **认证钱包** | 持续性收入 |
| 文档体系 | 分散 | **统一规范** | 开发者友好 |
| 目录结构 | `backend/` + `app/` 并存 | **仅 `app/`**（2026-04-20 全量迁移） | 单一落点 |

### 📚 新增 / 更新文档

- 💰 [`BUSINESS_MODEL.md`](BUSINESS_MODEL.md) — 三层收入结构详解（如提供）
- 🏗️ [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — Neuro-DDD 架构详解
- 🗺️ [`docs/FEATURE_MAP.md`](docs/FEATURE_MAP.md) — 功能边界与目录职责（必读）
- 🧭 [`docs/MIGRATION_REGISTRY.md`](docs/MIGRATION_REGISTRY.md) — 迁移总登记册

### ⚠️ 破坏性变更

- 新增环境变量：`TOKEN_WALLET_ENABLED`、`MOD_STORE_ENABLED`
- Mod Manifest 格式升级（v2）
- API 鉴权增强（Token 签名验证）
- 旧 `backend/` Python 包已全量下线；历史备份见 `.archive/legacy-backend-2026-04-final/`
- HTTP 入口统一为 `XCAGI/run.py` 端口 `5000`，`backend.http_app:8000` 已删除

---

## v5.0.0 (2026-04-05) - 🧠 Neuro-DDD 时代

### 🎯 重大定位升级

**从「AI 员工」升级为「基于 Neuro-DDD 架构的企业 AI 员工平台」**

- 🧠 **Neuro-DDD 架构** - 神经领域驱动设计，12 个神经域（含 `ShipmentNeuroDomain`）
- 🚌 **NeuroBus** - 8 大可靠性机制（去重、限流、熔断、追踪、SLA 等）
- ⚡ **神经反射弧** - <1ms 超快响应
- 📱 **小程序支持** - 微信小程序完整 CRM 功能

### 🆕 新增核心能力

| 能力 | 说明 | 重要性 |
|------|------|--------|
| **Neuro-DDD 架构** | 12 个神经域自治协同（含 `ShipmentNeuroDomain` 出货域） | ⭐⭐⭐⭐⭐ |
| **NeuroBus 8 大机制** | 去重、追踪、限流、熔断、SLA 等 | ⭐⭐⭐⭐⭐ |
| **神经反射弧** | <1ms 规则匹配快速响应 | ⭐⭐⭐⭐ |
| **潜意识/显意识双模** | <10ms / <200ms 双模处理 | ⭐⭐⭐⭐ |
| **小程序 API** | 微信小程序完整功能 | ⭐⭐⭐⭐ |
| **审批流** | 多级审批流程支持 | ⭐⭐⭐⭐ |
| **FastAPI 主入口** | `XCAGI/run.py` → `app.fastapi_app:get_fastapi_app`；Flask 已拆除 | ⭐⭐⭐⭐⭐ |

### 📊 性能指标

| 指标 | v4.0 | v5.0 | 提升 |
|------|------|------|------|
| 前端加载时间 | ~1.0s | ~0.8s | ⬆️ **20%** |
| AI 员工响应 | 毫秒级 | <1ms 反射弧 | ⬆️ **100 倍** |
| 可用性 | 99% | 99.5% | ⬆️ **0.5%** |

---

## v4.0.0 (2026-03-25) - 🤖 AI 员工时代

### 🎯 重大定位升级

**从「智能单据处理系统」升级为「基于 AI 的单据智能处理 AI 员工」**

- 🤖 **AI 员工定位** - 不再是被动工具，而是能主动决策、自主学习的 AI 员工
- 🔄 **全自动化流程** - 业务流程自动执行，真正解放双手
- 💬 **多模态交互** - TTS 语音 + 自然语言 + 微信消息
- 🏢 **行业智能适配** - 多行业模板支持

### 🆕 新增核心能力

| 能力 | 说明 | 重要性 |
|------|------|--------|
| **AI 智能决策** | 混合意图识别引擎 v2，准确率 99%+ | ⭐⭐⭐ |
| **全自动化处理** | 单据自动识别、业务流程自动执行 | ⭐⭐⭐ |
| **多模态交互** | TTS 语音合成、自然语言对话 | ⭐⭐⭐ |
| **行业智能适配** | 多行业模板、灵活配置 | ⭐⭐ |

### 🏢 适用行业扩展

- 🏭 **制造业** - 生产单据、物料标签、出货管理
- 🚚 **物流行业** - 快递单据、货物追踪、签收确认
- 🛒 **零售业** - 进货单、商品标签、库存管理
- 📦 **批发行业** - 批发单据、订单管理、价格体系
- 🛍️ **电商行业** - 订单处理、发货单、退货管理

---

## v3.0.0 (2026-03-15) - 🎯 混合智能时代

### 🆕 新增功能

| 功能 | 说明 | 重要性 |
|------|------|--------|
| **混合意图识别引擎** | 规则 + RASA NLU + BERT 三重保障 | ⭐⭐⭐ |
| **TTS 语音合成** | Edge TTS 多音色、语速/音调可调 | ⭐⭐⭐ |
| **任务自动化 Agent** | 复杂任务自动执行 | ⭐⭐⭐ |
| **微信生态集成** | 消息处理、联系人同步、消息解析 | ⭐⭐ |
| **BERT 本地推理** | 蒸馏模型离线可用 | ⭐⭐⭐ |
| **Alembic 迁移** | 数据库版本自动管理 | ⭐⭐ |
| **DDD 架构** | 领域驱动设计 | ⭐⭐ |

### 🔧 技术升级

| 类别 | v2.0 | v3.0 |
|------|------|------|
| Flask | 2.0+ | 3.0+ |
| ORM | 基础 | SQLAlchemy 2.0+ |
| 数据库迁移 | 手动 | Alembic 自动 |
| 前端状态管理 | - | Pinia 3.0+ |
| 构建工具 | 基础 | Vite 4.4+ |
| 意图识别 | 云端 API | 混合离线可用 |
| 架构模式 | 简单分层 | DDD 领域驱动 |

---

## v2.0.0 (2026-03-01) - 🌐 Web 智能化时代

### 🆕 新增功能

| 功能 | 说明 |
|------|------|
| Vue 3 前端 | 全新现代化 Web 界面 |
| AI 对话 | DeepSeek AI 模型集成 |
| OCR 识别 | 文字自动识别 |
| 多客户隔离 | 数据隔离管理 |
| 价格体系 | 价格管理功能 |
| RESTful API | 完整 API 接口 |
| Swagger 文档 | API 文档自动生成 |
| Redis 缓存 | 数据缓存加速 |
| Celery 队列 | 异步任务处理 |

### 🔧 技术升级

| 类别 | v1.0 | v2.0 |
|------|------|------|
| 界面 | 命令行 | Vue 3 Web |
| AI 能力 | 无 | DeepSeek API |
| 架构 | 单文件 | 模块化 |
| 文档 | 无 | Swagger |

---

## v1.0.0 (2026-02-15) - 📊 基础工具时代

### 🆕 核心功能

| 功能 | 说明 |
|------|------|
| Excel 解析 | 自动识别出货单/收货单 |
| 标签打印 | TSC 打印机支持 |
| 数据管理 | 基础 CRUD 操作 |
| 单据处理 | 出货/收货记录管理 |

### 🔧 技术栈

```
Python + openpyxl + SQLite + TSC 打印机
```

---

## 功能对比总览

| 功能 | v1.0 | v2.0 | v3.0 | v4.0 | v5.0 | v6.0 | v7.0 | v8.0 |
|------|:----:|:----:|:----:|:----:|:----:|:----:|:----:|:----:|
| Excel 解析 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 标签打印 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Vue Web 界面 | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| AI 对话 | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| OCR 识别 | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 多客户隔离 | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 价格管理 | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Redis 缓存 | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Celery 队列 | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| RESTful API | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Swagger / OpenAPI | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **混合意图引擎** | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **TTS 语音合成** | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **任务 Agent** | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **微信集成** | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **DDD 架构** | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **BERT 本地推理** | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Alembic 迁移** | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **AI 员工定位** | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **全自动流程** | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **多模态交互** | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **行业适配** | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Neuro-DDD / NeuroBus** | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| **神经反射弧 (<1ms)** | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| **FastAPI 唯一入口** | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| **小程序 API** | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| **审批流** | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Mod 商店 / 员工商店** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| **Token 认证钱包** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| **三层收入结构** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| **桌面安装包（Electron）** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| **自动更新** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| **跨行业 UI 适配** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Mod 制作端行业选择** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## 技术栈演进

### v1.0

```
Python + openpyxl + SQLite + TSC 打印机
```

### v2.0

```
Python + Flask + Vue 3 + DeepSeek API + OCR + Redis + Celery
```

### v3.0

```
Python + Flask 3.0 + Vue 3.3 + Pinia + SQLAlchemy 2.0 + Alembic
    + DeepSeek AI + RASA NLU + BERT + PyTorch + Transformers
    + Edge TTS + Celery + Redis + DDD 架构
```

### v4.0

```
Python + Flask 3.0 + Vue 3.4 + Pinia + SQLAlchemy 2.0 + Alembic
    + DeepSeek AI + RASA NLU + BERT + PyTorch + Transformers
    + Edge TTS + Celery + Redis 7.0 + DDD 架构
    + PostgreSQL 16 + pgvector 向量搜索
    + Prometheus + Grafana + Loki 全链路监控
    + Kubernetes 容器编排
    + AI 员工核心 + 全自动流程 + 多模态交互 + 行业智能适配
```

### v5.0

```
Python 3.11 + FastAPI 0.110 + Uvicorn + Vue 3.4 + Vite 6 + TypeScript 5
    + SQLAlchemy 2 + Alembic + PostgreSQL 16 + pgvector
    + Neuro-DDD 分层 + NeuroBus 8 大机制 + 12 神经域
    + DeepSeek / BERT / PaddleOCR / EasyOCR
    + MODstore / Mod Manager + 微信小程序 + 审批流
```

### v6.0

```
v5.0 技术栈
    + Mod 商店 / 员工商店 / Manifest v2
    + Token 认证钱包（按量计费、套餐管理、用量监控）
    + 开发者分成（70/30）+ License / API 签名校验
    + 本地部署 + SaaS Token 的混合部署形态
```

---

## 升级路径

### v1.0 → v2.0

```bash
pip install -r requirements.txt
python run.py
```

### v2.0 → v3.0

```bash
pip install -r requirements.txt
alembic upgrade head
python run.py
celery -A celery_app worker --loglevel=info   # 可选
```

### v3.0 → v4.0

```bash
git pull origin main
pip install -r requirements.txt
alembic upgrade head
# .env：AI_EMPLOYEE_MODE=true / INDUSTRY_TYPE=manufacturing
docker-compose restart
```

### v4.0 → v5.0

```bash
git pull origin main
pip install -r requirements.txt
alembic upgrade head
# HTTP 入口改为 XCAGI/run.py（端口 5000），Flask 入口已拆除
cd XCAGI && python run.py
```

### v5.0 → v6.0

```bash
git pull origin main
pip install -r requirements.txt
alembic upgrade head
# .env 新增：
#   TOKEN_WALLET_ENABLED=true
#   MOD_STORE_ENABLED=true
# Mod Manifest 升级到 v2（模板见 docs/guides/MOD_AUTHORING_GUIDE.md）
cd XCAGI && python run.py
```

---

## 未来展望

### v7.0

- [x] Windows/macOS 桌面安装包
- [x] 自动更新

### v8.0（当前）

- [x] 跨行业 UI 适配 + 行业预设
- [x] Mod 制作端行业选择
- [ ] 更广覆盖的自动化测试与 CI
- [ ] 移动端 App 支持
- [ ] 多语言支持（国际化）
- [ ] 更多行业模板

---

## 许可证

本项目采用 **GNU Affero General Public License v3.0 (AGPL-3.0)** 开源许可证。

---

> 🚀 **从 v1 到 v8，XCAGI 完成了从「工具」→「智能系统」→「AI 员工」→「企业 AI 员工平台」→「跨行业适配平台」的五次跨越**
>
> - **v1**: 自动化工具 - 替代手工操作
> - **v2**: 智能系统 - 引入 AI 能力
> - **v3**: 混合智能 - 离线可用、多引擎协同
> - **v4**: AI 员工 - 主动决策、自主学习、全自动化
> - **v5**: Neuro-DDD 平台 - 神经域 + FastAPI + Mod 生态（基础）
> - **v6**: 企业 AI 员工平台 - 三层收入 + Mod 商店 + Token 钱包
> - **v7**: 桌面化时代 - Windows/macOS 安装包 + 自动更新
> - **v8**: 跨行业适配 - 行业预设 + Mod 制作端行业选择

*最后更新：2026-05-26*
