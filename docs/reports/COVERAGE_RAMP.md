# 覆盖率分阶段提升与补测清单

本文档与根目录及 `XCAGI/pyproject.toml` 中的 `tool.coverage.report.fail_under` 对齐，作为**分阶段提高门槛**的操作说明（避免一次性提到 80% 导致 CI 长期失败）。

## 阶段目标

| 阶段 | `fail_under` 目标 | 说明 |
|------|-------------------|------|
| CI 门禁（稳定子集） | **25** | `CI_STABLE_ONLY=1` + 多包 `--cov=app.neuro_bus` 等（约 26% 实测） |
| 本地全量目标 | **60→80** | 阶段 B–D；全量 `pytest tests/` 须先清零失败用例 |
| 目标 | **80** | 阶段 D；当前与目标差距见 CI `cov-fail-under` |
| A | ~~55~~ | 已完成 |
| B | **60** | 扩展 `tests/test_coverage_ramp_routes.py`、基础设施单测 |
| B | **60** | 补齐 `app/infrastructure` 仓储与模板路径 |
| C | **70** | 扩展 `app/domain` 聚合与值对象 |
| D | **80** | 接近「关键路径全覆盖」；按需调整 `omit` |

每进入下一阶段前：在本地与 CI 执行 `pytest tests/ --cov=app --cov-report=term-missing`，确认全绿后再改 `fail_under`。

## 补测优先级（建议顺序）

### P0 — 变更频繁、故障代价高

1. **`app/application/`** — 应用服务编排（发货、任务、AI 聊天等已有部分测试，继续补分支与异常路径）。
2. **`app/neuro_bus/bus.py`** — 发布、队列满、可选可靠性层与环境变量组合（已有 `tests/test_neuro_bus_core.py`、`tests/test_neuro_bus_reliability_env.py`，可扩展 DLQ 自动入队等）。

### P1 — 领域规则

3. **`app/domain/shipment`**（及关联聚合）— 与 `tests/test_domain/` 已有用例对齐，补边界条件。
4. **`app/domain`** 其他包 — 按业务变更频率轮流加测。

### P1 — 基础设施

5. **`app/infrastructure/`** — 模板存储、SQLite 专用分支、与 Mod 相关的 DB 辅助函数（注意测试隔离与临时目录）。

### P2 — 路由与集成

6. **`app/fastapi_routes/`** — 对未覆盖路由补 FastAPI `TestClient` 用例；与 `tests/test_routes/` 已有模式一致。

## 配置位置

- 根目录：[`pyproject.toml`](../../pyproject.toml) → `[tool.coverage.report]` → `fail_under`
- XCAGI 子树：[`XCAGI/pyproject.toml`](../../XCAGI/pyproject.toml)（与根保持同数值，便于子树独立检出时一致）

## pytest 与路径说明

本地默认从仓库根运行：

```bash
python -m pip install -r XCAGI/requirements.lock.txt pytest pytest-cov
# CI 稳定子集（与 workflow 一致）
CI_STABLE_ONLY=1 python -m pytest tests/ \
  --cov=app.neuro_bus --cov=app.middleware --cov=app.fastapi_routes \
  --cov=app.utils.rate_limiter --cov=app.utils.password_hash --cov=app.config \
  --cov-fail-under=25
# 全量回归（含 700+ 用例，本地可能有个别失败需逐个修）
python -m pytest tests/ --cov=app --cov-report=term-missing
```

若 CI 使用其他 `testpaths`，以该 workflow 为准，但 **`fail_under` 数值应与本文阶段表同步更新**。

## 前端类型检查（CI）

`.github/workflows/test.yml` 已增加 `npm run type-check`（`vue-tsc`），当前为 **`continue-on-error: true`**：待清零存量 TS 报错后改为硬失败，与 `frontend/tsconfig.json` 的 `strict: true` 形成闭环。

## 前端单测与 E2E（CI）

| Workflow | Job | 命令 |
|----------|-----|------|
| [`test.yml`](../../.github/workflows/test.yml) | `frontend-build` | `npm run test`、`npm run test:coverage`（Vitest 阈值 lines **18%**→40%；`CI=true` 时跳过依赖 Mod 的 ChatView 用例） |
| [`test.yml`](../../.github/workflows/test.yml) | `frontend-e2e` | 启动 FastAPI `:5000` + Vite preview `:5001`，`npm run test:e2e`（smoke / core-business / login-flow / navigation） |
| [`ci-cd.yml`](../../.github/workflows/ci-cd.yml) | `frontend-test`、`frontend-e2e` | 与上表一致，合并 PR 到 main 时必跑 |

本地 E2E：`python XCAGI/run.py` + `cd frontend && npm run build && npm run preview`，另开终端 `npm run test:e2e`。
