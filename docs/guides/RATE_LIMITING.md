# API 速率限制策略说明

## 现状（2026-05）

FHD FastAPI 栈已挂载**两层进程内/Redis 限流中间件**（见 [`app/fastapi_app/factory.py`](../../app/fastapi_app/factory.py)）：

| 中间件 | 文件 | 默认策略 |
|--------|------|----------|
| **全局限流** | [`app/middleware/global_rate_limit.py`](../../app/middleware/global_rate_limit.py) | `/api/*` 按 IP + 路径段，**300 次/60s**；`/api/health`、`/metrics` 除外 |
| **认证专用** | [`app/middleware/auth_rate_limit.py`](../../app/middleware/auth_rate_limit.py) | 登录/注册/找回密码/移动端登录，**10 次/60s/IP** |

计数实现：[`app/utils/rate_limiter.py`](../../app/utils/rate_limiter.py) — 若配置 `CACHE_REDIS_URL`（或 `REDIS_URL`）则使用 **Redis 固定窗口**（多副本共享）；否则回退内存。

超限响应：`429`，JSON `code: RATE_LIMITED`，含 `retry_after`。

## 环境变量

| 变量 | 默认 | 说明 |
|------|------|------|
| `XCAGI_GLOBAL_RATE_LIMIT` | `1` | 全局限流总开关 |
| `XCAGI_GLOBAL_RATE_LIMIT_MAX` | `300` | 全局限流配额 |
| `XCAGI_GLOBAL_RATE_LIMIT_WINDOW` | `60` | 全局限流窗口（秒） |
| `XCAGI_AUTH_RATE_LIMIT` | `1` | 认证路径限流开关 |
| `XCAGI_AUTH_RATE_LIMIT_MAX` | `10` | 认证路径配额 |
| `XCAGI_AUTH_RATE_LIMIT_WINDOW` | `60` | 认证路径窗口（秒） |
| `CACHE_REDIS_URL` | 空 | 配置后全集群共享计数 |

K8s 生产默认值见 [`k8s/configmap.yaml`](../../k8s/configmap.yaml)。

## 路由级 / 装饰器限流（保留）

- [`app/utils/security_middleware.py`](../../app/utils/security_middleware.py)：`api_security(..., rate_limit=…)`
- AI 聊天：[`app/services/service_optimizers.py`](../../app/services/service_optimizers.py) 命名限流器（`ai_chat` 30/60s），可在 FastAPI 路由通过 `Depends` 接入。

## 推荐并存策略

| 层级 | 职责 |
|------|------|
| 网关 / Ingress | 粗粒度 IP / 路径 QPS |
| Redis + 上述中间件 | 集群维度登录防暴力、API 滥用 |
| `api_security` 装饰器 | 单路由细粒度兜底 |

## 相关测试

- [`tests/test_middleware_rate_limit.py`](../../tests/test_middleware_rate_limit.py)
