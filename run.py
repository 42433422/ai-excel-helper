"""XCAGI API 启动入口（仓库根；CI / gunicorn 使用）。"""
from __future__ import annotations

from app.fastapi_app import get_fastapi_app

app = get_fastapi_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5000)
