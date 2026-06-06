# 认证与市场会话契约（FHD / MODstore / Android）

跨端「登录一次、工作台互通」的单一约定。实现变更时先改本文，再改各客户端。

## 账号体系

| 概念 | SSOT | 说明 |
|------|------|------|
| 修茈市场用户 | `modstore_server` `/api/auth/*` | 用户名密码、手机验证码、JWT |
| FHD 本地会话 | `sessions` 表 + Cookie `session_id` | 电脑端宿主登录 |
| 移动端 FHD JWT | `POST /api/mobile/v1/auth/login` | 与 FHD 同源 `auth_app_service`，`aud=xcagi-mobile` |
| 市场 token 绑定到 FHD 会话 | `market_account.save_session_market_token` | DB + 进程内缓存 |

**同一用户**：官网 MODstore、FHD（绑定后）、Android 工作台 WebView 应使用**同一套**市场 JWT（`modstore_token`）。

## localStorage / WebView 键名（跨端契约）

| 键 | 用途 |
|----|------|
| `modstore_token` | 市场 access JWT |
| `modstore_refresh_token` | 市场 refresh JWT |

FHD Electron 本地可额外缓存 `xcagi_market_access_token` / `xcagi_market_refresh_token`；注入 Android WebView 时必须写成 `modstore_*`。

## HTTP 端点

### 读：FHD 会话 → 市场 token

`GET /api/market/session-handoff`（需 FHD 已登录）

响应 `data.market_access_token`、`data.market_refresh_token`（可选）。

### 写：市场 token → FHD 会话

`POST /api/market/account-sync`

Body 任选：`token`、`authorization`，或 Header `Authorization: Bearer …`。

用于：Android 手机登录后电脑在线时，把市场 JWT 绑到当前 FHD 会话。

**禁止**用 `POST /api/market/login` 仅传 `{token}`（该接口需要 username/password）。

### 主登录（FHD）

`POST /api/auth/login` — 成功后服务端应 `save_session_market_token`；客户端优先用响应内 `market_access_token`，否则再调 `session-handoff`。

### 纯云端（无 FHD）

`POST https://xiu-ci.com/api/auth/login`（或配置的 `XCAGI_MARKET_BASE_URL`）。

## 客户端登录决策表

| 客户端 | 条件 | 动作 |
|--------|------|------|
| FHD Web | 始终 | `POST /api/auth/login` → `applyMarketTokensAfterFhdLogin`（响应或 handoff） |
| Android | 电脑在线 + 已配置 host | `POST /api/mobile/v1/auth/login` → `GET session-handoff` |
| Android | 纯云端 | `POST /api/auth/login`（Modstore）→ WebView 注入 token；若电脑在线再 `account-sync` |
| Android 手机验证码 | 云端 | `POST /api/auth/login-with-phone-code` → 同上 |
| Market 浏览器 | — | `api/auth.login` → `tokenStore` |

## 能力边界（非重复实现）

| 能力 | 实现位置 | 不应复制 |
|------|----------|----------|
| 工作台 UI / AI | Market SPA | Android/FHD 仅 WebView 或外链 |
| 审批/ERP/同步 | FHD `:5000` | 手机 Room 缓存 + mobile API |
| 原生 SSE 对话 | FHD `/api/ai/chat/stream` | 需 FHD token；纯云端用工作台 AI |

## `/api/auth/refresh` 归属

- **小程序 JWT**：`POST /api/auth/refresh`（`mp_auth.refresh_access_token`），body `refresh_token`。
- **FHD Web Cookie 会话**：不走此接口；重新 `session-handoff` 或重新登录。

## 部署

生产环境仅保留一套 modstore upstream，见 [DEPLOY_MODSTORE_SINGLE_UPSTREAM.md](./DEPLOY_MODSTORE_SINGLE_UPSTREAM.md)。

## 相关文件

- [market_account.py](../../app/fastapi_routes/market_account.py)
- [marketAccount.ts](../../frontend/src/api/marketAccount.ts)
- [tokenStore.ts](../../../成都修茈科技有限公司/MODstore_deploy/market/src/infrastructure/storage/tokenStore.ts)
- [XcagiRepository.kt](../../mobile-android/app/src/main/java/com/xiuci/xcagi/mobile/core/repository/XcagiRepository.kt)
- [MOBILE_ANDROID.md](./MOBILE_ANDROID.md)
