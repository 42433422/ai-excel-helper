# FHD (XCAGI) 项目深度评估报告（修订版）

> 评估日期：2026-05-03  
> 评估范围：`FHD` 仓库根目录 `app/`、`frontend/`、`k8s/`、`pyproject.toml` 等  
> 修订说明：对照源码核实后，更正原报告中与事实不符或过度概括的表述；保留经核实的结论。

---

## 一、测试体系（仍为短板，但表述需更新）

### 1.1 覆盖率门槛

**证据**：根目录 [`pyproject.toml`](../../pyproject.toml) 与 [`XCAGI/pyproject.toml`](../../XCAGI/pyproject.toml) 中 `[tool.coverage.report]` 的 `fail_under`（当前 **52%**）。

**结论**：门槛偏低、近半代码未强制覆盖的风险判断**仍然成立**。

### 1.2 测试布局（更正原报告）

原报告列举的 `tests/` 树**不完整**。除 `test_db/`、`test_tasks/` 等外，还存在例如：

- `tests/test_domain/`、`tests/test_application/`、`tests/test_infrastructure/`
- `tests/test_routes/`、`tests/test_services/`、`tests/neuro/` 等

**结论**：后端并非「仅有若干顶层用例」，但**领域与基础设施的覆盖深度仍可加强**（与分阶段提覆盖率计划一致）。

### 1.3 前端与 E2E（更正原报告）

原报告称「`frontend/` 无任何测试」「无 E2E」**不成立**。

**依据**：

- [`frontend/package.json`](../../frontend/package.json)：`test`（Vitest）、`test:e2e`（Playwright）
- [`frontend/vitest.config.js`](../../frontend/vitest.config.js)、`frontend/e2e/smoke.spec.ts` 及多处 `*.test.ts` / `*.test.js`

**更准确结论**：

- 前端已有 **Vitest + @vue/test-utils** 与 **Playwright** 烟测；CI 中前端单测曾为 `continue-on-error`（见 `.github/workflows/test.yml`），**门禁强度不足**，而非「完全缺失」。
- 类型侧：[`frontend/tsconfig.json`](../../frontend/tsconfig.json) 已启用 **`"strict": true`**；短板是 **mypy 不检查 `frontend/`**，应在 CI 中强化 **`vue-tsc` / `npm run type-check`**。

### 1.4 建议（保留方向，调整措辞）

| 优先级 | 动作 |
|--------|------|
| P0 | 分阶段提高 `fail_under`，并维护补测清单（见 [`COVERAGE_RAMP.md`](COVERAGE_RAMP.md)） |
| P0 | CI 将前端 `test` / `type-check` 从「可选失败」改为稳定门禁（分步启用） |
| P1 | 扩展 Playwright 覆盖核心业务流 |

---

## 二、NeuroBus（可选层默认关闭 — 成立；DLQ/背压 — 细化）

### 2.1 可靠性层与环境变量

**证据**：[`app/neuro_bus/bus.py`](../../app/neuro_bus/bus.py) 中 `_rel_*` 默认 `None`，由 `XCAGI_NEURO_BUS_*` 等环境变量在构造期启用。

**结论**：「文档式多机制、运行时默认关闭」**成立**；README 已说明为可选 publish/分发增强，需避免对外宣传为「默认全开」。

### 2.2 死信队列（更正原报告）

原报告「死信队列未实现」**不准确**。

- 实现见 [`app/neuro_bus/dead_letter_queue.py`](../../app/neuro_bus/dead_letter_queue.py)，[`initializer.py`](../../app/neuro_bus/initializer.py) 会初始化 DLQ。
- **原报告合理之处**：主总线在 handler 异常路径上曾**未自动入队**；现已通过环境变量 **`XCAGI_NEURO_BUS_DLQ_AUTO`** 可选打通（见 README 与 `bus.py`）。

### 2.3 背压（收窄表述）

[`PriorityEventQueue`](../../app/neuro_bus/bus.py) 具备 `max_size`（默认 10000）及队列满时丢弃/替换低优先级等策略，**并非完全无界队列**。

**结论**：仍可讨论 SLA、丢弃策略与监控是否足够，但不宜写「完全无背压」。

---

## 三、数据库架构（SQLite / 多库 — 成立）

**证据**：[`app/fastapi_app.py`](../../app/fastapi_app.py) 中 `_initialize_databases_sync` 对 SQLite 调用 `ensure_sqlite_per_mod_database_copies`；[`app/db/session.py`](../../app/db/session.py) 中 `get_db()` 使用全局 `SessionLocal`。

**结论**：桌面 SQLite、多文件与跨库一致性风险等判断**仍可保留**；原报告中函数名 `is_sqlite_url` 应为 **`_is_sqlite_url`**（笔误）。

---

## 四、Python 类型系统（mypy — 成立）

**证据**：[`pyproject.toml`](../../pyproject.toml) 中 `ignore_missing_imports = true` 且 `exclude` 含 `frontend`。

**结论**：后端类型宽松、前端不在 mypy 范围内**成立**；与「前端未开 strict」**不矛盾** — 前端 strict 在 `tsconfig.json`，mypy 不覆盖前端源码。

---

## 五、遗留与双入口（成立）

**证据**：[`app/bootstrap.py`](../../app/bootstrap.py) 中 `get_shipment_application_service_core` / `get_shipment_app_service`；[`app/fastapi_app.py`](../../app/fastapi_app.py) 注释中 `register_all_routes` 合并历史兼容路由。

---

## 六、安全与可观测性（部分收窄）

### 6.1 速率限制

[`app/fastapi_app.py`](../../app/fastapi_app.py) **未**注册全站 SlowAPI 式中间件，**成立**。

同时存在 [`app/utils/security_middleware.py`](../../app/utils/security_middleware.py) 的 `api_security(..., rate_limit=...)` 与内存限流 [`app/utils/rate_limiter.py`](../../app/utils/rate_limiter.py)。

**更准确结论**：缺**统一、分布式（如 Redis）全局限流**时，多实例与爬虫场景仍薄弱；详见 [`../guides/RATE_LIMITING.md`](../guides/RATE_LIMITING.md)。

### 6.2 日志

默认 `logging.basicConfig` 文本格式**成立**；结构化日志仍为改进项。

---

## 七、部署与 K8s（更正原报告）

原报告「无 readiness/liveness 探针」**不成立**。

**证据**：[`k8s/deployment.yaml`](../../k8s/deployment.yaml) 已配置 `livenessProbe` / `readinessProbe`（`/health/liveness`、`/health/readiness`）。

**仍可改进**：Helm Chart、告警规则 CI 校验、Grafana 仪表盘等（与原报告 P2 方向一致）。

---

## 八、依赖锁定（成立）

根目录无 **`poetry.lock` / `uv.lock`** 的**可重复构建**叙事**成立**；落地方式见 [`../guides/DEPENDENCY_LOCKS.md`](../guides/DEPENDENCY_LOCKS.md)。

---

## 九、性能基准（方向成立）

README 中的性能数字若无自动化复现，仍建议 Locust/k6/Lighthouse CI 等门禁；与 [`capacity-planning.md`](capacity-planning.md) 等文档对齐。

---

## 十、核实摘要表

| 原报告条目 | 修订后 |
|------------|--------|
| 前端无任何测试 | **有误**：已有 Vitest/Playwright，需强调 CI 门禁 |
| 无 E2E | **有误**：存在 `frontend/e2e/` |
| 死信未实现 | **有误**：有实现；曾缺总线自动入队，已用 `XCAGI_NEURO_BUS_DLQ_AUTO` 可选补齐 |
| 无背压 | **过宽**：有界队列与丢弃策略 |
| K8s 无探针 | **有误**：`deployment.yaml` 已配置 |
| TS 未 strict | **部分有误**：`tsconfig.json` 已 `strict: true` |
| 无 API 限流 | **收窄**：有路由级内存限流，缺全站/Redis 中间件 |
| fail_under 52、mypy、SQLite、双入口、无 lockfile | **维持成立** |

---

*修订归档：与计划「FHD 评估报告核实与后续改进」对齐；请勿编辑本文件作为计划正文回写。*
