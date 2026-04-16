# claw-plugin-report — OpenClaw 插件伽利略上报

纯 HTTP POST 方式的伽利略自定义事件上报，为 OpenClaw 插件提供统一的数据上报能力。

**不依赖任何 Aegis SDK**，直接通过 HTTP POST 请求上报到伽利略服务器。

## 上报协议

关键要点：
- **上报端点**: `https://galileotelemetry.tencent.com/collect`
- **Content-Type**: `text/plain;charset=UTF-8`
- **协议版本**: `scheme: "v2"`
- **环境**: `env` 必须为 `"production"` 才会上报到正式环境

## 快速开始

### 1. 创建配置文件

在插件根目录创建 `claw-plugin-report.config.json`：

```json
{
  "enabled": true,
  "reportToken": "SDK-ce69a98f7b7420f02ae8",
  "hostUrl": "https://galileotelemetry.tencent.com/collect",
  "env": "production"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `enabled` | boolean | 否 | 是否启用上报，默认 `true` |
| `reportToken` | string | 是 | 伽利略项目上报 Token（注册前端观测 target 后获得） |
| `hostUrl` | string | 否 | 上报地址，默认 `https://galileotelemetry.tencent.com/collect` |
| `env` | string | 否 | 环境标识，`production`（正式）或 `test`（测试），默认 `production` |

### 2. 在插件入口初始化

```typescript
import type { PluginApi } from 'openclaw';
import { GalileoReport, REPORT_CONST } from './claw-plugin-report/index.js';

export function register(api: PluginApi) {
  const reporter = GalileoReport.getInstance();

  // 初始化上报（自动从 ~/.qclaw/qclaw.json 读取共享参数）
  reporter.initReport({
    configDir: __dirname,   // 插件根目录（用于加载 claw-plugin-report.config.json）
    logger: api.logger,     // 使用插件日志接口
  });

  // 设置 OpenClaw 版本号
  reporter.setOpenclawVersion(api.runtime?.version ?? '');

  // 设置公共参数
  reporter.setCommonParams({
    plugin_id: 'openclaw-mem0',
    mem0_mode: 'cloud',
  });

  // 直接上报事件（公共参数已自动从主进程同步）
  reporter.reportFunc(REPORT_CONST.CLICK_NEW, {
    page_id: reporter.getPluginName() || 'openclaw-mem0',
    action: 'plugin_loaded',
  });
}
```

## 共享参数机制

插件运行在 OpenClaw 进程中，无法通过 IPC 直接与 Electron 主进程通信。为了共享 `sessionId`、`guid` 等上报必需的参数，SDK 采用文件共享机制：

### 工作原理

```
Electron 主进程                              OpenClaw 插件
┌─────────────────┐                        ┌─────────────────┐
│ 渲染进程同步     │   写入                │ initReport()    │
│ sessionId/guid  │ ──────► ~/.qclaw/     │      │          │
│ 等参数          │        qclaw.json     │      ▼          │
│                 │                        │ 自动读取        │
│                 │                        │ sharedParams    │
└─────────────────┘                        └─────────────────┘
```

### 共享参数内容

主进程在 `~/.qclaw/qclaw.json` 的 `sharedParams` 字段中写入：

| 字段 | 说明 | 写入时机 |
|------|------|----------|
| `sessionId` | 伽利略 sessionId | 渲染进程同步时 |
| `guid` | 设备唯一标识 | 渲染进程同步公共参数时 |
| `appVersion` | 应用版本 | 渲染进程同步公共参数时 |
| `appChannel` | 应用渠道 | 渲染进程同步公共参数时 |
| `platform` | 平台标识 | 渲染进程同步公共参数时 |

### 自动同步

`initReport()` 会自动读取共享参数，无需手动调用。如需主动刷新：

```typescript
import { GalileoReport } from './claw-plugin-report/index.js';

const reporter = GalileoReport.getInstance();
// 主动从 ~/.qclaw/qclaw.json 刷新共享参数
reporter.syncFromSharedParams();
```

### 手动读取

```typescript
import { GalileoReport } from './claw-plugin-report/index.js';

const reporter = GalileoReport.getInstance();
const shared = reporter.readSharedParams();
console.log(shared.sessionId, shared.guid, shared.platform);
```

## API 参考

### `GalileoReport.getInstance(): GalileoReport`

获取全局唯一的上报实例（单例模式）。

```typescript
import { GalileoReport } from './claw-plugin-report/index.js';
const reporter = GalileoReport.getInstance();
```

### `reporter.initReport(options: TelemetryInitOptions): void`

初始化上报模块（同步方法）。在插件 `register` 阶段调用一次。

**初始化流程**：
1. 加载插件配置文件 `claw-plugin-report.config.json`
2. 自动从 `~/.qclaw/qclaw.json` 读取共享参数
3. 生成 deviceId 和 sessionId（如果没有从共享参数获取）

**待上报队列**：
- 上报请求会被缓存到待上报队列（最多 1000 条）
- 每 3 秒批量刷新队列，每批最多 50 条
- 上报失败的事件会放回队列头部等待重试

**共享参数定时同步**：
- 初始化后自动启动定时同步，每 3 分钟从 `~/.qclaw/qclaw.json` 读取一次共享参数
- 主要用于同步 sessionId 的变化（sessionId 会定期更新）
- 如果 sessionId 有变化会自动更新缓存，确保上报数据的 sessionId 正确
- 定时同步不阻塞插件流程

```typescript
const reporter = GalileoReport.getInstance();
reporter.initReport({
  configDir: __dirname,       // 必填：插件根目录
  logger: api.logger,         // 可选：日志接口
  reportToken: 'SDK-xxx',     // 可选：覆盖配置文件中的 token
  hostUrl: 'https://...',     // 可选：覆盖配置文件中的上报地址
  env: 'production',          // 可选：覆盖配置文件中的环境
  sessionId: 'session-xxx',   // 可选：显式覆盖 sessionId（优先级高于共享参数）
});
```

### `reporter.reportFunc(name: string, options?: Record<string, any>): void`

上报事件（fire-and-forget）。如果 `initReport` 未调用，静默返回。

```typescript
reporter.reportFunc(REPORT_CONST.CLICK_NEW, {
  page_id: 'openclaw-mem0',
  action: 'task_recovered',
  task_id: '12345',
});
```

### `reporter.reportFuncAsync(name: string, options?: Record<string, any>): Promise<void>`

异步上报事件（可 await）。

```typescript
await reporter.reportFuncAsync(REPORT_CONST.SUBMIT, {
  page_id: 'openclaw-mem0',
  action: 'checkpoint_saved',
});
```

### `reporter.setCommonParams(params: Record<string, any>): void`

手动设置公共参数（覆盖共享参数）。后续每次 `reportFunc` 自动携带。

```typescript
reporter.setCommonParams({
  plugin_id: 'openclaw-mem0',
  mem0_mode: 'cloud',
  mem0_user: 'user123',
});
```

### `reporter.setOpenclawVersion(version: string): void`

设置 OpenClaw 版本号，上报时 `bean.version` 和 `message.openclaw_version` 将使用此值。

```typescript
reporter.setOpenclawVersion(api.runtime?.version ?? '');
```

### `reporter.getPluginName(): string`

获取插件名称（从配置文件 `pluginName` 读取，用于上报 `page_id`）。

```typescript
const pageId = reporter.getPluginName() || 'openclaw-mem0';
```

### `reporter.readSharedParams(): QClawSharedParams`

从 `~/.qclaw/qclaw.json` 读取主进程共享的参数。

```typescript
const shared = reporter.readSharedParams();
// { sessionId, guid, appVersion, appChannel, platform }
```

### `reporter.syncFromSharedParams(forceUpdate?: boolean): boolean`

从共享参数同步到 SDK 内部缓存（`initReport` 已自动调用）。

### `reporter.destroy(): void`

销毁上报模块，释放资源。在插件卸载时调用。会尝试发送剩余的待上报事件。

### `reporter.isInitialized(): boolean`

检查上报模块是否已初始化且已启用。

## 事件常量

`REPORT_CONST` 提供与 Electron 主进程一致的事件代码常量：

| 常量 | 值 | 说明 |
|------|------|------|
| `CLICK_NEW` | `click_new` | 点击事件 |
| `EXPO` | `expo` | 曝光事件 |
| `SUBMIT` | `submit` | 提交事件 |
| `RESOURCE_MONITOR` | `resource_monitor` | 资源监控 |
| `CRASH_EVENT` | `crash_event` | 崩溃事件 |
| `INTERACTION_EVENT` | `interaction_event` | 交互事件 |
| `JANK_EVENT` | `jank_event` | 卡顿事件 |

## 上报参数处理

内部自动执行以下参数处理：

1. **合并公共参数** — `cachedParams` + 当次 `options`
2. **添加前缀** — `addQclawPrefix()` 为所有参数添加 `PC_Qclaw_` 前缀

## 工具函数

同时导出以下工具函数，供高级场景使用：

- `addQclawPrefix(options)` — 为参数添加 `PC_Qclaw_` 前缀
- `getDevicePlatform({ platform, arch })` — 生成平台标识（`Qclaw_Win` / `Qclaw_MAC_ARM` / `Qclaw_MAC_INTEL`）

## 上报协议格式

上报数据格式遵循伽利略 v2 协议：

```json
{
  "topic": "SDK-xxx",           // 必填，项目 token
  "bean": {
    "uid": "user-guid",         // 用户 uid
    "version": "1.0.0",         // 版本号
    "aid": "device-uuid",       // 设备号，用于计算 UV
    "env": "production",        // 环境，production 为正式环境
    "platform": "Qclaw_Win"     // 平台标识
  },
  "ext": "{...}",               // JSON 字符串，扩展字段
  "scheme": "v2",               // 必填，固定值
  "d2": [
    {
      "fields": "{\"type\":\"normal\",\"level\":\"info\",\"plugin\":\"custom\"}",
      "message": ["{\"event_name\":\"xxx\",\"PC_Qclaw_xxx\":\"...\",\"timestamp\":1234567890,...}"],
      "timestamp": 1234567890   // 当前时间戳（毫秒）
    }
  ]
}
```

关键说明：
- **fields**: 必填 JSON 字符串，必须包含 `type` 和 `level`
  - 自定义日志 `type` 为 `"normal"`
  - `level` 通常为 `"info"`
- **message**: 必填 string 数组，**在 message 里按需增加想要上报的字段**
  - 包含事件名称 (`event_name`, `msg`)
  - 包含所有业务字段（带 `PC_Qclaw_` 前缀）
  - 包含事件时间戳 (`timestamp`)

