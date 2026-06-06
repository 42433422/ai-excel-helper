# API 快照与前端接口指南

本目录包含面向前端和集成测试的 API 快照与说明。

- `openapi.json`：由 CI 在每次构建时从运行中的 FastAPI 应用导出，用于前端对照与契约检查。

如何在本地生成快照（开发者）：

```bash
# 在后端可启动的环境下运行（能 import app.fastapi_app）
python -c "from app.fastapi_app import get_fastapi_app; import json; json.dump(get_fastapi_app().openapi(), open('docs/api/openapi.json','w'), ensure_ascii=False, indent=2)"
```

前端开发者使用方式：
- 用作 mock server contract，或与 `frontend/src/utils/apiBase.ts` 对照接口名称与路径。
- 若 CI 报告 openapi.json 有改动，请同时更新前端的调用代码或与后端协商接口变更。

