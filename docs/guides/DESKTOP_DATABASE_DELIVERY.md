# 桌面交付：本地 SQLite 基线

> 所有桌面 SKU（personal / enterprise）安装包默认使用 **userData 下的 SQLite**，不依赖 Docker 或本机 PostgreSQL。后续可选连接中心库见下文 Phase 2。

## 交付路径

| 环节 | 行为 |
|------|------|
| 安装包启动 | Electron `userData` + 后端 `--desktop` |
| 数据库文件 | `{userData}/data/xcagi.db` |
| 配置文件 | `{userData}/config/database.json`（默认 `mode: local`） |
| Mod 数据 | SQLite 按 Mod 拆副本（非 PostgreSQL 分库） |

Windows 典型 userData：`%APPDATA%\XCAGI\`

## 开发启动（与交付一致）

```bat
E:\XCMAX\FHD\start-desktop-sqlite.bat
```

或：

```bat
cd /d E:\XCMAX\FHD\XCAGI
set XCAGI_PRODUCT_SKU=enterprise
python run_fastapi.py --desktop --data-dir E:\XCMAX\FHD\XCAGI\data\desktop-dev
```

开发数据目录为 `XCAGI/data/desktop-dev/`，避免污染真实 `%APPDATA%\XCAGI`。

验收 API：

```http
GET /api/desktop/status
```

期望：`storageMode` 为 `local_sqlite`，`database` 指向 `...\data\xcagi.db`。

## Web / PostgreSQL 开发（非桌面交付）

仍使用 `XCAGI/.env` 中的 `DATABASE_URL=postgresql+...` 与 `start-xcagi.bat`。

## 后续连接中心 PostgreSQL（Phase 2，本阶段无 UI）

编辑 userData 下的 `config/database.json`：

```json
{
  "version": 1,
  "mode": "remote",
  "remote": {
    "enabled": true,
    "database_url": "postgresql+psycopg://user:pass@db.example.com:5432/xcagi"
  }
}
```

重启应用后，`configure_desktop_environment` 会保留该 URL（`XCAGI_DESKTOP_KEEP_DATABASE_URL=1`）。设置页与迁移工具将在后续版本提供。

## 备份与回滚

见 [customer/CUSTOMER_SUPPORT.md](../customer/CUSTOMER_SUPPORT.md)：`backups/` 下的 `xcagi-*.db`。

## 发版自检

在本机仓库根（`FHD`）依次执行：

```bat
start-desktop-sqlite.bat
```

```powershell
cd E:\XCMAX\FHD
.\.venv\Scripts\python.exe -m pytest tests/test_desktop_runtime.py tests/test_desktop_status_api.py -q
powershell -ExecutionPolicy Bypass -File scripts\package\verify-desktop-database-default.ps1
powershell -ExecutionPolicy Bypass -File scripts\dev\desktop_deliverable_smoke.ps1
powershell -ExecutionPolicy Bypass -File scripts\dev\deliverable_smoke.ps1
```

发版前安全阶段（含桌面库默认校验）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\package\pre-release-security.ps1 -Phase pre
```

浏览器：`http://127.0.0.1:5000/api/desktop/status` → `local_sqlite`；设置页显示「本地数据库（SQLite）」与 `xcagi.db` 路径。

首启本地登录（市场未连通时）：默认账号 `admin` / `admin123`（可通过环境变量 `ADMIN_USERNAME`、`ADMIN_PASSWORD` 覆盖）。企业版桌面在无法连接修茈市场时会自动降级为本地账号登录。

**勿**仅用 `xcagi-backend.cmd`（未加 `--desktop`）做交付验收；Web/Postgres 开发才用该入口。
