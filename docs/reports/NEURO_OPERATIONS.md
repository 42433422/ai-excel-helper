# Neuro 全量观测：运行参数与排障

本文档对应「读写全量」迁移下的 **采样、隐私与自检入口**。业务 API 契约不变；Neuro 失败一律吞掉。

## 环境变量（推荐生产默认值）


| 变量                           | 生产建议          | 说明                                                   |
| ---------------------------- | ------------- | ---------------------------------------------------- |
| `XCAGI_NEURO_INTENT`         | `1`           | 总开关：`0`/`false`/`off`/`no` 关闭总线与桥接（含 HTTP trace 短路）。 |
| `XCAGI_NEURO_HTTP_TRACE`     | `0`           | HTTP 层 trace：`1` 开启；与采样配合使用。                         |
| `XCAGI_NEURO_HTTP_SAMPLE`    | `0.01`–`0.05` | 采样率 `0.0`–`1.0`；全量联调可设 `1.0`。                        |
| `XCAGI_NEURO_HTTP_BODY_MAX`  | `0`           | Body 预览最大字节；`0` 表示不记录 body（仅 path/query 等）。          |
| `XCAGI_NEURO_APP_SAMPLE`     | 留空或 `0.1`     | Application 层 trace 采样；留空等价于 `1.0`（全量）。高频读路径建议显式调低。  |
| `XCAGI_NEURO_SERVICE_TRACE`  | `1`           | Services 层包装 trace；`0` 关闭。                           |
| `XCAGI_NEURO_DOMAIN_METRICS` | `0`           | 各域 handler 内轻量计数（无写库）；排障时临时 `1`。                     |


修改 `XCAGI_NEURO_HTTP_TRACE` 后，进程内会缓存该标志；热重载或重启应用后生效（单测可调用 `clear_neuro_trace_config_cache()`）。

## NeuroBus 可靠性层（生产全开）

生产/K8s 建议启用下列变量（与 [`k8s/configmap.yaml`](../../k8s/configmap.yaml)、`deploy-production` 一致）：

| 变量 | 生产建议 |
|------|----------|
| `XCAGI_NEURO_BUS_DEDUP` | `1` |
| `XCAGI_NEURO_BUS_CIRCUIT` | `1` |
| `XCAGI_NEURO_BUS_RATE_LIMIT` | `1` |
| `XCAGI_NEURO_BUS_TRACE` | `1` |
| `XCAGI_NEURO_BUS_TRACE_SAMPLE_RATE` | `0.1`（避免 trace 洪泛） |
| `XCAGI_NEURO_BUS_LIFELINE` | `1` |
| `XCAGI_NEURO_BUS_DLQ_AUTO` | `1` |
| `XCAGI_NEURO_BUS_SLA_LOG` | `1` |

验证：`GET /api/neurobus/health` → `reliability` 中 `dedup`、`circuit_breaker`、`rate_limit`、`tracer`、`lifeline`、`dlq_auto`、`sla_log` 均为 `true`。

Staging 未显式设置时默认仅 `DEDUP` + `CIRCUIT`（`FHD_ENV=staging`）；**生产勿使用 `FHD_ENV=staging`**。

## 自检与健康端点

- `GET /api/neuro/migration-smoke`：栈启用、域注册数量、反射弧探测等。
- `GET /api/neurobus/health`、`GET /api/neurobus/stats`：总线状态与队列统计（含 `sla_log`、`trace_sample_rate`）。
- `GET /api/health`：聚合健康信息中的 `neuro` 摘要（启用时）。

## 隐私与噪声

- HTTP 中间件对 `Authorization`、`Cookie`、`Set-Cookie`、`X-Api-Key` 等头做占位脱敏。
- 默认不采集 body；勿在生产对全流量开启 `XCAGI_NEURO_HTTP_SAMPLE=1.0` 与空 `XCAGI_NEURO_APP_SAMPLE` 叠加，除非已评估队列与下游消费。

## 相关代码入口

- HTTP：`app/middleware/neuro_http_trace.py`，注册于 `app/fastapi_app.py` 的 `_register_middleware`。
- 配置与采样：`app/neuro_bus/neuro_trace_config.py`。
- Application / Service 桥接：`app/neuro_bus/application_neuro_bridge.py`、`*_instrumentation.py`。