# 全量 Pytest 收敛计划（782 用例）

## 当前（2026-05-26）

| 指标 | 数值 |
|------|------|
| 收集 | **782** |
| 全量 `tests/` | **777 通过 / 0 失败 / 2 skip**（2026-05-26；`pyproject` 默认仅 `tests/`） |
| CI 稳定子集 `CI_STABLE_ONLY=1` | **~127+ 通过**，其余 skip |

## 已修簇

- 发货 `Quantity`、微信任务、产品服务、excel_utils、NeuroBus 核心测试、打印机服务、DB 读 token（ERP 短路）

## 配置注意

- **勿**在根目录无参 `pytest` 同时收集 `XCAGI/xcagi_tests`（与 `tests/` 模块名冲突）；`pyproject.toml` 已仅 `testpaths = ["tests"]`。
- 全量顺序污染：`tests/conftest.py` 每用例清理 `XCAGI_PRODUCT_SKU*` / edition 环境变量。
- 遗留 xcagi：`pytest XCAGI/xcagi_tests --import-mode=importlib`（部分用例缺 `app.db.test_db_manager`）。

## 阶段

- **A**：维持 `CI_STABLE_ONLY` 扩面（每修一文件加入 `conftest` 片段）
- **B**：按上表簇逐个清零，每周目标失败数 < 30
- **C**：去掉 `CI_STABLE_ONLY`，全量进 CI（目标 0 失败）

本地全量：`python -m pytest tests/ -q`  
稳定子集：`$env:CI_STABLE_ONLY='1'; python -m pytest tests/ -q`
