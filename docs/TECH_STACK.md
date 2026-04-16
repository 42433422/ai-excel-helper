# FHD 技术栈（单一说明）

本文件为 **修茈官网（根目录静态站）** 与 **Excel 助手后端（`backend/`）** 的权威技术栈说明。其它位置若出现不一致描述，以本文为准。

## 官网（`index.html` / `styles.css` / `main.js`）

| 层级 | 选型 | 说明 |
|------|------|------|
| 标记与样式 | 原生 HTML5 + CSS3 | 无构建步骤，便于静态托管 |
| 动效 | Canvas 2D（`main.js`） | 粒子与连线背景 |
| 部署 | 任意静态站点托管 | GitHub Pages、对象存储 + CDN 等 |

## 后端（`backend/`）

| 层级 | 选型 | 版本约束见 `requirements.txt` |
|------|------|--------------------------------|
| HTTP | FastAPI + Uvicorn | OpenAPI 自动生成（`/docs`） |
| 数据与 Excel | pandas、openpyxl | 读写 `.xlsx` / `.xlsm` / `.xls` |
| 向量与语义 | sentence-transformers、torch、numpy | 本地或缓存模型 |
| LLM 调用 | OpenAI 兼容客户端（`openai`） | 可对接 DeepSeek 等兼容端点 |
| 时序（可选） | Prophet | 图表/预测相关能力 |
| 测试 | pytest | `pytest.ini` 指定 `backend/tests` |

## 环境变量（后端常用）

| 变量 | 作用 |
|------|------|
| `WORKSPACE_ROOT` | 工作区根路径；上传文件写入其下 `uploads/` |
| `CORS_ALLOW_ORIGINS` | 逗号分隔允许来源，默认 `*` |
| `HOST` / `PORT` | Uvicorn 监听地址与端口 |
| `AUDIT_LOG_PATH` | 若设置，将结构化审计日志以 JSON Lines 追加写入 |
| `FHD_API_KEYS` | 若设置（逗号分隔），除健康检查与文档外需携带 `X-API-Key` 或 `Authorization: Bearer <key>` |

详见 [ENTERPRISE_AUDIT.md](./ENTERPRISE_AUDIT.md) 与 [PERFORMANCE_LOAD_TESTING.md](./PERFORMANCE_LOAD_TESTING.md)。

## 图像 / OCR（实验脚本与规划）

官网文案中的 OCR 能力与 **`scripts/` 下 PaddleOCR 实验脚本**对应；目标架构（PaddleOCR 主线、规则引擎、表格、Ensemble、微调、VLM）见 **[OCR_ARCHITECTURE.md](./OCR_ARCHITECTURE.md)**。
