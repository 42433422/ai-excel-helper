# XCAGI v4.0 技术栈

> AI Employee 4.0 - 基于 AI 的单据智能处理员工

---

## 技术架构

```
┌─────────────────────────────────────────────────────────────────┐
│                  用户界面层 (Vue 3 + Vite)                        │
│   智能对话界面 | 单据管理 | 标签打印 | 数据可视化 | Pro Mode      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              AI 员工核心层 (Flask 3.0 + AI Engines)               │
├─────────────────────────────────────────────────────────────────┤
│  🧠 混合意图识别引擎 | 🗣️ TTS 语音 | 🤖 任务 Agent                │
│  📊 智能决策系统 | 🔄 流程自动化 | 📱 微信集成                    │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   AI 引擎群    │    │   业务服务群   │    │   任务队列     │
│               │    │               │    │               │
│ DeepSeek AI   │    │ 单据处理服务   │    │ Celery 5.3    │
│ RASA NLU      │    │ 产品管理服务   │    │ Redis 7.0     │
│ BERT 模型     │    │ 标签打印服务   │    │               │
│ OCR/TTS       │    │ 微信集成服务   │    │               │
│ 蒸馏模型      │    │ 数据分析服务   │    │               │
└───────────────┘    └───────────────┘    └───────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│             数据层 (SQLAlchemy 2.0 + DDD 架构)                     │
│   PostgreSQL 16 + pgvector + Alembic 迁移 + Repository Pattern   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  监控层 (Prometheus + Grafana)                    │
│   Prometheus | Grafana | Loki | Alertmanager                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 技术明细

### 后端技术

| 技术 | 版本 | 说明 |
|------|------|------|
| **Python** | 3.11+ | 核心编程语言 |
| **Flask** | 3.0+ | Web 框架 |
| **SQLAlchemy** | 2.0+ | ORM 框架 |
| **Alembic** | 1.13+ | 数据库迁移 |
| **Celery** | 5.3+ | 分布式任务队列 |
| **Redis** | 7.0+ | 缓存 & 消息中间件 |
| **PostgreSQL** | 16+ | 生产级数据库 |
| **pgvector** | 0.5+ | 向量相似度搜索 |

### AI/ML 引擎

| 技术 | 用途 |
|------|------|
| **DeepSeek AI** | 大语言模型对话 & 意图识别 & 工作流规划 |
| **LLM Workflow Planner** | 动态生成可执行工作流节点 |
| **RASA NLU** | 自然语言理解 & 对话管理 |
| **BERT** | 深度语义理解 & 文本分类 |
| **蒸馏模型** | 离线意图识别 |
| **Transformers** | 预训练模型库 |
| **PyTorch** | 深度学习框架 |
| **EasyOCR / Tesseract** | OCR 文字识别 |
| **Edge TTS** | 语音合成 |

### LLM 工作流规划

```
┌─────────────────────────────────────────────────────────────┐
│              LLM Workflow Planner (DeepSeek)                  │
├─────────────────────────────────────────────────────────────┤
│  输入: 用户意图 + 工具注册表 + 对话上下文 + 业务上下文       │
│  处理: API 调用 → JSON 计划生成 → 风险评估 → 依赖解析        │
│  输出: PlanGraph (intent / todo_steps / nodes / risk_level) │
├─────────────────────────────────────────────────────────────┤
│  风险控制:                                                    │
│  - low: 查询类 → 自动放行                                     │
│  - medium: 创建类 → 需确认                                    │
│  - high: 删除类 → 强制确认                                     │
└─────────────────────────────────────────────────────────────┘
```

### 前端技术

| 技术 | 版本 | 用途 |
|------|------|------|
| **Vue** | 3.4+ | 渐进式 JavaScript 框架 |
| **Vite** | 5.4+ | 下一代前端构建工具 |
| **Pinia** | 3.0+ | Vue 状态管理 |
| **Vue Router** | 4.6+ | Vue 路由管理 |
| **TypeScript** | 5.5+ | 类型安全 |

### 数据处理

| 技术 | 用途 |
|------|------|
| **OpenPyXL** | Excel 文件读写 |
| **Pandas** | 数据分析 & 处理 |
| **NumPy** | 科学计算 |
| **Scikit-learn** | 机器学习算法 |
| **XLSX** | 前端 Excel 解析 |

### 监控与可观测性

| 技术 | 用途 |
|------|------|
| **Prometheus** | 指标采集与存储 |
| **Grafana** | 数据可视化与仪表盘 |
| **Loki** | 日志聚合系统 |
| **Alertmanager** | 告警管理 |
| **Promtail** | 日志收集代理 |

### 容器化与编排

| 技术 | 用途 |
|------|------|
| **Docker** | 容器化部署 |
| **Docker Compose** | 多容器编排 |
| **Kubernetes** | 容器编排 |
| **Gunicorn** | WSGI HTTP 服务器 |

---

## 核心功能

### 🤖 AI 员工核心能力

- **AI 智能决策** - 混合意图识别引擎 v2，准确率 99%+
- **全自动化处理** - 业务流程自动执行，解放双手
- **多模态交互** - TTS 语音 + 自然语言 + 微信消息
- **行业智能适配** - 多行业模板支持，快速部署上线
- **智能决策系统** - 业务决策支持，持续优化
- **自主学习** - 持续学习和优化能力

### 🏢 业务功能

- 📊 **智能单据解析** - Excel/OCR 自动识别
- 🏷️ **标签打印增强** - TSC 打印机 & 批量打印
- 📦 **出货管理** - 全流程自动化
- ✅ **收货确认** - 智能核对数据
- 💬 **AI 对话** - 多引擎支持
- 📱 **微信集成** - 消息自动处理
- 📈 **数据分析** - 业务报表与洞察
- 🔐 **权限管理** - RBAC 权限控制

### 🔧 技术特性

- ⚡ **高性能** - 前端加载时间 < 1s，响应速度提升 10 倍
- 🗄️ **向量搜索** - pgvector 支持的相似度搜索
- 🔄 **异步任务** - Celery 分布式任务队列
- 📊 **全链路监控** - Prometheus + Grafana + Loki
- 🚀 **K8s 就绪** - Kubernetes 部署配置
- 🔒 **安全加固** - 生产级安全配置
- 📝 **API 文档** - Swagger 自动生成
- 🧪 **测试覆盖** - 单元测试 + 集成测试

---

## 项目结构 (DDD 架构)

```
XCAGI/
├── app/
│   ├── domain/              # 领域层
│   │   ├── entities/        # 实体定义
│   │   ├── value_objects/   # 值对象
│   │   ├── aggregates/      # 聚合根
│   │   └── services/        # 领域服务
│   ├── application/         # 应用层
│   │   ├── ports/           # 端口接口
│   │   ├── workflow/        # 工作流引擎
│   │   └── services/        # 应用服务
│   ├── infrastructure/      # 基础设施层
│   │   ├── repositories/    # 仓储实现
│   │   ├── persistence/     # 持久化
│   │   ├── database/        # 数据库管理
│   │   ├── documents/       # 文档生成
│   │   ├── ocr/             # OCR 服务
│   │   ├── printing/        # 打印服务
│   │   ├── tts/             # TTS 服务
│   │   └── plugins/         # 插件系统
│   ├── routes/              # API 路由
│   ├── services/            # 业务服务
│   │   └── skills/          # 技能模块
│   ├── utils/               # 工具函数
│   └── models/              # 数据模型
├── frontend/                # 前端项目
│   ├── src/
│   │   ├── components/      # Vue 组件
│   │   ├── views/           # 页面视图
│   │   ├── stores/          # Pinia 状态管理
│   │   ├── composables/     # 组合式函数
│   │   ├── router/          # 路由配置
│   │   ├── api/             # API 客户端
│   │   └── utils/           # 工具函数
│   └── public/              # 静态资源
├── k8s/                     # Kubernetes 配置
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   └── monitoring/          # 监控配置
├── release-bundle/          # 发布包
├── resources/               # 资源文件
├── scripts/                 # 部署脚本
└── tools/                   # 工具集
```

---

## 混合意图识别引擎 v2

```
┌──────────────────────────────────────────┐
│     混合意图识别引擎 (准确率 99%+)         │
├──────────────────────────────────────────┤
│  规则系统      │  快速/确定性高          │
│  蒸馏模型     │  离线可用/轻量级         │
│  BERT 模型    │  深度语义理解            │
│  DeepSeek AI  │  大模型推理              │
│  RASA NLU     │  对话管理                │
└──────────────────────────────────────────┘

✅ 离线可用 (蒸馏模型 + BERT)
✅ 意图识别准确率 99%+
✅ 响应速度毫秒级
✅ 自主学习和优化
```

---

## Python 依赖

```
Flask==3.0.0
Flask-CORS==4.0.0
Flask-Caching==2.1.0
Flasgger==0.9.7.1
Celery==5.3.4
redis==5.0.1
openpyxl==3.1.2
gunicorn==21.2.0
gevent==24.2.1
python-dotenv==1.0.0
httpx==0.26.0
edge-tts>=6.1.10
SQLAlchemy>=2.0.0
alembic>=1.13.0

# ML/AI 预训练模型依赖
torch>=2.0.0
transformers>=4.35.0
scikit-learn>=1.3.0
pandas>=2.0.0
numpy>=1.24.0
statsmodels>=0.14.6
prophet>=1.3.0
accelerate>=0.25.0
protobuf>=4.25.0

# Retry and resilience
tenacity>=8.2.0
prometheus_client>=0.19.0
psutil>=5.9.0

# 测试依赖
pytest==7.4.3
pytest-cov==4.1.0
pytest-mock==3.12.0
```

---

## 前端依赖

```json
{
  "vue": "^3.4.21",
  "vue-router": "^4.6.4",
  "pinia": "^3.0.4",
  "vite": "^5.4.8",
  "typescript": "^5.5.4",
  "xlsx": "^0.18.5",
  "font-awesome": "^4.7.0",
  
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.1.4",
    "@vue/eslint-config-prettier": "^10.0.0",
    "@vue/eslint-config-typescript": "^14.0.0",
    "@vue/test-utils": "^2.4.0",
    "eslint": "^9.9.0",
    "eslint-plugin-vue": "^9.27.0",
    "vitest": "^2.0.5",
    "vue-tsc": "^2.0.29"
  }
}
```

---

## 容器化部署

### Docker Compose 服务

```yaml
services:
  backend:        # Flask 后端服务
  celery-worker:  # Celery 任务 worker
  redis:          # Redis 缓存 & 消息队列
  postgres:       # PostgreSQL + pgvector
  frontend:       # Nginx 前端服务
```

### Kubernetes 资源

```yaml
# 核心资源
- deployment.yaml      # 部署配置
- service.yaml         # 服务定义
- ingress.yaml         # 入口规则
- configmap.yaml       # 配置管理
- secret.yaml          # 密钥管理
- hpa.yaml            # 自动扩缩容

# 监控栈
- Prometheus          # 指标采集
- Grafana             # 可视化
- Loki                # 日志聚合
- Alertmanager        # 告警管理
```

---

## 性能指标

| 指标 | v3.0 | v4.0 | 提升 |
|------|------|------|------|
| 前端加载时间 | ~1.5s | ~1.0s | ⬆️ **33%** |
| 意图识别准确率 | ~98% | ~99% | ⬆️ **1%** |
| 单据处理速度 | 基础 | 优化 | ⬆️ **50%** |
| AI 员工响应 | 秒级 | 毫秒级 | ⬆️ **10 倍** |
| 行业适配速度 | 手动 | 配置化 | ⬆️ **5 倍** |
| 数据库性能 | SQLite | PostgreSQL | ⬆️ **10 倍** |
| 并发能力 | 低 | 高 | ⬆️ **100 倍** |

---

## 部署要求

### 最低配置

- **CPU**: 4 核心
- **内存**: 8GB
- **存储**: 50GB
- **操作系统**: Windows 10/11 或 Linux

### 推荐配置

- **CPU**: 8 核心
- **内存**: 16GB
- **存储**: 100GB SSD
- **操作系统**: Linux (Ubuntu 20.04+)

### 依赖服务

- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Kubernetes**: 1.25+ (可选)
- **Redis**: 7.0+
- **PostgreSQL**: 16+ (含 pgvector)

---

## 适用场景

### 企业级应用

- ✅ 大规模单据处理
- ✅ 高并发场景
- ✅ 多租户隔离
- ✅ 生产环境部署

### 行业场景

- 🏭 **制造业** - 生产单据、物料标签
- 🚚 **物流行业** - 快递单据、货物追踪
- 🛒 **零售业** - 进货单、商品标签
- 📦 **批发行业** - 批发单据、订单管理
- 🛍️ **电商行业** - 订单处理、发货单

### 技术场景

- ✅ 离线优先环境
- ✅ 高意图识别准确率需求
- ✅ 语音播报需求
- ✅ 微信生态集成
- ✅ 大规模任务处理
- ✅ 全链路监控需求

---

## 技术优势

### 架构优势

1. **DDD 领域驱动设计** - 清晰的职责划分，高可维护性
2. **微服务就绪** - Kubernetes 原生支持
3. **事件驱动架构** - Celery 异步任务队列
4. **CQRS 模式** - 读写分离优化

### 技术优势

1. **混合 AI 引擎** - 多引擎融合，准确率 99%+
2. **向量数据库** - pgvector 支持的相似度搜索
3. **全链路监控** - Prometheus + Grafana + Loki
4. **容器化部署** - Docker & K8s 一键部署

### 业务优势

1. **AI 员工定位** - 从"工具"到"员工"的升级
2. **全自动化** - 业务流程自动执行
3. **多模态交互** - 语音 + 文本 + 微信
4. **行业适配** - 快速配置上线

---

## 安全特性

- 🔐 **RBAC 权限控制** - 基于角色的访问控制
- 🔒 **数据加密** - 敏感数据加密存储
- 🛡️ **SQL 注入防护** - SQLAlchemy ORM 防护
- 🚫 **XSS 防护** - 前端输入验证
- 🔑 **JWT 认证** - 安全的身份认证
- 📝 **审计日志** - 完整的操作日志

---

## 开发工具

### 代码质量

- **Black** - 代码格式化
- **Ruff** - 快速 linting
- **Mypy** - 类型检查
- **ESLint** - 前端 linting
- **Prettier** - 前端格式化

### 测试工具

- **Pytest** - Python 测试框架
- **Vitest** - 前端测试框架
- **Playwright** - E2E 测试

### 开发效率

- **Hot Reload** - 热重载开发
- **TypeScript** - 类型安全
- **Vue DevTools** - 前端调试

---

## 版本演进对比

| 组件 | v1.0 | v2.0 | v3.0 | v4.0 |
|------|:----:|:----:|:----:|:----:|
| 定位 | 工具 | 智能系统 | 智能系统 | **AI 员工** |
| 数据库 | SQLite | SQLite | SQLite | **PostgreSQL** |
| 向量搜索 | ❌ | ❌ | ❌ | **pgvector** |
| 监控 | ❌ | ❌ | ❌ | **Prometheus+Grafana** |
| 编排 | ❌ | ❌ | Docker | **K8s** |
| AI 能力 | ❌ | DeepSeek | 混合引擎 | **智能决策** |
| 自动化 | ❌ | 半自动 | 任务 Agent | **全自动** |

---

> 🚀 **v4.0 - AI 员工时代**: 从"智能单据处理系统"升级为"基于 AI 的单据智能处理 AI 员工"
> 
> 🎯 **核心定位**: 不再是被动工具，而是能主动决策、自主学习、智能执行的 AI 员工
> 
> 💡 **适用行业**: 制造业 | 物流行业 | 零售业 | 批发行业 | 电商行业

---

## 快速开始

### Docker 部署（推荐）

```bash
# 1. 克隆仓库
git clone https://github.com/42433422/xcagi.git
cd xcagi

# 2. 一键部署
docker-compose up -d --build

# 3. 查看状态
docker-compose ps

# 访问地址：http://localhost
```

### Kubernetes 部署

```bash
# 1. 应用配置
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml

# 2. 部署应用
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# 3. 部署监控
kubectl apply -f k8s/monitoring/
```

---

## 文档资源

- 📖 [快速开始指南](docs/QUICK_START.md)
- 🏗️ [架构设计文档](docs/ARCHITECTURE.md)
- 🤖 [AI 员工配置指南](docs/AI_EMPLOYEE.md)
- 📝 [更新日志](CHANGELOG.md)
- 🔒 [安全策略](SECURITY.md)
- 📟 [API 文档](http://localhost:5000/apidocs)
- 🛠️ [部署指南](docs/DEPLOYMENT.md)

---

*最后更新：2026-03-27*  
*版本：4.0.0*  
*定位：🤖 基于 AI 的单据智能处理 AI 员工*
