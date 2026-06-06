"""列出 FastAPI 应用注册的路由（调试用）。从仓库根加入 sys.path。"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.fastapi_app import get_fastapi_app

app = get_fastapi_app()

print(f"App: {app}")
print(f"App routes count: {len(app.routes)}")
print("\nAll routes:")
for route in app.routes:
    if hasattr(route, "path"):
        print(f"  {route.path}")
    elif hasattr(route, "url_path"):
        print(f"  {route.url_path}")

print("\n\nSearching for sales-contract routes:")
for route in app.routes:
    if hasattr(route, "path") and "sales" in route.path.lower():
        print(f"  FOUND: {route.path}")
    elif hasattr(route, "url_path") and "sales" in str(route.url_path).lower():
        print(f"  FOUND: {route.url_path}")
