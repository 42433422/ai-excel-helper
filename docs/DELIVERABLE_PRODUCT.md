# XCAGI 可交付产品说明（v8.0）

> **产品模型**：每家客户独立部署一份宿主；装平台 MOD 后变为对应垂直系统。供应商不代运营客户业务库。

---

## 交付物清单

| 交付物 | 路径 / 命令 | 验收 |
|--------|-------------|------|
| Windows 安装包（双 SKU，推荐） | `scripts/package/build-all-skus.ps1 -Version 8.0.0` | `release/xcagi-v8.0.0/{personal,enterprise}/` 各一 exe |
| Windows 安装包（单 SKU） | `build-installer.ps1 -Version 8.0.0 -ProductSku personal\|enterprise` | 仅写入对应子目录，见下表 |
| 通用壳前端 | 默认 `npm run build`（generic） | 侧栏仅壳菜单 + Mod |
| 内置 Mod 种子 | 安装包 `mods/`（9 个 bridge） | 首启自动复制到 userData/mods |
| 客户快速开始 | [QUICK_START.md](QUICK_START.md) | 5 分钟内本地可访问 |
| 客户运维 | [customer/CUSTOMER_SUPPORT.md](customer/CUSTOMER_SUPPORT.md) | 版本/日志/回滚口径一致 |
| 技术验收 API | `GET /api/platform-shell/deliverable-status` | `deliverable: true` |
| 一键装包 API | `POST /api/mod-store/bootstrap-edition-pack?edition=generic` | `success: true` |
| 自动化验收 | `scripts/dev/deliverable_smoke.ps1` | 全部 [OK] |

---

## 双 SKU 发行矩阵

| SKU | 命令 | 安装包文件名 | 内置 Mod | ERP |
|-----|------|--------------|----------|-----|
| **personal** | `-ProductSku personal` | `XCAGI-Personal-Setup-{ver}-x64.exe` | `MINIMAL_HOST_MOD_IDS`（3 个 bridge） | 否 |
| **enterprise** | `-ProductSku enterprise` | `XCAGI-Enterprise-Setup-{ver}-x64.exe` | `GENERIC_HOST_MOD_IDS` + 辅助 Mod | **是**（`xcagi-erp-domain-bridge`） |

- 打包过滤：`scripts/package/stage-bundled-mods.ps1` → PyInstaller 仅打入白名单目录。
- 运行时：`XCAGI_PRODUCT_SKU` / `product-sku.json`；个人版**禁止**加载 ERP Mod（`mod_manager`）。
- 更新站路径：`https://update.xcagi.com/releases/stable/{personal|enterprise}/`
- 打包后验收：`scripts/package/verify-bundled-mods.ps1 -ProductSku <sku>`

官网下载页（MODstore）环境变量：`VITE_XCAGI_DOWNLOAD_BASE_URL`、`VITE_XCAGI_DOWNLOAD_VERSION`。

---

## 客户标准路径

1. 安装 XCAGI（generic 宿主）
2. 首次打开 → **首次设置向导**（`/onboarding`）：认识宿主 → 宿主包就绪 → 行业定型（可跳过）
3. 宿主包未齐时：**一键装齐通用包**（或安装包已种子 Mod）
4. 从**扩展市场**安装**行业 MOD** → 系统变为该客户垂直方案
5. 日常使用：智能对话 + Mod 菜单；数据在客户本机 `userData`

**完整流程说明（必读）**：[guides/PRODUCT_USER_FLOW.md](guides/PRODUCT_USER_FLOW.md)

---

## 供应商发版前自检（必做）

```powershell
cd <repo-root>
powershell -ExecutionPolicy Bypass -File scripts/dev/adcdfg_acceptance.ps1
powershell -ExecutionPolicy Bypass -File scripts/dev/deliverable_smoke.ps1
```

确认 `VERSION.md` 与 `CHANGELOG.md` 顶部版本均为 **8.0.0**，且 `rg` 扫描锚点一致（见 VERSION.md）。

---

## 可交付判定（API）

```http
GET /api/platform-shell/deliverable-status
```

| 字段 | 含义 |
|------|------|
| `deliverable` | `true` = 可对外交付该 edition |
| `edition` | `minimal` / `generic` / `full` |
| `generic_pack_installed` | 9 个通用 bridge Mod 是否齐全 |
| `blockers` | 未满足项与 `missing_mod_ids` |
| `next_actions` | 建议操作（装包、打开市场等） |

---

## 环境变量（交付相关）

| 变量 | 默认 | 说明 |
|------|------|------|
| `XCAGI_GENERIC_EDITION` | 桌面 `1` | generic 发行 |
| `XCAGI_PLATFORM_SHELL` | 桌面 `1` | 平台壳模式 |
| `XCAGI_DEFAULT_EDITION` | 桌面 `generic` | Electron 传入 |
| `XCAGI_PRODUCT_SKU` | 无 | `personal` / `enterprise`（双 SKU 安装包） |
| `XCAGI_AUTO_BOOTSTRAP_EDITION` | `0` | `1` 时启动会从公网 Catalog 补装 |
| `XCAGI_REGISTER_LEGACY_ROUTES` | 非 full 关闭 | full 构建可设 `1` |

---

## 已知非阻断项（后续版本）

- `legacy_gaps_batch*` 按域拆分（full 版专用）
- 覆盖率 80%+
- MOD 签名强制与公网 SLA

*配套：[guides/ADCDFG_COMPLETION_PLAN.md](guides/ADCDFG_COMPLETION_PLAN.md)*
