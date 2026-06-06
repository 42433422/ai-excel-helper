# 文档地图

本页说明仓库内**主文档（单一入口）**与**历史 / 专题归档**的分工，避免在子目录根散落多份「修复说明」却找不到架构总览。

## Canonical（优先阅读）

| 文档 | 说明 |
|------|------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | 系统架构与设计决策 |
| [FEATURE_MAP.md](FEATURE_MAP.md) | 功能边界与目录职责 |
| [QUICK_START.md](QUICK_START.md) | 快速启动 |
| [MIGRATION_REGISTRY.md](MIGRATION_REGISTRY.md) | 迁移与入口统一登记 |
| [TECH_STACK.md](TECH_STACK.md) | 技术栈摘要 |
| [DEPLOYMENT.md](DEPLOYMENT.md) | 部署相关 |
| [reports/capacity-planning.md](reports/capacity-planning.md) | 容量规划、k6 `scripts/loadtest` 基线与目标 SLO；MODstore 全链路数字见姊妹仓 `MODstore_deploy/docs/perf-benchmark-public.md` |
| [reports/FHD_DEPTH_ASSESSMENT_REVISED_2026-05-03.md](reports/FHD_DEPTH_ASSESSMENT_REVISED_2026-05-03.md) | FHD/XCAGI 深度评估（修订版，与源码核实对齐） |
| [reports/COVERAGE_RAMP.md](reports/COVERAGE_RAMP.md) | 覆盖率 `fail_under` 分阶段目标与补测清单 |
| [guides/RATE_LIMITING.md](guides/RATE_LIMITING.md) | 全站 / 路由级 / Redis 限流并存策略 |
| [guides/DEPENDENCY_LOCKS.md](guides/DEPENDENCY_LOCKS.md) | uv / Poetry 依赖锁定与 CI 安装说明 |
| [DELIVERABLE_PRODUCT.md](DELIVERABLE_PRODUCT.md) | **可交付产品**：交付物清单、验收 API、发版自检命令 |
| [DELIVERABLE_PRODUCT.md](DELIVERABLE_PRODUCT.md) | **可交付产品**：交付物清单、验收 API、发版自检 |
| [guides/PRODUCT_USER_FLOW.md](guides/PRODUCT_USER_FLOW.md) | **产品用户流程**：安装→首启→宿主就绪→行业 MOD→日常使用（实施必读） |
| [customer/CUSTOMER_SUPPORT.md](customer/CUSTOMER_SUPPORT.md) | **客户交付**：版本与安装包对齐、升级/回滚、日志与诊断包、SLA 话术模板 |

## 子项目入口

| 区域 | 说明 |
|------|------|
| [../WXCC/README.md](../WXCC/README.md) | 微信小程序（WXCC）开发与运行说明 |
| [../XCAGI/README.md](../XCAGI/README.md) | 后端 XCAGI 子树说明（若独立检出） |
| [../frontend/README.md](../frontend/README.md) | Web 前端 SPA |

## Historical / 专题归档

| 位置 | 内容 |
|------|------|
| [wxcc/](wxcc/) | 小程序历史修复笔记：`FIXES.md`、`IMAGE_FIX.md`、`IMAGE_FIX_V2.md`、`PATH_FIX.md` |
| [reports/](reports/) | 迁移、测试、Neuro、Flask→FastAPI 等阶段性报告与评估（偏考古，非日常必读）；**容量与性能基线**见 `reports/capacity-planning.md` |

## 工具与调试脚本说明

| 位置 | 内容 |
|------|------|
| [../tools/debug/README.md](../tools/debug/README.md) | 诊断脚本（如 `diagnose_pro_mode.py`、`diagnose_routes.py`） |
| [../scripts/README.md](../scripts/README.md) | 根级脚本约定与 launchers |
| [../tools/frontend-oneoffs/README.md](../tools/frontend-oneoffs/README.md) | 前端一次性修补历史说明 |
