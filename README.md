# XCAGI v8.0 - 独立宿主 + 平台 MOD 变身垂直系统

> **产品模型**：每家客户部署**自己的一份** XCAGI 宿主（空壳）；从平台安装 MOD 后，该实例即变为对应的行业系统（ERP、出货、客服等）。你不代运营客户业务数据。  
> 技术形态：桌面版 + Web 自托管并行 · Neuro-DDD · FastAPI · Mod 生态 · MOD 商店。  
> 全量收口计划：[docs/guides/ADCDFG_COMPLETION_PLAN.md](docs/guides/ADCDFG_COMPLETION_PLAN.md)

**版本说明索引**：下列 **[版本与发布约定](#version-policy)** 与仓库根目录 **[`VERSION.md`](VERSION.md)** 保持同一套锚点与自检命令；本 README 在该节**复述 `VERSION.md` 正文**并额外说明 **Git / GitHub 展示仓库** 行为。若两处将来出现差异，**以 `VERSION.md` 为准**，README 应随 PR 一并改正。

🤖 **基于 Neuro-DDD（分层 + AI 用例编排）与 FastAPI 的 AI 单据智能处理系统**，适用于各行业的标签打印、出货管理和收货确认场景。

[Release](https://github.com/42433422/xcagi/releases)
[License: AGPL v3](https://www.gnu.org/licenses/agpl-3.0.html)
[Python](https://www.python.org/)
[FastAPI](https://fastapi.tiangolo.com/)
[Architecture](#-neuro-ddd-与代码落点必读)
[Vue](https://vuejs.org/)
[Platform](https://www.microsoft.com/windows/)
[Code style: black](https://github.com/psf/black)
[Contributions welcome](https://github.com/42433422/ai-excel-helper/blob/master/.github/CONTRIBUTING.md)

## 🌟 项目简介

**XCAGI v8.0** 通过 OCR、混合意图识别与大模型工作流，把「上传 Excel / 对话指令 → 解析 → 业务动作（出货、打印、库存等）」连成可运维的闭环，并新增 Windows / macOS 桌面交付形态。

> 🚀 **v8.0 / 8.0.0 当前版本**: `Electron 桌面壳 + FastAPI 本地子进程 + Vue 3 前端复用`，同时保留 Docker / Nginx web 版并行交付；Mod 商店 / 员工商店 / Token 认证钱包继续作为两种形态共用的商业化能力；跨行业 UI 适配 + Mod 制作端行业选择。
> 🎯 **从「工具」到「员工」**: 侧重可编排的用例与可替换的基础设施实现，而不是把业务规则堆在路由里。  
> 🧠 **Neuro-DDD 在本仓库的含义**: **DDD 分层**（`application` / `domain` / `infrastructure`）+ **AI 对话与工作流的用例编排**；HTTP 层尽量薄，装配集中在 Composition Root（`app/bootstrap.py`）。**神经域 + NeuroBus 大图及组件摘录**与 `**[XCAGI/README.md](XCAGI/README.md)`** 同构展示；**以源码为准**。

**仓库**: 默认以 **[ai-excel-helper](https://github.com/42433422/ai-excel-helper)** 为一体化交付树（与历史 **xcagi** 发行说明互通，克隆地址见下文）。

**快速链接**:

- 📖 [快速开始指南](docs/QUICK_START.md)
- 🏗️ [架构设计文档](docs/ARCHITECTURE.md)
- 🗺️ [功能边界图 / 目录职责(Feature Map)](docs/FEATURE_MAP.md) ← **必读**
- 🤖 [AI 员工配置指南](docs/AI_EMPLOYEE.md)
- 🧩 [MOD 作者指南](docs/guides/MOD_AUTHORING_GUIDE.md)（manifest / SDK / hook / comms / workflow_employees / 打包与冒烟）
- 🧭 [迁移总登记册](docs/MIGRATION_REGISTRY.md)(入口统一 / Flask 拆除 / Neuro / 归档索引)
- 📚 [完整文档](docs/)
- 🗂️ [文档地图（Canonical / 归档 / 工具说明）](docs/DOCUMENTATION_MAP.md)
- 📝 [更新日志](CHANGELOG.md)
- 📌 [版本锚点 VERSION.md](VERSION.md)（**单一事实来源**，与下文 README 节同步）
- 🤝 [贡献指南](.github/CONTRIBUTING.md)

<a id="version-policy"></a>

## 版本与发布约定（与 VERSION.md 一致）

> 本节的**版本号表、产品定位、相关文档索引、发版前自检命令**与 [`VERSION.md`](VERSION.md) 对齐；完整叙事与按日期的发布说明仍以 [`CHANGELOG.md`](CHANGELOG.md) 为准（当前 GA 章节：**v8.0.0 (2026-05-21) — 跨行业适配**）。

### 版本号（必须同步的锚点）

| 组件 | 版本 | 文件 |
|------|------|------|
| **XCAGI 总版本** | `8.0.0` | `CHANGELOG.md`、`README.md` |
| **Python 包（根）** | `8.0.0` | `pyproject.toml` |
| **Python 包（XCAGI 子树）** | `8.0.0` | `XCAGI/pyproject.toml` |
| **前端 SPA** | `8.0.0` | `frontend/package.json` |
| **桌面壳 npm** | `8.0.0` | `desktop/package.json` |
| **根级 npm（脚本/测试入口）** | `8.0.0` | `package.json` |
| **FastAPI 应用** | `8.0.0` | `app/fastapi_app.py`（`FastAPI(version=...)`） |
| **Mod 依赖校验基线** | `8.0.0` | `app/infrastructure/mods/manifest.py` |

> 独立子工程保留自己的版本号：`MODstore/pyproject.toml`（`0.2.0`）、`MODstore/web/package.json`（`0.2.0`）、`MODstore/market/package.json`（`1.0.0`）。

发版打安装包时脚本使用的 **`-Version` / 参数版本字符串** 须与上表 **8.0.0** 一致（示例见下文 CHANGELOG 摘要中的命令块）。

### 当前定位（v8.0）

**跨平台企业 AI 员工桌面平台** — Windows/macOS 桌面版 + Web 版并行交付，保留 Neuro-DDD + FastAPI + Mod 生态 + Token 认证钱包 + 跨行业 UI 适配。

### v8.0.0 发布摘要（详见 CHANGELOG）

以下内容对应 `CHANGELOG.md` **v8.0.0 (2026-05-21) — 跨行业适配** 一节，此处仅作索引；细节、命令与注意事项以 CHANGELOG 全文为准。

- **定位**：在 v7.0 桌面版 + Web 版并行基础上，新增**跨行业 UI 适配**与**Mod 制作端行业选择**能力。
- **新增能力（节选）**：宿主与 Mod 制作端共用 `industryPresets`（通用、涂料、考勤、烤禽、批发等），菜单/欢迎语/快捷按钮随所选行业切换；新建 Mod 可指定目标行业，写入 `manifest.industry` 与 `config/industry_card.json`。
- **版本锚点**：前后端与桌面壳统一为 `8.0.0`；Mod 依赖基线 `>=8.0.0`。
- **打包命令示例**（与 CHANGELOG 一致）：

```bash
# Windows 桌面安装包
powershell -ExecutionPolicy Bypass -File scripts/package/build-installer.ps1 -Version 8.0.0

# macOS 桌面安装包
bash scripts/package/build-installer.sh 8.0.0
```

### 相关文档（与 VERSION.md 相同索引）

- 📝 [完整变更日志 CHANGELOG.md](CHANGELOG.md)
- 📖 [项目 README](README.md)（即本页）
- 🏗️ [架构设计 docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- 🗺️ [功能边界 docs/FEATURE_MAP.md](docs/FEATURE_MAP.md)
- 🧭 [迁移登记册 docs/MIGRATION_REGISTRY.md](docs/MIGRATION_REGISTRY.md)

### 版本同步约定（发版前自检）

当主版本号变更时，必须**同步修改**本节表格中的所有锚点文件，并在 `CHANGELOG.md` 顶部新增一节。建议在 PR 描述里贴一段 diff 摘要。

```bash
# 快速全仓对齐扫描（与 VERSION.md 中命令一致）
rg -n --hidden -g '!node_modules' -g '!.archive' -g '!XCAGI/node_modules' \
  'version\s*=\s*"[0-9]' pyproject.toml XCAGI/pyproject.toml \
  frontend/package.json desktop/package.json package.json
rg -n 'version\s*=\s*"[0-9]' app/fastapi_app.py app/infrastructure/mods/manifest.py
```

### Git 与 GitHub 展示仓库（README 扩展说明）

| 项目 | 说明 |
|------|------|
| **一体化展示仓库** | **[ai-excel-helper](https://github.com/42433422/ai-excel-helper)**，**主库默认分支为 `master`**，用于公开展示与协作克隆（`git clone` 后默认检出 `master`）。 |
| **Git 标签** | 附注标签 **`v8.0.0`** 指向与上表 **语义化 `8.0.0`** 一致的提交；在 **`master`** 上执行 `git describe --tags` 应得到 **`v8.0.0`**（[标签页](https://github.com/42433422/ai-excel-helper/releases/tag/v8.0.0)）。 |
| **与 xcagi 发行说明** | 历史与发行说明仍可与 **[xcagi/releases](https://github.com/42433422/xcagi/releases)** 对照；本仓库 `CHANGELOG` 为一体化树的主变更记录。 |
| **展示克隆体积控制** | 向 **`origin/master`** 推送时采用**在 `master` 上增量提交**的方式，避免附带历史中的超大二进制（如旧快照 zip）；**`QClaw/resources/app.asar` 等运行时大包不纳入该分支**，本地完整体验需自行构建或取发行物。 |
| **CI 触发** | 推送符合 **`v8.*`** 模式的标签会触发 `.github/workflows/` 中桌面/Web 相关流水线；若仅浏览源码、不需要 CI，请避免误推此类标签或按需调整 workflow。 |

---

## 🖥️ v8.0 交付形态

- **桌面版**：Windows `.exe` 与 macOS `.dmg/.pkg`，由 [desktop/](desktop/) 的 Electron 壳启动本地 FastAPI 子进程，数据默认存放在系统 userData 目录。
- **Web 版**：Docker Compose / Nginx 路径继续保留，适合企业自托管、局域网部署和开发调试。
- **开发模式**：仍然使用 `cd XCAGI && python run.py` + `cd frontend && npm run dev`，桌面化不改变现有开发流。
- **桌面打包**：Windows 执行 `scripts/package/build-installer.ps1`，macOS 执行 `scripts/package/build-installer.sh`。真实发布前需准备 Windows 代码签名证书与 Apple Developer ID。

---

## 📏 目录职责硬规则(提交前自检)

新的代码/文件落点有三条 **硬约束**,PR 不遵守将被拒:

1. **服务端代码只许新写到 `app/`**。`backend/` 目录已于 **2026-04-20** 全量迁出并删除(迁移登记见 [docs/MIGRATION_REGISTRY.md §5](docs/MIGRATION_REGISTRY.md))。历史文件备份在 [.archive/legacy-backend-2026-04-final/](.archive/legacy-backend-2026-04-final/)。
2. **前端代码只许写到 `frontend/`**。`static/`、`templates/vue-dist/` 是构建产物,不是源;不要往里改东西。
3. **服务启动只用 `XCAGI/run.py`(端口 5000)**。`backend/http_app.py`(历史 8000 端口)已删除;禁止新增任何其它 HTTP 入口。

> 每个业务功能的单一落点见 [docs/FEATURE_MAP.md](docs/FEATURE_MAP.md)。
> 目录重组历史见 `docs/reports/`;本轮(2026-04-20)把 60+ 顶层目录 + 270+ 根文件收敛到 45 目录 + 38 根文件。

---

## 🧠 Neuro-DDD 与代码落点（必读）

> **架构展示**（神经域拓扑、NeuroBus 大图、伪代码摘录、11 域职责表）与 `**[XCAGI/README.md](XCAGI/README.md)`** 同一套叙事对齐，便于「一体化仓库」与 **XCAGI 独立发行子树** 对照阅读。  
> **生产推荐唯一 HTTP 入口**：`**XCAGI/run.py` → `app.fastapi_app:get_fastapi_app`（默认 `5000`）**。根目录 `**backend/` Python 包已于 2026-04-20 完全下线**（路由迁至 `[app/fastapi_routes/](app/fastapi_routes/)`,支持模块迁至 `[app/legacy/](app/legacy/)` 与 `[app/shell/](app/shell/)`，详见 `[docs/MIGRATION_REGISTRY.md §5](docs/MIGRATION_REGISTRY.md)`）。

### 1）一体化仓库：共享分层与遗留入口（管理视角）


| 类型                   | 代码落点                                                                                    | 说明                                                                   |
| -------------------- | --------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| **推荐 API 入口**        | `**XCAGI/run.py`**                                                                      | 默认 `**0.0.0.0:5000`**；OpenAPI：`/docs`、`/redoc`                       |
| **弃用 API 入口**        | `backend/http_app.py`                                                                   | 已删除;历史备份 `.archive/legacy-backend-2026-04-final/`                    |
| **已移除 Flask 路由**     | **已删**；备份 `.archive/flask-routes-2026-04/`                                              | 替代：`**app/fastapi_routes/`**（及 `app/fastapi_compat_routes` 等注册一致的壳层） |
| **装配根**              | `**app/bootstrap.py`**（仓库根 `app/`）                                                      | `XCAGI/run.py` 将父目录加入 `sys.path` 后加载该包                               |
| **应用服务 / 领域 / 基础设施** | `**app/application/`**、`**app/domain/`**、`**app/infrastructure/**`、`**app/neuro_bus/**` | 路由层应薄；优先调用 application                                               |


**依赖方向（约定）**: HTTP 层 → `application` → (`domain` + `infrastructure` 抽象)。更细的约束与示例见 `[app/application/README.md](app/application/README.md)`。

---

### 2）Neuro-DDD 神经领域驱动架构（与 `XCAGI/README.md` 同构展示）

在经典 **DDD** 之上，为 AI 对话、意图、工作流与多模块协同增加了 **NeuroBus / 神经域** 等概念与实现（`**app/neuro_bus/`**、`**app/fastapi_app.py`** 中 `lifespan` 装配等），统称为 **Neuro-DDD**。下图与后文摘录用于理解边界，**以仓库根 `app/` 源码为准**。

#### 2.1 神经域 (NeuroDomain) 体系

项目定义了 **12 个神经域**（含出货 **ShipmentNeuroDomain**），每个域都是独立的自治单元，通过**神经总线 (NeuroBus)** 进行异步信号通信：

```
┌─────────────────────────────────────────────────────────────────────┐
│                        🧠 Neuro-DDD 架构                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐         │
│   │  Intent     │     │   Order     │     │ Inventory   │         │
│   │  NeuroDomain│────▶│  NeuroDomain│────▶│  NeuroDomain│         │
│   │  意图识别    │     │   订单域    │     │   库存域     │         │
│   └─────────────┘     └─────────────┘     └─────────────┘         │
│         │                   │                   │                   │
│         ▼                   ▼                   ▼                   │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐         │
│   │  Product    │     │ Customer    │     │  AIService  │         │
│   │  NeuroDomain│     │  NeuroDomain│     │  NeuroDomain│         │
│   │   产品域     │     │   客户域    │     │  AI服务域   │         │
│   └─────────────┘     └─────────────┘     └─────────────┘         │
│         │                   │                   │                   │
│         └───────────────────┼───────────────────┘                   │
│                             ▼                                        │
│   ┌─────────────────────────────────────────────────────────┐       │
│   │                    NeuroBus 神经总线                      │       │
│   │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐     │       │
│   │  │ 去重器   │ │ 限流器   │ │ 熔断器   │ │ 追踪器   │     │       │
│   │  └─────────┘ └─────────┘ └─────────┘ └─────────┘     │       │
│   │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐     │       │
│   │  │ SLA配置  │ │错误反馈  │ │ 沙盒预演  │ │ 保命通道  │     │       │
│   │  └─────────┘ └─────────┘ └─────────┘ └─────────┘     │       │
│   └─────────────────────────────────────────────────────────┘       │
│                             │                                        │
│         ┌───────────────────┼───────────────────┐                    │
│         ▼                   ▼                   ▼                    │
│   ┌───────────┐       ┌───────────┐       ┌───────────┐            │
│   │  Wechat   │       │  Print    │       │   OCR     │            │
│   │  NeuroDomain│     │  NeuroDomain│     │  NeuroDomain│           │
│   └───────────┘       └───────────┘       └───────────┘            │
│         │                   │                   │                   │
│         └───────────────────┼───────────────────┘                   │
│                             ▼                                        │
│   ┌───────────┐       ┌───────────┐       ┌───────────┐            │
│   │  Payment  │       │  Safety   │       │ Shipment  │            │
│   │  NeuroDomain│     │  NeuroDomain│     │  NeuroDomain│           │
│   │   支付域   │       │   安全域   │       │  出货/发货 │            │
│   └───────────┘       └───────────┘       └───────────┘            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

**示意图与源码对照（导入可用 `from app.neuro_domains import ...`）**


| 示意图名      | 类                                | 源码                                                                         |
| --------- | -------------------------------- | -------------------------------------------------------------------------- |
| Intent    | `IntentNeuroDomain`              | `app/neuro_bus/domains/intent_domain.py`                                   |
| Order     | `OrderNeuroDomain`               | `app/neuro_bus/domains/order_domain.py`                                    |
| Inventory | `InventoryNeuroDomain`           | `app/neuro_bus/domains/inventory_domain.py`                                |
| Product   | `ProductNeuroDomain`             | `app/neuro_bus/domains/product_domain.py`                                  |
| Customer  | `CustomerNeuroDomain`            | `app/neuro_bus/domains/customer_domain.py`                                 |
| AIService | `AIServiceNeuroDomain`           | `app/neuro_bus/domains/ai_service_domain.py`                               |
| Wechat    | `WechatNeuroDomain`              | `app/neuro_bus/domains/wechat_domain.py`                                   |
| Print     | `PrintNeuroDomain`               | `app/neuro_bus/domains/print_domain.py`                                    |
| OCR       | `OCRNeuroDomain`                 | `app/neuro_bus/domains/ocr_domain.py`                                      |
| Payment   | `PaymentNeuroDomain`             | `app/neuro_bus/domains/payment_domain.py`                                  |
| Safety    | `SafetyNeuroDomain`              | `app/neuro_bus/domains/safety_domain.py`                                   |
| Shipment  | `ShipmentNeuroDomain` + handlers | `app/neuro_bus/domains/shipment_domain.py` / `shipment_domain_handlers.py` |
| 注册        | `register_all_neuro_domains`     | `app/neuro_bus/register_all_neuro_domains.py`                              |
| 稳定 import | `app.neuro_domains`              | `app/neuro_domains/__init__.py`                                            |


#### 2.2 神经科学启发的核心组件（摘录）

意图栈已实现于 `**app/domain/neuro/`**（`SubconsciousProcessor`、`ConsciousProcessor`、`IntentReflexArc`、`ProcessorCoordinator`）。下文为能力摘要。

##### IntentNeuroDomain - 双模式意图识别引擎

```python
# 潜意识处理器 - <10ms 快速响应
class SubconsciousProcessor:
    Level 1: 缓存命中 (<1ms)
    Level 2: 规则匹配 (<5ms)
    Level 3: 关键词匹配 (<10ms)

# 显意识处理器 - 99%+ 准确率
class ConsciousProcessor:
    Level 1: BERT 语义分析 (~50ms)
    Level 2: DeepSeek 深度推理 (~150ms)
```

##### 神经反射弧 (Reflex Arc)

```python
class IntentReflexArc:
    """预定义模式的超快速响应，类似人体膝跳反射"""
    REFLEX_PATTERNS = {
        "greeting":      简单问候 → 即时回复 (<1ms)
        "emergency.stop": 紧急停止 → 立即中止 (<1ms)
        "confirmation.yes/no": 确认/取消 → 快速响应 (<1ms)
    }
```

##### NeuroUnitOfWork - 神经工作单元

实现见 `app/domain/neuro/neuro_uow.py`：`NeuroUnitOfWork` 封装 SQLAlchemy `Session` 的 commit/rollback，并可选用 `NeuroBus` 发布领域事件。

##### NeuroBus - 神经总线 (8 大可靠性机制)

生产类名为 `**NeuroBus**`（`app/neuro_bus/bus.py`）；异步由 `asyncio` 处理循环实现。文档旧称 `AsyncNeuroBusImpl` 已废弃。


| 机制      | 模块                              | 启用变量（`1`/`true`/`on`）        |
| ------- | ------------------------------- | ---------------------------- |
| 链路追踪    | `tracer.py`                     | `XCAGI_NEURO_BUS_TRACE`      |
| 去重      | `deduplicator.py`               | `XCAGI_NEURO_BUS_DEDUP`      |
| 限流      | `rate_limiter.py`               | `XCAGI_NEURO_BUS_RATE_LIMIT` |
| 熔断      | `circuit_breaker.py`            | `XCAGI_NEURO_BUS_CIRCUIT`    |
| SLA 日志  | `sla_controller.py`             | `XCAGI_NEURO_BUS_SLA_LOG`    |
| 保命通道    | `lifeline.py`                   | `XCAGI_NEURO_BUS_LIFELINE`   |
| 死信自动入队 | `dead_letter_queue.py`（handler 异常写入全局 DLQ） | `XCAGI_NEURO_BUS_DLQ_AUTO` |
| 重试 / 沙盒 | `retry_handler.py`、`sandbox.py` | 业务按需调用；默认不挂入总线 publish       |


```text
NeuroBus：生产级异步事件总线；上表为可选 publish/分发增强。
```

#### 2.3 神经域详解


| 神经域                      | 职责       | 核心能力                                        |
| ------------------------ | -------- | ------------------------------------------- |
| **IntentNeuroDomain**    | 意图识别     | 双模式引擎 + 神经反射弧                               |
| **OrderNeuroDomain**     | 订单域      | 状态机管理 + 工作流编排                               |
| **InventoryNeuroDomain** | 库存管理     | NeuroUnitOfWork 事务 + 预留/扣减                  |
| **ProductNeuroDomain**   | 产品管理     | Fan-Out/Fan-In 并行处理                         |
| **CustomerNeuroDomain**  | 客户管理     | 联系人同步 + 层级管理                                |
| **AIServiceNeuroDomain** | AI 服务    | 多引擎调度 + 负载均衡                                |
| **WechatNeuroDomain**    | 微信集成     | 消息处理 + 联系人同步                                |
| **PrintNeuroDomain**     | 打印服务     | 标签生成 + 任务队列                                 |
| **OCRNeuroDomain**       | OCR 识别   | 多引擎支持 (PaddleOCR/EasyOCR)                   |
| **PaymentNeuroDomain**   | 支付管理     | 价格计算 + 退款处理                                 |
| **SafetyNeuroDomain**    | 安全域      | 一致性检查 + 熔断保护                                |
| **ShipmentNeuroDomain**  | 出货 / 发货单 | 与 `shipment_domain_handlers` 事件对齐的域级指标与扁平订阅 |


---

### 3）XCAGI 子工程：运行入口与分层表（与 `XCAGI/README.md` 一致）


| 层级 / 组件         | 代码落点                                                                                        | 说明                                                                                                                              |
| --------------- | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| **HTTP 入口（默认）** | `**XCAGI/run.py`**                                                                          | `uvicorn` 加载 `**app.fastapi_app:get_fastapi_app`**（`factory=True`），默认 `**0.0.0.0:5000**`；热重载默认开启，可设 `XCAGI_UVICORN_RELOAD=0` 关闭 |
| **FastAPI 应用**  | `**app/fastapi_app.py`**                                                                    | `lifespan` 内初始化 NeuroBus、数据库等；注册 `**app/fastapi_routes/`** 与 `**app/fastapi_compat_routes**`                                    |
| **装配根**         | `**app/bootstrap.py`**                                                                      | `@lru_cache` 将 **application** 与 **infrastructure** 接线                                                                          |
| **应用服务**        | `**app/application/`**                                                                      | 用例编排                                                                                                                            |
| **领域层**         | `**app/domain/`**                                                                           | 领域规则                                                                                                                            |
| **基础设施**        | `**app/infrastructure/`**                                                                   | 持久化与外部系统                                                                                                                        |
| **历史兼容路由**      | `**app/fastapi_routes/`** 内的 `xcagi_compat`、`archive_gap_batch*`、`miniprogram`、`approval` 等 | 原 `backend.routers.*` 2026-04-20 起已迁至此处,统一由 `app.fastapi_routes.register_all_routes` 挂载                                         |


**OpenAPI**: `http://localhost:5000/docs` 或 `/redoc`。  
**前端静态资源**：由根目录 `**frontend/`** 构建；Vite 默认输出至 `**templates/vue-dist/`**（见 `frontend/vite.config.js`），生产可由反向代理或容器 `**frontend**` 服务托管；当前 `**app/fastapi_app.py` 未挂载** 一体化 SPA 静态目录，勿依赖文档中已废弃的 `XCAGI_SPA_ROOT_MOUNT` 叙事。

---

## 🚀 三大产品路线（概览）


| 路线         | 说明                    | 典型落点                                   |
| ---------- | --------------------- | -------------------------------------- |
| **Mod 仓库** | 扩展功能与行业包，核心尽量不 fork   | `mods/`、`/api/mod-store/`*、Mod Manager |
| **小程序**    | 移动侧 CRM / 单据能力        | `/api/mp`* 族接口、`miniprogram/`          |
| **传统模式**   | 类资源管理器 + 表格工作流，降低上手成本 | 前端「传统模式」视图与对应 API（以 OpenAPI 为准）        |


---

## 🎯 AI 员工核心能力

### 🧠 AI 智能决策

- **LLM 工作流规划**（DeepSeek 等）与工具调用闭环
- 混合意图识别（规则 + NLU + 模型，随部署变化）
- 业务确认流、风险门与工作流中断恢复（见运行时与 OpenAPI）

### 🔄 全自动化处理

- 单据解析 → 结构化 → 写库 / 出单 / 打印链路
- 异常与重试策略（HTTP 层、LLM 与任务队列按部署启用）

### 💬 多模态交互

- 对话、TTS、微信与打印等通道按模块启用

### 🏢 行业与模板

- 多行业模板与 Mod 覆盖

---

## 🏢 适用行业与场景

### 🏭 制造业

- 生产单据、物料标签、出货与质检记录

### 🚚 物流与批发

- 快递/批发单据、签收、价格与出货追踪

### 🛒 零售与电商

- 进货、价签、库存与发货协同

---

## 📊 AI 员工 vs 传统工具


| 维度      | 传统工具  | XCAGI AI 员工             | 优势         |
| ------- | ----- | ----------------------- | ---------- |
| **架构**  | 脚本/单体 | **Neuro-DDD + FastAPI** | 分层清晰、可替换实现 |
| **决策**  | 无     | 对话 + 工作流                | 可编排、可审计    |
| **交互**  | 表单为主  | 对话 + 业务 UI              | 降低重复操作     |
| **自动化** | 半自动   | 端到端链路                   | 减少人工拷贝     |
| **扩展**  | 改核心   | **Mod**                 | 行业包隔离      |


---

## ⚡ 性能指标

下表为版本迭代中的**内部对比与目标取向**（环境、模型与数据不同会导致差异），非第三方审计 SLA。


| 指标       | v3.0  | v4.0  | v5.0              | v6.0                         | v7.0                                      | v8.0                                      |
| -------- | ----- | ----- | ----------------- | ---------------------------- | ----------------------------------------- | ----------------------------------------- |
| 前端加载（典型） | ~1.5s | ~1.0s | ~0.8s             | **~0.6s**                    | **与 v6 同栈；桌面壳内嵌同一 Vue 构建**            | **同 v7；行业预设按需加载**                     |
| 意图与对话延迟  | 秒级    | 优化    | <1ms 反射弧 + 云端 LLM | **显著依赖模型与路由**                | **同左**                                     | **同左**                                     |
| 行业适配     | 手动配置  | 配置化   | Mod / 模板 + 策略     | **Mod 商店 + 开发者分成**           | **同左**                                     | **行业预设 + Mod 行业选择**                      |
| 交付形态     | Web   | Web   | Web               | Web                          | **Web + Windows/macOS 安装包（Electron）**   | **同 v7**                                   |
| 商业化      | —     | —     | —                 | **本地部署 + Mod 商店 + Token 钱包** | **同左**                                     | **同左**                                     |


---

## 🔧 系统要求

- Windows 10/11 或 Linux（以实际部署为准）
- Python 3.11+
- PostgreSQL 16+（推荐，含 pgvector）或按迁移支持的 DB
- Redis（缓存 / 队列，按场景）
- Docker & Docker Compose（可选，推荐生产）

---

## 🚀 快速开始

### 克隆本仓库（一体化树）

```bash
git clone https://github.com/42433422/ai-excel-helper.git
cd ai-excel-helper
```

（历史文档中若出现 `xcagi` 仓库名，多为同源发行说明；**以你实际推送的远程为准**。）

### 方式 1：Docker（若提供 compose）

```bash
docker-compose up -d --build
docker-compose ps
```

### 方式 2：本地 Python

```bash
pip install -r requirements.txt
alembic upgrade head
cd XCAGI && python run.py
```

浏览器打开：**[http://127.0.0.1:5000/docs](http://127.0.0.1:5000/docs)**。（`backend.http_app:8000` 已于 2026-04-20 随 `backend/` 一同下线,备份在 `.archive/legacy-backend-2026-04-final/`。）

### 方式 3：Windows 部署脚本

若仓库根目录提供 `deploy.bat` / `deploy-release.bat`，可按脚本菜单选择生产或开发配置。

---

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────────────┐
│           用户界面层 (Vue 3 + Vite + TypeScript)                      │
│     对话 / 单据 / 打印 / Pro Mode / 工作流 / 读库门禁                  │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│     API 层（FastAPI，`app.fastapi_app` + `app/fastapi_compat_routes`） │
│     业务 Router + 兼容层 + CORS + 审计/限流（如有）                    │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Neuro-DDD（`app/`：分层 + 用例编排）                       │
├─────────────────────────────────────────────────────────────────────┤
│  FastAPI 路由(`app/fastapi_routes/`,含历史兼容子集)→              │
│  `application`（用例）→ `domain`（规则）→ `infrastructure`（实现）   │
│  装配：`app/bootstrap.py`                                           │
└─────────────────────────────────────────────────────────────────────┘
                │                              │
                ▼                              ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│ LLM / OCR / 工具执行       │    │ PostgreSQL / Redis / 文件   │
└──────────────────────────┘    └──────────────────────────┘
```

---

## 💻 技术栈详情

### 后端技术


| 技术                 | 版本     | 用途                      |
| ------------------ | ------ | ----------------------- |
| **Python**         | 3.11+  | 核心语言                    |
| **FastAPI**        | 0.110+ | **唯一 Web 与 OpenAPI 入口** |
| **Uvicorn**        | -      | ASGI 服务器                |
| **SQLAlchemy**     | 2.0+   | ORM                     |
| **Alembic**        | 1.13+  | 迁移                      |
| **Celery / Redis** | 按场景    | 异步任务与缓存                 |
| **PostgreSQL**     | 16+    | 生产库（含 pgvector）         |


### AI / 数据


| 技术                         | 用途           |
| -------------------------- | ------------ |
| **DeepSeek 等 LLM**         | 对话、规划、工具调用   |
| **RASA / BERT / 蒸馏**       | NLU 与意图（按部署） |
| **PyTorch / Transformers** | 模型推理         |
| **PaddleOCR / EasyOCR**    | OCR          |
| **OpenPyXL / Pandas**      | Excel 与表格    |


### 前端技术


| 技术                     | 用途    |
| ---------------------- | ----- |
| **Vue 3 + Vite + TS**  | SPA   |
| **Pinia / Vue Router** | 状态与路由 |


---

## 🎯 AI 员工核心场景（示例）

### 标签打印

用户上传 Excel → 解析 → 模板/标签 → 打印队列。

### 出货管理

识别订单文本或表格 → 预览 → 确认 → 出货记录与打印。

### 收货与库存

单据核对 → 库存更新（以实际模块与权限为准）。

### 微信与对话

消息接入 → 意图 → 工具或业务流程（按启用模块）。

---

## 📡 API 接口（摘录）

完整列表以 **OpenAPI** 为准（`/docs`）。

- `/api/health` — 健康检查  
- `/api/chat`、`/api/chat/stream` — 对话与流式输出  
- `/api/upload/`* — 上传与运行时上下文  
- `/api/template`、`/api/word/`*、`/api/excel/*` — 模板与文档处理  
- `/api/fhd/*` — 身份、读库令牌、AI 策略等  
- `/api/mod-store/*` — 模块市场相关  
- `/api/*`（兼容路由）— 旧版路径族

---

## 🔄 版本演进

### v8.0（当前主线）

- **版本与锚点、发版自检、Git/GitHub 行为**：已上收至前文 **[版本与发布约定](#version-policy)**（与 [`VERSION.md`](VERSION.md) 对齐），请勿在本小节重复改版本号表。
- **跨行业 UI 适配**：宿主菜单/欢迎语/快捷按钮随所选行业切换；Mod 制作端可指定目标行业。
- **延续 v7 桌面交付与 v6 商业化**：Windows/macOS 安装包（Electron 壳 + 本地 FastAPI 子进程 + 与 Web 同源 Vue 资源），与 Docker / 本地 `run.py` 并行；本地部署授权、Mod 商店分成、Token 认证钱包；Manifest 与路由契约不变。

### v7.0

- **桌面交付**：Windows / macOS 安装包（Electron 壳 + 本地 FastAPI 子进程 + 与 Web 同源 Vue 资源），与 Docker / 本地 `run.py` 并行。
- **延续 v6 商业化与 Mod 生态**：本地部署授权、Mod 商店分成、Token 认证钱包；Manifest 与路由契约不变。

### v6.0

- **商业模式明确**：本地部署授权 + Mod 商店分成（70/30） + Token 认证钱包（按量计费）三层收入结构  
- **Mod 生态**：员工商店、Manifest v2、热插拔、行业配置覆盖；已有 `sz-qsm-pro`、`taiyangniao-pro` 等行业包  
- **Token 钱包 / 防绕过**：核心 AI 能力云端化、License 验证、API 签名校验  
- **可观测与并发**：目标 ~~0.6s 前端加载、~~99.5% 意图准确率、99.9% 可用性、2000 QPS 目标  
- **文档体系统一**：`[BUSINESS_MODEL.md](BUSINESS_MODEL.md)`（如提供）、`[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)`、本 `README.md` 与 `[CHANGELOG.md](CHANGELOG.md)` 同口径

### v5.0

- **FastAPI 主入口**：`XCAGI/run.py` → `app.fastapi_app:get_fastapi_app`；原 `backend/` 所有路由与支持模块已于 2026-04-20 全量迁入 `app/`，旧目录删除  
- **Neuro-DDD 分层**：`app/application`、`app/domain`、`app/infrastructure` + `app/bootstrap.py` 装配  
- **模块生态（基础）**：MODstore、Mod Manager、前后端 Mod 路由注册  
- **读库鉴权与门禁**：前端令牌提示与 API 协同  
- **工作流与 Pro Mode UI**：可视化与员工站组件  
- **隐私与安全发布**：移除数据库与大文件敏感物，公开仓库可审计

### v4.0 及更早

- AI 员工定位、自动化流程、多模态、DDD 演进等（见 `[CHANGELOG.md](CHANGELOG.md)`）。

---

## 📊 技术栈演进对比


| 组件    | v1.0 | v2.0 | v3.0     | v4.0       | v5.0            | v6.0                  | v7.0                         | **v8.0**                         |
| ----- | ---- | ---- | -------- | ---------- | --------------- | --------------------- | -------------------------------- | -------------------------------- |
| 定位    | 工具   | 智能系统 | 智能系统     | AI 员工      | AI 员工 + 模块生态    | 企业 AI 员工平台            | + 桌面安装版（Electron）          | **+ 跨行业 UI 适配**              |
| 主 API | -    | -    | Flask 为主 | Flask + 演进 | FastAPI 唯一入口    | FastAPI + Token 签名    | 同 v6                          | **同 v7**                          |
| 架构    | 单文件  | MVC  | DDD      | DDD+       | Neuro-DDD + 兼容层 | Neuro-DDD + Mod 生态 v2 | 同 v6                          | **同 v7**                          |
| 扩展    | ❌    | ❌    | ❌        | 有限         | Mod / Mod Store | Mod 商店 + 开发者分成        | 同 v6                          | **+ 行业预设**                    |
| 商业化   | ❌    | ❌    | ❌        | ❌          | 未明确             | 本地部署 + Mod + Token    | 同 v6                          | **同 v7**                          |


---

## ⚠️ 注意事项

**隐私**: 数据库文件、密钥与大体积私有资源勿提交；以 `.gitignore` 与发布检查清单为准。

**安全**: API Key 与数据库凭据使用环境变量；生产环境务必 HTTPS 与最小权限。

---

## 🤝 贡献指南

1. Fork **[ai-excel-helper](https://github.com/42433422/ai-excel-helper)**
2. 新建分支 `feature/...`
3. 提交并推送后开启 Pull Request

开发环境示例：

```bash
git clone https://github.com/42433422/ai-excel-helper.git
cd ai-excel-helper
pip install -r requirements.txt
pytest
```

详见 [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md)。

---

## 📚 文档资源

- [快速开始](docs/QUICK_START.md)  
- [架构](docs/ARCHITECTURE.md)  
- [AI 员工配置](docs/AI_EMPLOYEE.md)  
- [CHANGELOG](CHANGELOG.md)  
- [SECURITY](SECURITY.md)  
- [部署](docs/DEPLOYMENT.md)  
- 在线 API：`http://127.0.0.1:5000/docs`（默认端口已统一为 5000）

---

## 🗺️ 路线图（节选）

- FastAPI 主入口与兼容层  
- Neuro-DDD 分层与 Mod 生态  
- 更广覆盖的自动化测试与 CI  
- 国际化与更多行业模板

---

## 🙏 致谢

[Vue.js](https://vuejs.org/)、[FastAPI](https://fastapi.tiangolo.com/)、[Uvicorn](https://www.uvicorn.org/)、[SQLAlchemy](https://www.sqlalchemy.org/)、[DeepSeek](https://www.deepseek.com/)、[RASA](https://rasa.com/)、[Hugging Face](https://huggingface.co/) 等开源项目。

---

## 📄 许可证

**AGPL-3.0** — 详见 [LICENSE](LICENSE)。

---

## 📬 联系方式

- **作者**: [@42433422](https://github.com/42433422)  
- **Issues**: [ai-excel-helper Issues](https://github.com/42433422/ai-excel-helper/issues)

---

**XCAGI v8.0 — 企业 AI 员工平台（Neuro-DDD + FastAPI + Mod 生态 + 可选桌面版 + 跨行业适配）**

[🔝 返回顶部](#-项目简介)