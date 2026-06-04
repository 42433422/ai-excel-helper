# v10 技术债收口状态（2026-06-03）

## 已完成

| 项 | 说明 |
|----|------|
| P0 SQLite 并发 | `get_db` / `session.get_db` → `MultiDbConsistencyManager.transaction` + 写锁 |
| P1 限流 / NDJSON | 桌面与 Helm 默认开启；整机中间件测试 |
| P2 SLA / Helm | `sla-probe.yml`、`helm lint` + `envFrom` |
| **破坏性清理 v10.0.3** | 删除 22 个 `legacy_*` / `xcagi_compat_*` shim；保留 `xcagi_compat.py`（前端 compat 聚合） |

## Shim 删除后导入规范

```python
# 路由 / handler
from app.fastapi_routes.domains.auth import routes
from app.fastapi_routes.domains.product import compat_routes

# 会话 / 权限工具
from app.fastapi_routes.domains.misc import helpers

# DB 辅助
from app.fastapi_routes.domains.db import base, queries, writes

# 前端 compat 聚合（仅此一处）
from app.fastapi_routes.xcagi_compat import router
```

CI 门禁：`python scripts/dev/verify_no_legacy_shims.py`（见 `domain-registry-integrity` job）。

## 可选后续（v10.0.5 已收口）

- ~~将 `LEGACY_ROUTE_REGISTRY` 精简为纯文档表~~ **（已完成：每业务域一行，CI 仅校验域目录 + `xcagi_compat.py` 白名单）**
- ~~物理删除 `legacy_host_routers.py`~~ **（v10.0.4：`register_legacy_gap_routers` 内联）**
