# XCAGI 容量规划与性能基线

## 文档信息

- **版本**: v1.1
- **更新日期**: 2026-05-03
- **维护者**: XCAGI 架构团队

**MODstore 全链路（登录、市场、支付、WS 等）**的公开压测数字以姊妹部署仓库为准：[`../../../成都修茈科技有限公司/MODstore_deploy/docs/perf-benchmark-public.md`](../../../成都修茈科技有限公司/MODstore_deploy/docs/perf-benchmark-public.md)（若仓库未与 FHD 同盘检出，请改为组织内实际路径）。

## 1. 性能基线指标

### 1.1 单实例基准（FHD `scripts/loadtest/smoke.js`）

| 指标 | 当前值 | 目标值 | 测量方式 |
|------|--------|--------|----------|
| QPS（查询） | N/A（见 §6：最近一次无可用 API 进程） | ≥ 200 | k6 load test |
| QPS（写入） | N/A | ≥ 50 | k6 load test |
| P50 延迟 | N/A | < 50ms | k6 + Prometheus |
| P95 延迟 | N/A | < 200ms | k6 + Prometheus |
| P99 延迟 | N/A | < 500ms | k6 + Prometheus |
| 错误率 | 见 §6（无上游时为连接失败） | < 1% | k6 + Prometheus |

### 1.2 资源消耗（待填充）

| 资源 | 单实例消耗 | 限制 | 测量方式 |
|------|-----------|------|----------|
| CPU（空闲） | - | - | docker stats |
| CPU（满载） | - | - | docker stats |
| 内存（空闲） | - | - | docker stats |
| 内存（满载） | - | - | docker stats |
| 数据库连接池 | - | 20 | SQLAlchemy pool status |

### 1.3 AI 服务延迟（待填充）

| 服务 | P50 | P95 | P99 | 超时设置 |
|------|-----|-----|-----|----------|
| DeepSeek Chat | - | - | - | 30s |
| BERT 意图识别 | - | - | - | 5s |
| RASA NLU | - | - | - | 10s |
| OCR 识别 | - | - | - | 30s |
| TTS 合成 | - | - | - | 15s |

## 2. 压测方案

### 2.1 压测工具

使用 k6 作为主要压测工具，脚本位于 `scripts/loadtest/`。路径已与 FastAPI 对齐：`/api/health`、`/api/mod-store/catalog`、`/health/liveness`、`/api/auth/login`（`stress.js`）。

| 脚本 | 用途 | VU | 持续时间 |
|------|------|-----|----------|
| smoke.js | 冒烟验证 | 5 | 30s |
| load.js | 负载测试 | 10→50 | 3min |
| stress.js | 压力测试 | 50→200 | 5min |

### 2.2 运行方式

```bash
# 冒烟测试
k6 run -e BASE_URL=http://127.0.0.1:8000 scripts/loadtest/smoke.js

# 负载测试
k6 run -e BASE_URL=http://127.0.0.1:8000 scripts/loadtest/load.js

# 压力测试
k6 run -e BASE_URL=http://your-server:8000 scripts/loadtest/stress.js
```

## 3. 扩缩容策略

### 3.1 水平扩缩容（HPA）

| 指标 | 阈值 | 最小副本 | 最大副本 |
|------|------|----------|----------|
| CPU 使用率 | 80% | 2 | 10 |
| 内存使用率 | 80% | 2 | 10 |

### 3.2 垂直扩容

| 组件 | 当前规格 | 推荐规格 |
|------|----------|----------|
| API Server | 1C2G | 2C4G |
| PostgreSQL | 2C4G | 4C8G |
| Redis | 1C1G | 2C2G |

## 4. 容量规划

### 4.1 用户增长预估

| 时间 | DAU | 并发用户 | 所需实例 |
|------|-----|----------|----------|
| 当前 | - | - | 1 |
| 3 个月 | - | - | 2 |
| 6 个月 | - | - | 3-5 |
| 12 个月 | - | - | 5-10 |

### 4.2 数据增长预估

| 数据类型 | 当前量 | 月增长 | 12 个月预估 |
|----------|--------|--------|-------------|
| 发货单 | - | - | - |
| 产品 | - | - | - |
| 客户 | - | - | - |
| AI 对话记录 | - | - | - |

## 5. 性能优化方向

1. **数据库查询优化**：添加缺失索引、优化慢查询
2. **缓存策略**：Redis 缓存热点数据、CDN 静态资源
3. **异步处理**：Celery 异步化耗时操作（OCR、TTS、AI 推理）
4. **连接池调优**：SQLAlchemy pool size、Redis 连接池
5. **前端优化**：代码分割、懒加载、SSR

## 6. 基线测试记录

### 测试环境

| 项目 | 值 |
|------|-----|
| OS | Windows（Agent 执行机，文档生成用） |
| CPU / Memory | 未记录 |
| Python | 3.11 |
| Database | PostgreSQL 16 |
| Redis | 7-alpine |
| API 进程 | 未启动（`127.0.0.1:8000` 拒绝连接） |

### 测试结果

| 日期 | 脚本 | VU | http_reqs | 迭代次数 | http_req_failed | 备注 |
|------|------|-----|-------------|----------|-----------------|------|
| 2026-05-03 | smoke.js | 5 | 150 | 75 | 100% | 无上游，仅验证 k6 与脚本；FHD commit `aa9a961` |
| 2026-05-03 | MODstore `full_link_smoke.js` | 2 | 480 | 60 | 100% | 数据见姊妹仓库 [perf-benchmark-public.md](../../../成都修茈科技有限公司/MODstore_deploy/docs/perf-benchmark-public.md) |

服务可用后请重跑本表并填写 **P50/P95/P99** 与 **业务错误率**（可附 `--summary-export` JSON 路径）。
