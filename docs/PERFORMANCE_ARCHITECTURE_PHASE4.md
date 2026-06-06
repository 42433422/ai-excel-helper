# Phase 4：架构拆分（按需）

在 Phase 1–3 指标仍不达标时推进，避免过早过度工程。

## API / Worker 分离

- **主 API 进程**：沿用 `deploy/requirements-server-api.txt`，不 import `torch` / 重型 OCR。
- **Sidecar**：BERT 意图、训练、重 OCR 独立进程；主 API 经 HTTP/队列调用。
- **桌面包**：PyInstaller 仅打包 enterprise 白名单 Mod；重模型走 `desktop/models` 按需下载。

## Mod 清单快照

- 构建：`python scripts/package/generate_mods_index.py`（`build-backend.ps1` 在 staged mods 上自动执行）。
- 运行时：`mod_manager.scan_mods` 在指纹一致时读 `mods-index.json`，避免每次 `listdir` + 解析 manifest。

## 前端 vendor

- 在消除 `vite.config.js` 所述 store/router 循环依赖后，可对 `element-plus` 做小范围 `manualChunks`。
- 当前已用 `unplugin-vue-components` + `ElementPlusResolver` 做组件按需。

## Web 企业版

- PostgreSQL 连接池、只读副本、Redis 为桌面 SQLite + 进程内 LRU 的超集；机制与 `performance_initializer` 共用。
