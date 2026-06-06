# Debug Scripts

Put troubleshooting and inspection scripts here.

Typical examples:

- data consistency checks
- API response inspections
- temporary diagnostics for incidents

Do not place long-term business logic in this folder.

## 仓库内脚本

| 脚本 | 说明 |
|------|------|
| `diagnose_pro_mode.py` | 检查 DeepSeek / 专业模式相关配置与 API 连通性（在仓库根执行 `python tools/debug/diagnose_pro_mode.py`） |
| `diagnose_routes.py` | 打印 FastAPI 路由列表（需已安装依赖，在仓库根执行 `python tools/debug/diagnose_routes.py`） |

TCP 端口探测请使用 [`../scripts/launchers/test_port.ps1`](../scripts/launchers/test_port.ps1)（参数 `-TargetHost`、`-Port`）。
