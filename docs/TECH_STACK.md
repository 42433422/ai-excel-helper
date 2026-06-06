# FHD (XCAGI) 技术栈

> 本文件为 XCAGI v8.0 项目的权威技术栈说明。其它位置若出现不一致描述，以本文为准。
> 更新日期：2026-05-26

---

## 一、总体架构

| 维度 | 选型 | 说明 |
|------|------|------|
| 架构模式 | Neuro-DDD | 领域驱动设计 + AI 用例编排 |
| 交付形态 | 桌面版 + Web 版 | Electron 桌面壳 + FastAPI 子进程 / Nginx + FastAPI |
| 部署方式 | Docker / K8s / 桌面安装包 | 灵活部署选项 |

---

## 二、后端技术栈

### 2.1 核心框架

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| HTTP 框架 | FastAPI | 0.100+ | REST API 服务，自动 OpenAPI 文档 |
| ASGI 服务器 | Uvicorn | 0.20+ | 异步 WSGI 服务器 |
| 生产服务器 | Gunicorn | 21.0+ | 进程管理 + Uvicorn worker |
| Python | Python | 3.10+ | 运行环境 |

### 2.2 数据库

| 场景 | 技术 | 说明 |
|------|------|------|
| Web 版 | PostgreSQL | 生产环境主数据库 |
| 桌面版 | SQLite | 本地数据库，无需额外服务 |
| ORM | SQLAlchemy | 2.0+ 版本，类型安全 |
| 迁移 | Alembic | 数据库版本管理 |

### 2.3 缓存与队列

| Web 版 | 桌面版 | 用途 |
|--------|--------|------|
| Redis | 内存队列 | 缓存、会话、限流 |
| Celery | 本地队列 | 异步任务处理 |

### 2.4 AI 与机器学习

| 能力 | 技术 | 说明 |
|------|------|------|
| LLM 调用 | OpenAI SDK | 兼容 DeepSeek、GPT 等 |
| 意图识别 | Rasa NLU | 本地 NLU 模型 |
| 意图识别 | BERT / sentence-transformers | 语义理解 |
| OCR | PaddleOCR | 表格识别、文字提取 |
| TTS | Edge TTS / 阿里云 | 语音合成 |
| 规则引擎 | 自研 | 快速规则匹配 |

### 2.5 开发与测试

| 工具 | 用途 |
|------|------|
| pytest | 单元测试框架 |
| black | 代码格式化 |
| flake8 | 代码检查 |
| mypy | 类型检查 |

---

## 三、前端技术栈

### 3.1 Web 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue | 3.x | 前端框架 |
| TypeScript | 4.9+ | 类型安全 |
| Vite | 4.x | 构建工具 |
| Vue Router | 4.x | 路由管理 |
| Pinia | 2.x | 状态管理 |
| Axios | 1.x | HTTP 客户端 |
| Element Plus | 2.x | UI 组件库 |

### 3.2 桌面端

| 技术 | 用途 |
|------|------|
| Electron | 桌面应用框架 |
| TypeScript | 主进程代码 |
| electron-builder | 安装包打包 |

### 3.3 微信小程序

| 技术 | 用途 |
|------|------|
| 微信原生 | 小程序开发 |
| WXML/WXSS | 页面结构和样式 |

---

## 四、基础设施

### 4.1 部署与运维

| 技术 | 用途 |
|------|------|
| Docker | 容器化 |
| Docker Compose | 本地开发环境 |
| Kubernetes | 生产编排 |
| Nginx | 反向代理 |
| GitHub Actions | CI/CD |

### 4.2 监控与日志

| 技术 | 用途 |
|------|------|
| 结构化日志 | 应用日志 |
| Prometheus | 指标采集（规划中） |
| Loki | 日志聚合（规划中） |

---

## 五、环境变量（后端常用）

| 变量 | 作用 |
|------|------|
| `DATABASE_URL` | 数据库连接字符串 |
| `REDIS_URL` | Redis 连接字符串（Web 版） |
| `XCAGI_DESKTOP_MODE` | 启用桌面运行时（=1 时启用 SQLite/本地队列） |
| `CORS_ORIGINS` | 跨域允许来源 |
| `OPENAI_API_KEY` | LLM API 密钥 |
| `OPENAI_BASE_URL` | LLM API 端点 |
| `ENABLE_RASA` | RASA NLU 开关 |
| `AUDIT_LOG_PATH` | 审计日志路径 |
| `FHD_API_KEYS` | API 密钥（粗粒度接入控制） |

---

## 六、相关文档

- [架构设计](./ARCHITECTURE.md)
- [部署指南](./DEPLOYMENT.md)
- [快速开始](./QUICK_START.md)
- [企业级能力](./ENTERPRISE_AUDIT.md)
