# XCAGI Android 原生客户端

## 概述

`mobile-android/` 为 **成都修茈科技有限公司** XCAGI 的 Android 原生客户端（Kotlin + Jetpack Compose），与 [FHD](../) 电脑端（Electron + FastAPI）及公网 [MODstore](https://xiu-ci.com) 互联。

- **品牌图标**：与 Windows 相同，源文件 [`desktop/branding/app-icon-source.png`](../../desktop/branding/app-icon-source.png)，由 `scripts/package/generate-android-icons.py` 生成各密度 `mipmap`。
- **启动流程（混合）**：已保存电脑主机或完成引导 → 直达登录/工作台；仅首次显示「进入云端」引导（电脑连接可折叠）。
- **产品壳**：登录后主 Tab 为 **首页 · 对话 · 工作台 · 我的**（企业版含审批/业务）；工作台 WebView 加载 `https://xiu-ci.com/workbench/home?client=android`；「我的」集中账号、连接电脑与高级功能。
- **双 SKU**：`personal` / `enterprise` 两个独立安装包，可同时安装。

| Flavor | applicationId | 说明 |
|--------|---------------|------|
| **personal** | `com.xiuci.xcagi.mobile.personal` | 个人版 |
| **enterprise** | `com.xiuci.xcagi.mobile.enterprise` | 企业版（含审批/ERP 底栏） |

## 图标生成（打包前）

```bat
cd FHD
python scripts/package/generate-android-icons.py
```

## 构建 APK

```bat
cd mobile-android
gradlew.bat assemblePersonalDebug assembleEnterpriseDebug
```

整理到分发目录（含 Windows exe + Android apk）：

```powershell
cd FHD
python scripts/package/generate-android-icons.py
powershell -File scripts/package/stage-sku-download-folders.ps1 -Version 8.0.0
```

产出：`release/packages-v8.0.0/personal/` 与 `enterprise/`（或已重命名为 `个人版` / `企业版`）。

## 架构

| 模式 | 基址 | 用途 |
|------|------|------|
| 局域网 FHD | `http://<PC_IP>:5000/` | SSE 对话、审批、ERP、LAN、Mod |
| 云端 MODstore | `https://xiu-ci.com/` | 手机验证码、市场 |

移动端 API：`/api/mobile/v1/*`

## 底栏信息架构

| SKU | 底栏 Tab |
|-----|----------|
| 个人版 | 首页 · 对话 · 工作台 · 我的 |
| 企业版 | 首页 · 对话 · 工作台 · 审批 · 业务 · 我的 |

- **工作台**：WebView 加载公网工作台；登录后将 `modstore_token` / `modstore_refresh_token` 注入 `localStorage`（与官网 [`tokenStore`](../../成都修茈科技有限公司/MODstore_deploy/market/src/infrastructure/storage/tokenStore.ts) 一致）。
- **电脑端账号登录**：FHD 登录成功后调用 `GET /api/market/session-handoff` 同步市场 token。
- **手机号登录**：直接写入 `SessionStore` 市场 token。

## 前台体验说明

- 默认 **不** 后台扫描局域网；可在「我的」打开「后台自动发现电脑」。
- 「连接 / 更换电脑」仅在「我的」内进入，不出现在首屏底栏。
- 深色 Material3 主题，与工作台视觉一致。

## 超级 App 路线图（阶段三）

产品定位：**豆包式 AI 中枢** + **连电脑做工作数据同步**（非远控）+ **通用宿主 + Mod 集成**。

| 底栏（个人版） | 首页 · 对话 · 工作台 · 我的 |
| 底栏（企业版） | 首页 · 对话 · 工作台 · 审批 · 业务 · 我的 |

- **首页**：我的电脑（在线/同步）、Mod 网格、快捷进入对话/工作台
- **同步**：`GET/POST /api/mobile/v1/sync/*`，复用 PC 端 `xcmax_sync`；Room 缓存审批/发货；WorkManager 可选后台同步
- **对话**：建议芯片、同步提示、根据回复推荐打开工作台/Mod

### 移动端同步 API

| 端点 | 说明 |
|------|------|
| `GET /api/mobile/v1/home` | Mod 列表 + platform_shell + sync 状态 |
| `GET /api/mobile/v1/platform-shell` | 宿主能力清单 |
| `GET /api/mobile/v1/sync/status` | 同步游标与队列计数 |
| `POST /api/mobile/v1/sync/pull` | 拉取审批/发货与变更 |
| `POST /api/mobile/v1/sync/push` | 手机提交变更入 outbox |

### Release 正式签名

**推荐（一次性生成密钥 + 本地配置，不入 Git）：**

```powershell
cd FHD
powershell -File scripts/package/new-android-release-keystore.ps1
powershell -File scripts/package/build-android-release-signed.ps1 -Stage -Version 8.0.0 -AndroidVersion 1.3.0
```

- 密钥库默认路径：`mobile-android/signing/xcagi-release.jks`
- 配置：`mobile-android/keystore.properties`（由脚本生成，已 gitignore）
- 模板：`mobile-android/keystore.properties.example`

**或用手动环境变量（CI / 本机均可）：**

```bat
set XCAGI_ANDROID_KEYSTORE=E:\secure\xcagi-release.jks
set XCAGI_ANDROID_KEYSTORE_PASSWORD=***
set XCAGI_ANDROID_KEY_ALIAS=xcagi_release
set XCAGI_ANDROID_KEY_PASSWORD=***
set XCAGI_REQUIRE_RELEASE_SIGNING=1
cd mobile-android
gradlew.bat assemblePersonalRelease assembleEnterpriseRelease
```

未配置 keystore 时 Release 使用 **debug 签名**（仅内测）；`stage-sku-download-folders.ps1 -BuildAndroidRelease` 若存在 `keystore.properties` 会自动走正式签名脚本。

**务必备份** `.jks` 与密码；丢失后无法为同一 `applicationId` 在应用商店发布更新。

## 阶段二（体验补齐）

| 模块 | 内容 |
|------|------|
| 对话 | 左右气泡布局；顶栏 **云端 / 局域网** 状态 Chip；空状态提示 |
| 企业 Tab | 审批 / 业务统一 TopAppBar；骨架屏、空状态、错误重试 |
| 工作台 WebView | URL 带 `?client=android`；注入 `__XCAGI_CLIENT__` 后 market 端 `useBreakpoint` 强制移动布局 |

### v1.3.0 交付能力（真正 App 验收）

| 能力 | 说明 |
|------|------|
| 云端纯手机用户 | 手机号登录后首页展示 MODstore 目录；工作台注入 token；对话 Tab 引导至工作台 AI |
| 电脑 + 同步 | 首页 Mod 来自本机；WorkManager 后台同步；审批/发货离线读 Room 缓存 |
| WebView | 文件选择器（上传）；Mod 云端页自动注入市场 token |
| 分发 | `stage-sku-download-folders.ps1 -BuildAndroidRelease -AndroidVersion 1.3.0` |

应用商店物料（截图、隐私政策等）仍按商店流程单独准备。

## 认证互通

与 FHD、官网 MODstore 的 token 键名、登录路径、`session-handoff` / `account-sync` 约定见 [AUTH_MARKET_CONTRACT.md](./AUTH_MARKET_CONTRACT.md)。

## 相关文档

- [AUTH_MARKET_CONTRACT.md](./AUTH_MARKET_CONTRACT.md)
- [RELEASE_TWO_SKUS.md](./RELEASE_TWO_SKUS.md)
- [PLATFORM_SHELL.md](./PLATFORM_SHELL.md)
