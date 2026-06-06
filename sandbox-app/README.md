# FHD Mod 沙盒（sandbox-app）

在线轻量环境：复用仓库内的 `app.*` Python 包，仅挂载 Mod 测试所需的 API，其余常见业务接口由桩返回空数据；前端使用 `templates/vue-dist`（或可选 `web_static` 联接）。

## 前置条件

1. Python 3.11+（与主栈一致为佳）
2. 依赖：`pip install -r sandbox-app/requirements.txt`（从 **FHD 仓库根** 执行，或先 `cd sandbox-app` 再安装：路径内含 `-r ../XCAGI/requirements.txt`）
3. 前端产物：在 `frontend/` 执行 `npm run build`，生成 `templates/vue-dist/`
4. （可选）将 dist 链到沙盒目录：`cd sandbox-app && node scripts/sync-frontend-dist.mjs`

## 启动

```powershell
cd sandbox-app
copy .env.example .env   # 按需修改
python sandbox_run.py
```

默认：<http://127.0.0.1:5099/>

- 默认账号：`sandbox` / `sandbox`（可用环境变量 `SANDBOX_ADMIN_USERNAME` / `SANDBOX_ADMIN_PASSWORD` 修改）
- SQLite 数据：`sandbox-app/data/runtime/data/xcagi.db`
- Mod 目录：默认指向仓库根 `mods/`（`SANDBOX_MODS_ROOT` 可覆盖）

**说明：** 首次启动若执行 `bootstrap_sqlite_schema`，会 `import app.db.models` 创建完整表结构，可能较慢（取决于机器与依赖），属正常现象。

## 环境变量摘要

见 [.env.example](.env.example)。常用项：

| 变量 | 含义 |
|------|------|
| `SANDBOX_PORT` | 监听端口，默认 `5099` |
| `SANDBOX_URL_PREFIX` | 反代子路径时写入 HTML（如 `/sandbox`），并改写 `/assets/` 等绝对路径 |
| `SANDBOX_MODS_ROOT` | Mod 根目录 |
| `SANDBOX_RESET_ON_BOOT` | `1` 时每次启动删除 `xcagi.db` |
| `LAN_GUARD_ENABLED` | 建议 `0`（沙盒默认已设） |

## 同源部署（HTTPS）

将 `location /sandbox/` 反代到本进程，示例见 [deploy/nginx-sandbox.conf.example](deploy/nginx-sandbox.conf.example)。  
若未设置 `SANDBOX_URL_PREFIX`，需在 nginx 中额外映射 `/sandbox/assets/` 等静态路径（示例文件已包含）。

## Mod 测完后同步到完整 FHD

1. 在沙盒内用 `/api/mod-store/*` 安装或验证 Mod（或直接使用 `mods/` 目录调试）。
2. 打包为 `.xcmod` / 通过修茈市场上架后，在生产环境用完整 FHD 的 Mod 商店或安装接口部署。
3. 沙盒不提供生产数据；若 Mod 依赖未挂载的业务 API，会在兜底 JSON 中看到 `missing_route`，便于补齐依赖说明。

## Docker

在 **仓库根** 构建（需已存在 `templates/vue-dist` 与 `mods`）：

```bash
docker build -f sandbox-app/Dockerfile -t xcagi-mod-sandbox .
docker run --rm -p 5099:5099 xcagi-mod-sandbox
```

## 架构说明

- 路由白名单：`mods_routes`、`mod_store_routes`（前缀 `/api/mod-store`）、`legacy_auth`、`system_routes`、`state`、`legacy_conversation`
- 其后挂载 Mod 动态路由，再挂载 `/api/*` 兜底桩，最后挂载静态资源与 SPA fallback
- 页面顶部横幅与 `window.__SANDBOX__` 由 `banner_inject` 注入 `index.html`
