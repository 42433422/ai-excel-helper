# 通用化 XCAGI 宿主壳（阶段 4）

## 原则

| 概念 | 放哪里 |
|------|--------|
| **Mod（房子）** | 行业包、桥接包、含菜单/路由的业务扩展 |
| **员工（家具）** | `workflow_employees` 或 `employee_pack` 内单名员工 |
| **宿主壳** | 启动、ModManager、`app/mod_sdk`、本文件所列 API |

新业务 **不得** 再往 `frontend/src/data/workflow-employees.json` 写死员工；应做 Mod 或 `employee_pack`。

## 宿主保留 API（底座）

见 `app/mod_sdk/platform_shell.py` → `PLATFORM_SHELL_API_PREFIXES`。

## 桥接 Mod（边界标记，逻辑仍在宿主）

| Mod id | 宿主 API |
|--------|----------|
| `xcagi-approval-bridge` | `/api/approval/*` |
| `xcagi-lan-license-bridge` | `/api/lan/*` |
| `xcagi-model-payment-bridge` | `/api/model-payment/*` |
| `xcagi-planner-bridge` | `/api/ai/chat`, `/api/ai/intent` |

## 受保护客户 Mod

`taiyangniao-pro`、`sz-qsm-pro` — 见平台 [PROTECTED_MODS.md](../../../成都修茈科技有限公司/mods/PROTECTED_MODS.md)。

## 查询能力清单

```http
GET /api/platform-shell/capabilities
```

前端：`fetchPlatformShellCapabilities()`（`@/utils/platformShellApi`）。

## ADCDFG 全量完成（2026-05-22）

- 计划：[ADCDFG_COMPLETION_PLAN.md](./ADCDFG_COMPLETION_PLAN.md)
- 默认发行：`npm run build` = **generic**；桌面/安装包默认 **generic** 壳
- 一键装包：`POST /api/mod-store/bootstrap-edition-pack?edition=generic`
- 验收：`powershell -File scripts/dev/adcdfg_acceptance.ps1`

## 前端壳模式（里程碑 A / D）

启用后侧栏只保留：**智能对话、扩展市场、设置、员工空间、Mod 菜单**；内置产品/出货/考勤等业务页隐藏。

| 方式 | 说明 |
|------|------|
| **里程碑 I 推荐** | `cd frontend && npm run build:generic`（加载 `.env.generic`） |
| **里程碑 Q 推荐** | `cd frontend && npm run build:minimal`（加载 `.env.minimal`，空壳：对话 + Mod 市场 + 设置） |
| 通用发行构建 | `VITE_XCAGI_DEFAULT_PLATFORM_SHELL=1`（见 `frontend/.env.example` / `.env.generic`） |
| 构建 | `VITE_XCAGI_PLATFORM_SHELL=1` |
| URL | `?shell=1` 开启；`?full=1` 临时完整 ERP |
| 存储 | `localStorage.xcagi_platform_shell_mode=1`（通用版首次启动自动写入） |
| 设置页 | 系统设置 → 平台壳模式开关 |
| 自动 | 安装 `planner-bridge` + `erp-domain-bridge` + `core-workflow-employees` 且非仅太阳鸟部署 |

## 三档 edition（里程碑 Q）

| edition | 构建 | 默认 Mod 包 | 体感 |
|---------|------|-------------|------|
| `minimal` | `npm run build:minimal` / `XCAGI_MINIMAL_EDITION=1` | planner + neuro-bus + office-employee-pack | 空壳：对话、Mod 市场、设置；无 ERP 侧栏 |
| `generic` | `npm run build:generic` / `XCAGI_GENERIC_EDITION=1` | 9 个通用 bridge Mod | OpenClaw 式通用行业包 |
| `full` | 默认构建 | 已安装全部 Mod | 完整 ERP + 扩展 |

后端：`GET /api/platform-shell/capabilities` 与 `decoupling-progress` 返回 `edition`、`minimal_mod_ids`、`generic_pack_mod_ids`。

**宿主壳核心路由**（允许留在宿主）：`chat`（重定向 Mod 对话）、`mod-store`、`settings`、`workflow-employee-space`、`desktop-runtime`。

路由守卫会把访问内置业务页重定向到聊天页；**里程碑 K/O+** 起若已安装对应 bridge Mod，则重定向到 `/mod/<id>/...`（**O+** 组件来自 `mods/<id>/frontend/views/`，宿主 `views/` 为薄 shim）。

## 解耦完成度（2026）

- 核心工作流、横切桥接、Planner 门面、NeuroBus 边界 Mod 已上架源码库
- **壳模式**可切换；`npm run build:generic` 或 `VITE_XCAGI_DEFAULT_PLATFORM_SHELL=1` 时默认即为通用壳
- **主对话**（里程碑 P）：物理视图在 `xcagi-planner-bridge`；安装门面且 `xcagi_planner_mod_facade_enabled=1` 时访问 `/` 重定向到 `/mod/xcagi-planner-bridge/chat`
- 工具**执行**与 NeuroBus **总线**仍在宿主；新业务请走 Mod 或 `employee_pack`
- ERP 领域 API 见 [ERP_DOMAIN_MOD.md](./ERP_DOMAIN_MOD.md)（里程碑 C）
- Repository 装配见 `app/mod_sdk/erp_repository_registry.py`（里程碑 L/L+，`repository_via_mod` + `Mod*RepositoryAdapter`）

## 全量解耦进度

[DECOUPLING_ROADMAP.md](./DECOUPLING_ROADMAP.md)
