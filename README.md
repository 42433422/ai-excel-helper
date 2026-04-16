# XCAGI v5.0 - AI 单据智能处理员工

🤖 **基于 Neuro-DDD（分层 + AI 用例编排）与 FastAPI 的 AI 单据智能处理系统**，适用于各行业的标签打印、出货管理和收货确认场景。

[![Release](https://img.shields.io/github/v/release/42433422/xcagi?color=blue&label=Release&version=v5.0.0)](https://github.com/42433422/xcagi/releases)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0.html)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![Flask](https://img.shields.io/badge/Flask-3.0%20%28兼容%2F遗留%29-red.svg)](https://flask.palletsprojects.com/)
[![Architecture](https://img.shields.io/badge/Architecture-Neuro--DDD-purple.svg)](#-neuro-ddd-与代码落点必读)
[![Vue](https://img.shields.io/badge/Vue-3.3-brightgreen.svg)](https://vuejs.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-blue.svg)](https://www.microsoft.com/windows/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](https://github.com/42433422/ai-excel-helper/blob/master/.github/CONTRIBUTING.md)

## 🌟 项目简介

**XCAGI v5.0** 通过 OCR、混合意图识别与大模型工作流，把「上传 Excel / 对话指令 → 解析 → 业务动作（出货、打印、库存等）」连成可运维的闭环。

> 🚀 **v5.0 当前版本**: `Neuro-DDD + FastAPI` 主 API 入口，模块生态（MODstore / Mod Manager）、工作流前端组件、数据库读鉴权与兼容层并存演进。  
> 🎯 **从「工具」到「员工」**: 侧重可编排的用例与可替换的基础设施实现，而不是把业务规则堆在路由里。  
> 🧠 **Neuro-DDD 在本仓库的含义**: **DDD 分层**（`application` / `domain` / `infrastructure`）+ **AI 对话与工作流的用例编排**；HTTP 层尽量薄，装配集中在 Composition Root（`app/bootstrap.py`）。下文示意图帮助理解边界，**以源码为准**。

**仓库**: 默认以 **[ai-excel-helper](https://github.com/42433422/ai-excel-helper)** 为一体化交付树（与历史 **xcagi** 发行说明互通，克隆地址见下文）。

**快速链接**:
- 📖 [快速开始指南](docs/QUICK_START.md)
- 🏗️ [架构设计文档](docs/ARCHITECTURE.md)
- 🤖 [AI 员工配置指南](docs/AI_EMPLOYEE.md)
- 📚 [完整文档](docs/)
- 📝 [更新日志](CHANGELOG.md)
- 🤝 [贡献指南](.github/CONTRIBUTING.md)

---

## 🧠 Neuro-DDD 与代码落点（必读）

| 层级 / 组件 | 代码落点 | 说明 |
|-------------|----------|------|
| **主 API 运行时（默认）** | `backend/http_app.py` | FastAPI `app`，挂载 `/api/*`、CORS、SSE 对话、上传与业务路由 |
| **启动命令（推荐）** | 见下文「快速开始」 | `uvicorn backend.http_app:app --host 127.0.0.1 --port 8000` |
| **兼容层** | `backend/routers/xcagi_compat.py` 等 | 承接旧版前端路径与请求形状，减少一次性大改 |
| **装配根** | `app/bootstrap.py` | `@lru_cache` 将 **application** 与 **infrastructure** 接线（仓储、生成器、外部 IO） |
| **应用服务（用例编排）** | `app/application/` | 编排、事务与用例级逻辑；路由应优先调用此处 |
| **领域层** | `app/domain/` | 实体、值对象、领域服务 |
| **基础设施** | `app/infrastructure/` | ORM、仓储实现、文件与第三方调用 |
| **历史 HTTP（迁移中）** | `app/routes/*`（Flask Blueprint） | 仍可能承载部分业务接口；与 FastAPI **并行存在**，按模块逐步迁移 |

**依赖方向（约定）**: `routes` → `application` → (`domain` + `infrastructure` 抽象)；领域核心不依赖具体 ORM。更细的约束与示例见 [`app/application/README.md`](app/application/README.md)。

**OpenAPI**: 启动后访问 `http://127.0.0.1:8000/docs` 与 `/redoc`。

---

## 🚀 三大产品路线（概览）

| 路线 | 说明 | 典型落点 |
|------|------|----------|
| **Mod 仓库** | 扩展功能与行业包，核心尽量不 fork | `mods/`、`/api/mod-store/*`、Mod Manager |
| **小程序** | 移动侧 CRM / 单据能力 | `/api/mp*` 族接口、`miniprogram/` |
| **传统模式** | 类资源管理器 + 表格工作流，降低上手成本 | 前端「传统模式」视图与对应 API（以 OpenAPI 为准） |

---

## 🎯 AI 员工核心能力

### 🧠 AI 智能决策
- **LLM 工作流规划**（DeepSeek 等）与工具调用闭环
- 混合意图识别（规则 + NLU + 模型，随部署变化）
- 业务确认流、风险门与工作流中断恢复（见运行时与 OpenAPI）

### 🔄 全自动化处理
- 单据解析 → 结构化 → 写库 / 出单 / 打印链路
- 异常与重试策略（HTTP 层、LLM 与任务队列按部署启用）

### 💬 多模态交互
- 对话、TTS、微信与打印等通道按模块启用

### 🏢 行业与模板
- 多行业模板与 Mod 覆盖

---

## 🏢 适用行业与场景

### 🏭 制造业
- 生产单据、物料标签、出货与质检记录

### 🚚 物流与批发
- 快递/批发单据、签收、价格与出货追踪

### 🛒 零售与电商
- 进货、价签、库存与发货协同

---

## 📊 AI 员工 vs 传统工具

| 维度 | 传统工具 | XCAGI AI 员工 | 优势 |
|------|----------|---------------|------|
| **架构** | 脚本/单体 | **Neuro-DDD + FastAPI** | 分层清晰、可替换实现 |
| **决策** | 无 | 对话 + 工作流 | 可编排、可审计 |
| **交互** | 表单为主 | 对话 + 业务 UI | 降低重复操作 |
| **自动化** | 半自动 | 端到端链路 | 减少人工拷贝 |
| **扩展** | 改核心 | **Mod** | 行业包隔离 |

---

## ⚡ 性能指标

下表为版本迭代中的**内部对比与目标取向**（环境、模型与数据不同会导致差异），非第三方审计 SLA。

| 指标 | v3.0 | v4.0 | v5.0 |
|------|------|------|------|
| 前端加载（典型） | ~1.5s | ~1.0s | 视构建与网络 |
| 意图与对话延迟 | 秒级 | 优化 | **显著依赖模型与路由** |
| 行业适配 | 手动配置 | 配置化 | **Mod / 模板 + 策略** |

---

## 🔧 系统要求

- Windows 10/11 或 Linux（以实际部署为准）
- Python 3.11+
- PostgreSQL 16+（推荐，含 pgvector）或按迁移支持的 DB
- Redis（缓存 / 队列，按场景）
- Docker & Docker Compose（可选，推荐生产）

---

## 🚀 快速开始

### 克隆本仓库（一体化树）

```bash
git clone https://github.com/42433422/ai-excel-helper.git
cd ai-excel-helper
```

（历史文档中若出现 `xcagi` 仓库名，多为同源发行说明；**以你实际推送的远程为准**。）

### 方式 1：Docker（若提供 compose）

```bash
docker-compose up -d --build
docker-compose ps
```

### 方式 2：本地 Python

```bash
pip install -r requirements.txt
alembic upgrade head
python -m uvicorn backend.http_app:app --host 127.0.0.1 --port 8000
```

浏览器打开：**http://127.0.0.1:8000/docs**。

### 方式 3：Windows 部署脚本

若仓库根目录提供 `deploy.bat` / `deploy-release.bat`，可按脚本菜单选择生产或开发配置。

---

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────────────┐
│           用户界面层 (Vue 3 + Vite + TypeScript)                      │
│     对话 / 单据 / 打印 / Pro Mode / 工作流 / 读库门禁                  │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│     API 层（FastAPI，`backend/http_app.py`）                          │
│     业务 Router + `xcagi_compat` 兼容 + CORS + 审计/限流（如有）      │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│              Neuro-DDD（`app/`：分层 + 用例编排）                       │
├─────────────────────────────────────────────────────────────────────┤
│  Flask 蓝图（`app/routes`，迁移中）或 FastAPI 路由 →                  │
│  `application`（用例）→ `domain`（规则）→ `infrastructure`（实现）   │
│  装配：`app/bootstrap.py`                                           │
└─────────────────────────────────────────────────────────────────────┘
                │                              │
                ▼                              ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│ LLM / OCR / 工具执行       │    │ PostgreSQL / Redis / 文件   │
└──────────────────────────┘    └──────────────────────────┘
```

---

## 💻 技术栈详情

### 后端技术

| 技术 | 版本 | 用途 |
|------|------|------|
| **Python** | 3.11+ | 核心语言 |
| **FastAPI** | 0.110+ | **默认 Web 与 OpenAPI** |
| **Flask** | 3.0+ | **遗留蓝图**（`app/routes`，迁移中） |
| **Uvicorn** | - | ASGI 服务器 |
| **SQLAlchemy** | 2.0+ | ORM |
| **Alembic** | 1.13+ | 迁移 |
| **Celery / Redis** | 按场景 | 异步任务与缓存 |
| **PostgreSQL** | 16+ | 生产库（含 pgvector） |

### AI / 数据

| 技术 | 用途 |
|------|------|
| **DeepSeek 等 LLM** | 对话、规划、工具调用 |
| **RASA / BERT / 蒸馏** | NLU 与意图（按部署） |
| **PyTorch / Transformers** | 模型推理 |
| **PaddleOCR / EasyOCR** | OCR |
| **OpenPyXL / Pandas** | Excel 与表格 |

### 前端技术

| 技术 | 用途 |
|------|------|
| **Vue 3 + Vite + TS** | SPA |
| **Pinia / Vue Router** | 状态与路由 |

---

## 🎯 AI 员工核心场景（示例）

### 标签打印
用户上传 Excel → 解析 → 模板/标签 → 打印队列。

### 出货管理
识别订单文本或表格 → 预览 → 确认 → 出货记录与打印。

### 收货与库存
单据核对 → 库存更新（以实际模块与权限为准）。

### 微信与对话
消息接入 → 意图 → 工具或业务流程（按启用模块）。

---

## 📡 API 接口（摘录）

完整列表以 **OpenAPI** 为准（`/docs`）。

- `/api/health` — 健康检查  
- `/api/chat`、`/api/chat/stream` — 对话与流式输出  
- `/api/upload/*` — 上传与运行时上下文  
- `/api/template`、`/api/word/*`、`/api/excel/*` — 模板与文档处理  
- `/api/fhd/*` — 身份、读库令牌、AI 策略等  
- `/api/mod-store/*` — 模块市场相关  
- `/api/*`（兼容路由）— 旧版路径族  

---

## 🔄 版本演进

### v5.0（当前主线）

- **FastAPI 主入口**：`backend.http_app` 统一对外 API 与兼容层  
- **Neuro-DDD 分层**：`app/application`、`app/domain`、`app/infrastructure` + `app/bootstrap.py` 装配  
- **模块生态**：MODstore、Mod Manager、前后端 Mod 路由注册  
- **读库鉴权与门禁**：前端令牌提示与 API 协同  
- **工作流与 Pro Mode UI**：可视化与员工站组件  
- **隐私与安全发布**：移除数据库与大文件敏感物，公开仓库可审计  

### v4.0 及更早

- AI 员工定位、自动化流程、多模态、DDD 演进等（见 `CHANGELOG.md`）。

---

## 📊 技术栈演进对比

| 组件 | v1.0 | v2.0 | v3.0 | v4.0 | **v5.0** |
|------|:----:|:----:|:----:|:----:|:--------:|
| 定位 | 工具 | 智能系统 | 智能系统 | AI 员工 | **AI 员工 + 模块生态** |
| 主 API | - | - | Flask 为主 | Flask + 演进 | **FastAPI 为主** |
| 架构 | 单文件 | MVC | DDD | DDD+ | **Neuro-DDD + 兼容层** |
| 扩展 | ❌ | ❌ | ❌ | 有限 | **Mod / Mod Store** |

---

## ⚠️ 注意事项

**隐私**: 数据库文件、密钥与大体积私有资源勿提交；以 `.gitignore` 与发布检查清单为准。

**安全**: API Key 与数据库凭据使用环境变量；生产环境务必 HTTPS 与最小权限。

---

## 🤝 贡献指南

1. Fork **[ai-excel-helper](https://github.com/42433422/ai-excel-helper)**  
2. 新建分支 `feature/...`  
3. 提交并推送后开启 Pull Request  

开发环境示例：

```bash
git clone https://github.com/42433422/ai-excel-helper.git
cd ai-excel-helper
pip install -r requirements.txt
pytest
```

详见 [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md)。

---

## 📚 文档资源

- [快速开始](docs/QUICK_START.md)  
- [架构](docs/ARCHITECTURE.md)  
- [AI 员工配置](docs/AI_EMPLOYEE.md)  
- [CHANGELOG](CHANGELOG.md)  
- [SECURITY](SECURITY.md)  
- [部署](docs/DEPLOYMENT.md)  
- 在线 API：`http://127.0.0.1:8000/docs`  

---

## 🗺️ 路线图（节选）

- [x] FastAPI 主入口与兼容层  
- [x] Neuro-DDD 分层与 Mod 生态  
- [ ] 更广覆盖的自动化测试与 CI  
- [ ] 国际化与更多行业模板  

---

## 🙏 致谢

[Vue.js](https://vuejs.org/)、[FastAPI](https://fastapi.tiangolo.com/)、[Uvicorn](https://www.uvicorn.org/)、[SQLAlchemy](https://www.sqlalchemy.org/)、[DeepSeek](https://www.deepseek.com/)、[RASA](https://rasa.com/)、[Hugging Face](https://huggingface.co/) 等开源项目。

---

## 📄 许可证

**AGPL-3.0** — 详见 [LICENSE](LICENSE)。

---

## 📬 联系方式

- **作者**: [@42433422](https://github.com/42433422)  
- **Issues**: [ai-excel-helper Issues](https://github.com/42433422/ai-excel-helper/issues)  

---

<div align="center">

**XCAGI v5.0 — Neuro-DDD + FastAPI 一体化交付**

[🔝 返回顶部](#xcagi-v50---ai-单据智能处理员工)

</div>
