# 企业级能力：权限与审计

## 当前实现（可落地）

### 请求追踪

- 每个请求分配或透传 `X-Request-ID`（客户端可传入；否则服务端生成 UUID）。
- 响应头带回同一 `X-Request-ID`，便于与网关、APM、工单对齐。

### 结构化审计日志（可选）

设置环境变量 `AUDIT_LOG_PATH`（例如 `/var/log/fhd/audit.jsonl`）后，服务端对 **API 路由** 追加 JSON Lines，每行一条记录，字段包括：

| 字段 | 说明 |
|------|------|
| `ts` | ISO8601 UTC 时间戳 |
| `request_id` | 与响应头一致 |
| `method` / `path` | HTTP 方法与路径 |
| `status_code` | 响应状态码 |
| `duration_ms` | 处理耗时（流式接口为「首包返回前」耗时，见下） |
| `streaming` | 是否为 SSE/流式路由（`true`/`false`） |
| `client_host` | 直连客户端 IP（经 `X-Forwarded-For` 时取首个非空段，便于反代后追溯） |
| `user_agent` | `User-Agent` 截断至 512 字符，避免日志膨胀 |

**刻意不记录**：`/api/chat`、`/api/chat/stream` 的请求体与回复正文，避免在审计文件中落盘敏感业务数据。如需合规留痕，应在 **独立密级系统** 中做授权后的按需归档，并与本审计日志用 `request_id` 关联。

### 可选 API 密钥（粗粒度接入控制）

设置 `FHD_API_KEYS`（逗号分隔多个密钥）后：

- 除 `GET /api/health`、`GET /docs`、`GET /redoc`、`GET /openapi.json` 外，其它 `/api/*` 需携带：
  - `X-API-Key: <key>`，或
  - `Authorization: Bearer <key>`

适用于内网反代后、在应用层增加一层 **调用方标识**，**不是**完整 RBAC。多租户与细粒度权限见下文路线图。

## 路线图（复杂权限与合规审计）

| 能力 | 说明 | 状态 |
|------|------|------|
| RBAC / ABAC | 角色、资源、操作、数据范围（租户/部门） | 规划中 |
| 管理审计查询 | 按用户、资源、时间、操作类型过滤与导出 | 规划中 |
| 不可篡改存储 | 审计链（hash 链）或外送 SIEM（Syslog、S3 Object Lock 等） | 规划中 |
| 与 IdP 集成 | OIDC / SAML、SCIM 用户同步 | 规划中 |

上线企业版时建议：**身份来自 IdP**，**权限决策在策略引擎**，**审计双写**（应用日志 + 企业 SIEM），并保留 `request_id` 作为跨系统关联键。

## 运维建议

- 反代层开启访问日志，并与应用 `request_id` 关联（在网关注入 `X-Request-ID`）。
- `AUDIT_LOG_PATH` 目录单独轮转与权限控制；生产环境避免 world-readable。
- 流式接口的「完整会话时长」需结合网关日志或 APM Span；当前应用内 `duration_ms` 仅反映到响应对象返回为止的耗时。
