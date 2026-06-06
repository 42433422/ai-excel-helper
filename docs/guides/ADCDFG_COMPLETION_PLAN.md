# ADCDFG 全量完成计划

> **目标**：每家客户独立部署一份 XCAGI 宿主；从平台安装 MOD 后，该实例即变为对应垂直系统。你不代运营客户业务数据。  
> **状态**：2026-05-22 起按本计划收尾；里程碑 A～S 已完成，本计划覆盖 **T～G** 交付收口。

---

## 阶段定义

| 阶段 | 含义 | 交付物 | 验收 |
|------|------|--------|------|
| **A** | **Anchor 锚定** | 本计划、`VERSION.md`、产品定位 README | 文档与版本锚点一致 |
| **B** | **Build 默认空壳发行** | `build:generic` 为默认构建；安装包默认 generic 前端 | 新装桌面首屏仅壳菜单 |
| **C** | **Cleanup 宿主瘦身** | 非 `full` edition 不注册 `legacy_gaps_*` | `edition=generic` 时 OpenAPI 无 legacy-gaps tag |
| **D** | **Distribution 平台闭环** | `POST /api/mod-store/bootstrap-edition-pack`；桌面首启种子 Mod | 一键装齐 generic/minimal 包 |
| **E** | **Enforce 壳模式** | 桌面/后端默认 `XCAGI_GENERIC_EDITION` + `XCAGI_PLATFORM_SHELL` | `/api/platform-shell/capabilities` → `edition: generic` |
| **F** | **Frontend 默认壳** | `npm run build` = generic；路由守卫与壳模式一致 | `VITE_XCAGI_EDITION=generic` |
| **G** | **Gates 质量门禁** | 全局限流中间件、验收脚本、测试、decoupling 100% | `scripts/dev/adcdfg_acceptance.ps1` 通过 |

---

## 不在本轮（明确边界）

- `legacy_gaps_batch1/2` 按域拆成 14+ 模块（需 3～5 迭代，见 `LEGACY_CLEANUP_TRACKING.md` Phase 2D）
- `app/legacy/planner.py` / `tools.py` 枢纽迁移（Phase 4）
- 覆盖率 80%+（单独质量专项）
- MODstore 公网高可用与签名强制（运维专项）

---

## 客户路径（完成后）

```text
1. 安装 XCAGI 宿主（generic 空壳 + 内置 bridge Mod 种子）
2. 打开 → 智能对话 / Mod 市场 / 设置
3. 从平台下载行业 MOD → 安装 → 重载
4. 侧栏与首页变为该行业系统（菜单、员工、API 均由 Mod 提供）
```

---

## 自检命令

```powershell
# 验收（仓库根）
powershell -ExecutionPolicy Bypass -File scripts/dev/adcdfg_acceptance.ps1

# 构建通用壳桌面
powershell -File scripts/package/build-installer.ps1 -Version 8.0.0

# API：装齐 generic 包
curl -X POST http://127.0.0.1:5000/api/mod-store/bootstrap-edition-pack?edition=generic
```

---

## 可交付收口（2026-05-22 续）

见 [DELIVERABLE_PRODUCT.md](../DELIVERABLE_PRODUCT.md)：`deliverable-status` API、首启引导、桌面 Mod 种子、`deliverable_smoke.ps1`。

---

*与 [PLATFORM_SHELL.md](./PLATFORM_SHELL.md)、[DELIVERABLE_PRODUCT.md](../DELIVERABLE_PRODUCT.md)、[DECOUPLING_ROADMAP.md](../../../成都修茈科技有限公司/docs/DECOUPLING_ROADMAP.md) 配套。*
