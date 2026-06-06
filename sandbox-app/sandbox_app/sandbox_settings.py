"""沙盒路径与运行时开关（不含密钥逻辑，密钥走环境变量）。"""

from __future__ import annotations

import os
from pathlib import Path

# sandbox-app/ 目录
SANDBOX_ROOT = Path(__file__).resolve().parent.parent

# FHD 单仓根（含 app/、mods/、templates/vue-dist）
FHD_REPO_ROOT = SANDBOX_ROOT.parent

# 桌面模式数据根：xcagi.db 在 <RUNTIME_ROOT>/data/xcagi.db
DEFAULT_RUNTIME_ROOT = SANDBOX_ROOT / "data" / "runtime"
RUNTIME_ROOT = Path(os.environ.get("SANDBOX_RUNTIME_ROOT", DEFAULT_RUNTIME_ROOT)).expanduser().resolve()

# 可选：把 FHD 前端 dist 链到 web_static；不存在则回退 templates/vue-dist
WEB_STATIC = SANDBOX_ROOT / "web_static"
VUE_DIST_FALLBACK = FHD_REPO_ROOT / "templates" / "vue-dist"

# 部署在 https://host/sandbox/ 且 nginx 去掉前缀转发到本进程时，浏览器仍请求 /sandbox/assets/...
# 设为 "/sandbox"（无尾部斜杠）；本地直连 5099 时留空
SANDBOX_URL_PREFIX = (os.environ.get("SANDBOX_URL_PREFIX") or "").strip().rstrip("/")

# 启动时删库重来（危险，仅沙盒）
SANDBOX_RESET_ON_BOOT = (os.environ.get("SANDBOX_RESET_ON_BOOT") or "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def resolve_vue_dist_dir() -> Path:
    if WEB_STATIC.is_dir() and (WEB_STATIC / "index.html").is_file():
        return WEB_STATIC
    return VUE_DIST_FALLBACK


def default_mods_root() -> Path:
    raw = (os.environ.get("SANDBOX_MODS_ROOT") or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return (FHD_REPO_ROOT / "mods").resolve()
