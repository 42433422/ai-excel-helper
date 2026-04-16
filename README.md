# XCAGI v5.0 - AI 单据智能处理员工

🤖 **基于 AI 的单据智能处理 AI 员工**，适用于各行业的标签打印、出货管理和收货确认场景。

[![Release](https://img.shields.io/github/v/release/42433422/xcagi?color=blue&label=Release&version=v5.0.0)](https://github.com/42433422/xcagi/releases)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0.html)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-red.svg)](https://flask.palletsprojects.com/)
[![Vue](https://img.shields.io/badge/Vue-3.3-brightgreen.svg)](https://vuejs.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-blue.svg)](https://www.microsoft.com/windows/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](https://github.com/42433422/xcagi/blob/main/.github/CONTRIBUTING.md)

## 🌟 项目简介

**XCAGI v5.0** 是一款**基于 AI 的单据智能处理 AI 员工**，适用于各行业的标签打印、出货管理和收货确认。通过深度学习 OCR 技术、混合意图识别引擎和智能决策系统，像真实员工一样自动识别、理解和处理 Excel 单据数据。

> 🚀 **v5.0 当前版本**: 在 v4.0 基础上持续迭代，完善工程化能力、模块体系与交付稳定性
>
> 🎯 **从"工具"到"员工"**: 不再是被动工具，而是能主动决策、自主学习、智能执行的 AI 员工

**快速链接**:
- 📖 [快速开始指南](docs/QUICK_START.md)
- 🏗️ [架构设计文档](docs/ARCHITECTURE.md)
- 🤖 [AI 员工配置指南](docs/AI_EMPLOYEE.md)
- 📚 [完整文档](docs/)
- 📝 [更新日志](CHANGELOG.md)
- 🤝 [贡献指南](.github/CONTRIBUTING.md)

## 🎯 AI 员工核心能力

### 🧠 AI 智能决策
- **LLM 工作流规划** - DeepSeek 驱动的动态工作流生成
- 混合意图识别引擎（准确率 99%+）
- 智能业务决策支持
- 自主学习和持续优化
- 上下文理解和推理

### 🔄 全自动化处理
- 单据自动识别和解析
- 业务流程自动执行
- **LLM 驱动的动态规划** - 智能编排多步骤任务
- 任务自动化 Agent
- 异常自动处理

### 💬 多模态交互
- TTS 语音合成播报
- 自然语言对话界面
- 微信消息自动处理
- 智能语音交互

### 🏢 行业智能适配
- 多行业模板支持
- 灵活配置适配
- 快速部署上线
- 智能规则引擎

## 🏢 适用行业与场景

### 🏭 制造业
- 生产单据处理
- 物料标签打印
- 出货管理
- 质检记录管理

### 🚚 物流行业
- 快递单据识别
- 货物追踪管理
- 签收确认
- 运输单据处理

### 🛒 零售业
- 进货单处理
- 商品标签打印
- 库存管理
- 价格标签更新

### 📦 批发行业
- 批发单据处理
- 客户订单管理
- 价格体系管理
- 出货记录追踪

### 🛍️ 电商行业
- 订单自动处理
- 发货单打印
- 退货管理
- 库存同步

## 📊 AI 员工 vs 传统工具

| 维度 | 传统工具 | XCAGI AI 员工 | 优势 |
|------|----------|---------------|------|
| **决策能力** | 无 | ✅ 智能决策 | 自主判断 |
| **学习能力** | 无 | ✅ 持续优化 | 越用越聪明 |
| **交互方式** | 点击操作 | ✅ 自然语言 + 语音 | 像人一样交流 |
| **自动化** | 半自动 | ✅ 全自动 | 解放双手 |
| **适应性** | 固定流程 | ✅ 灵活适配 | 快速上线 |
| **离线能力** | ❌ 依赖网络 | ✅ 混合离线 | 稳定可靠 |

## ⚡ 性能指标

| 指标 | v3.0 | v4.0 | 提升 |
|------|------|------|------|
| 前端加载时间 | ~1.5s | ~1.0s | ⬆️ **33%** |
| 意图识别准确率 | ~98% | ~99% | ⬆️ **1%** |
| 单据处理速度 | 基础 | 优化 | ⬆️ **50%** |
| AI 员工响应 | 秒级 | 毫秒级 | ⬆️ **10 倍** |
| 行业适配速度 | 手动 | 配置化 | ⬆️ **5 倍** |

## 🔧 系统要求

- Windows 10/11
- Python 3.11+
- Microsoft Excel (可选，用于自动化)
- TSC 打印机 (可选，用于标签打印)
- Redis (用于缓存和任务队列)
- Docker & Docker Compose (推荐)

## 🚀 快速开始

### 方式 1：Docker 一键部署（推荐）

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

### 方式 2：本地部署

```bash
# 1. 克隆仓库
git clone https://github.com/42433422/xcagi.git
cd xcagi

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行数据库迁移
alembic upgrade head

# 4. 启动服务
python run.py

# 访问地址：http://localhost:5000
```

### 方式 3：使用部署脚本

```cmd
# Windows 用户
双击 deploy.bat
选择选项 1 (生产环境部署)
```

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                  用户界面层 (Vue 3 + Vite)                    │
│   智能对话界面 | 单据管理 | 标签打印 | 数据可视化              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              AI 员工核心层 (Flask 3.0 + AI Engines)          │
├─────────────────────────────────────────────────────────────┤
│  🧠 混合意图识别引擎 | 🗣️ TTS 语音 | 🤖 任务 Agent           │
│  📊 智能决策系统 | 🔄 流程自动化 | 📱 微信集成               │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   AI 引擎群    │    │   业务服务群   │    │   任务队列     │
│               │    │               │    │               │
│ DeepSeek AI   │    │ 单据处理服务   │    │ Celery 5.3    │
│ RASA NLU      │    │ 产品管理服务   │    │ Redis 5.0     │
│ BERT 模型     │    │ 标签打印服务   │    │               │
│ OCR/TTS       │    │ 微信集成服务   │    │               │
└───────────────┘    └───────────────┘    └───────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│             数据层 (SQLAlchemy 2.0 + DDD 架构)                │
│   SQLite + Alembic 迁移 + Repository Pattern                 │
└─────────────────────────────────────────────────────────────┘
```

## 💻 技术栈详情

### 后端技术

| 技术 | 版本 | 用途 |
|------|------|------|
| **Python** | 3.11+ | 核心编程语言 |
| **Flask** | 3.0+ | Web 框架 |
| **SQLAlchemy** | 2.0+ | ORM 框架 |
| **Alembic** | 1.13+ | 数据库迁移 |
| **Celery** | 5.3+ | 分布式任务队列 |
| **Redis** | 7.0+ | 缓存 & 消息中间件 |
| **PostgreSQL** | 16+ | 生产级数据库 (含 pgvector) |

### AI/ML 引擎

| 技术 | 用途 |
|------|------|
| **DeepSeek AI** | 大语言模型对话 & 意图识别 |
| **RASA NLU** | 自然语言理解 & 对话管理 |
| **BERT** | 深度语义理解 & 文本分类 |
| **Transformers** | 预训练模型库 |
| **PyTorch** | 深度学习框架 |
| **EasyOCR / Tesseract** | OCR 文字识别 |
| **Edge TTS** | 语音合成 |

### 前端技术

| 技术 | 版本 | 用途 |
|------|------|------|
| **Vue** | 3.3+ | 渐进式 JavaScript 框架 |
| **Vite** | 4.4+ | 下一代前端构建工具 |
| **Pinia** | 3.0+ | Vue 状态管理 |
| **Vue Router** | 4.6+ | Vue 路由管理 |

### 数据处理

| 技术 | 用途 |
|------|------|
| **OpenPyXL** | Excel 文件读写 |
| **Pandas** | 数据分析 & 处理 |
| **NumPy** | 科学计算 |
| **Scikit-learn** | 机器学习算法 |

## 🎯 AI 员工核心场景

### 场景 1：标签打印 AI 员工
```
用户上传 Excel → AI 自动解析 → 生成标签模板 → 自动打印
```
- 自动识别 Excel 格式
- 智能提取产品信息
- 自动生成标签模板
- 批量打印标签

### 场景 2：出货管理 AI 员工
```
接收出货单 → AI 识别产品 → 创建出货记录 → 生成标签 → 打印发货
```
- 自动识别出货单
- 智能匹配产品
- 自动创建出货记录
- 生成并发货标签

### 场景 3：收货确认 AI 员工
```
接收收货单 → AI 核对数据 → 更新库存 → 生成确认单
```
- 自动识别收货单
- 智能核对数据
- 自动更新库存
- 生成确认单据

### 场景 4：微信消息处理 AI 员工
```
接收微信消息 → AI 理解意图 → 自动回复/创建任务 → 同步联系人
```
- 自动接收微信消息
- 智能理解意图
- 自动回复或创建任务
- 同步联系人信息

## 📡 API 接口

### 主要 API 端点

- `/api/excel/extract` - 提取 Excel 数据
- `/api/shipment/create` - 创建出货单
- `/api/shipment/receive` - 创建收货单
- `/api/products` - 产品管理
- `/api/customers` - 客户管理
- `/api/materials` - 物料管理
- `/api/print/label` - 标签打印
- `/api/ai/chat` - AI 对话接口
- `/api/ai/intent` - 意图识别
- `/api/ai/tts` - 语音合成
- `/api/wechat/messages` - 微信消息
- `/api/wechat/contacts` - 联系人同步
- `/api/tasks` - 任务管理

### Swagger 文档

访问 `http://localhost:5000/apidocs` 查看完整 API 文档

## 🔄 版本演进

### v5.0 新特性（当前最新）⭐

- 🤖 **AI 员工定位** - 从"工具"升级为"员工"，主动决策、自主学习
- 🔄 **全自动化流程** - 业务流程自动执行，解放双手
- 💬 **多模态交互** - TTS 语音 + 自然语言 + 微信消息
- 🏢 **行业智能适配** - 多行业模板支持，快速部署上线
- 📊 **智能决策系统** - 业务决策支持，持续优化
- 🎯 **混合意图引擎 v2** - 准确率提升至 99%+
- ⚡ **性能优化** - 前端加载时间降至 1s，响应速度提升 10 倍

### v4.0 特性

- 🎯 混合意图识别引擎 - 规则 + RASA NLU + BERT
- 🔊 TTS 语音合成 - Edge TTS 集成
- 🤖 任务自动化 Agent - 智能任务代理
- 📱 微信生态集成 - 消息自动处理
- 🏷️ 标签打印增强 - TSC 打印机支持
- 🏛️ DDD 领域驱动设计 - 清晰架构

### v3.0 特性

- 🎨 Vue 3 前端界面 - 现代化 Web 界面
- 🤖 AI 对话系统 - DeepSeek 集成
- 📸 OCR 识别 - 文字自动识别
- 📊 多客户隔离 - 数据安全管理

### v2.0 特性

- 📊 Excel 解析 - 自动识别单据
- 🏷️ 标签打印 - TSC 打印机支持

## 📊 技术栈演进对比

| 组件 | v1.0 | v2.0 | v3.0 | v4.0 |
|------|:----:|:----:|:----:|:----:|
| 定位 | 工具 | 智能系统 | 智能系统 | **AI 员工** |
| 自动化 | ❌ | 半自动 | 任务 Agent | **全自动** |
| 交互 | 命令行 | Web 界面 | 对话界面 | **多模态** |
| AI 能力 | ❌ | DeepSeek | 混合引擎 | **智能决策** |
| 架构 | 单文件 | MVC | DDD | **DDD+** |

## ⚠️ 注意事项

**隐私保护**:
- 数据库文件（*.db）已列入 .gitignore，不会上传到仓库
- 出货记录文件夹已排除
- 请勿在代码中硬编码敏感信息

**安全建议**:
- API 密钥通过环境变量配置
- 生产环境请设置强密码和 HTTPS
- 定期备份数据库文件

## 🤝 贡献指南

我们欢迎各种形式的贡献！

### 如何贡献

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 开发环境设置

```bash
# 克隆仓库
git clone https://github.com/42433422/xcagi.git
cd xcagi

# 安装依赖
pip install -r requirements.txt

# 运行测试
pytest
```

详细信息请查阅 [贡献指南](.github/CONTRIBUTING.md)

## 📚 文档资源

- 📖 [快速开始指南](docs/QUICK_START.md) - 5 分钟快速上手
- 🏗️ [架构设计文档](docs/ARCHITECTURE.md) - DDD 架构详解
- 🤖 [AI 员工配置指南](docs/AI_EMPLOYEE.md) - 行业适配配置
- 📝 [更新日志](CHANGELOG.md) - 版本更新历史
- 🔒 [安全策略](SECURITY.md) - 安全报告指南
- 📟 [API 文档](http://localhost:5000/apidocs) - Swagger 文档
- 🛠️ [部署指南](docs/DEPLOYMENT.md) - 生产和开发部署

## 🗺️ 路线图

### v5.x 计划（当前）

- [x] AI 员工定位升级
- [x] 全自动化流程
- [x] 多模态交互
- [ ] 移动端 App 支持
- [ ] 多语言支持（国际化）
- [ ] 云端部署方案
- [ ] 更多行业模板

### v6.0 展望

- [ ] 支持更多 AI 模型本地部署
- [ ] 微服务架构改造
- [ ] 实时协作功能
- [ ] AI 模型自主训练
- [ ] 区块链存证

## 🙏 致谢

感谢以下开源项目：

- [Vue.js](https://vuejs.org/) - 渐进式 JavaScript 框架
- [Flask](https://flask.palletsprojects.com/) - Python Web 框架
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL 工具包
- [DeepSeek](https://www.deepseek.com/) - AI 大模型
- [RASA](https://rasa.com/) - 开源对话 AI
- [Hugging Face](https://huggingface.co/) - 预训练模型库

## 📄 许可证

本项目采用 **GNU Affero General Public License v3.0 (AGPL-3.0)** 开源许可证。

这意味着：
- ✅ 你可以自由使用本软件
- ✅ 你可以查看和修改源代码
- ✅ 你必须开源任何基于本项目的修改
- ⚠️ 如果你通过网络提供服务，必须开源你的服务代码

详情请参阅 [LICENSE](LICENSE) 文件。

## 📬 联系方式

- **作者**: [@42433422](https://github.com/42433422)
- **Issues**: [提交 Issue](https://github.com/42433422/xcagi/issues)
- **Discussions**: [参与讨论](https://github.com/42433422/xcagi/discussions)

## 🌟 支持项目

如果这个 AI 员工对你有帮助，请给我一个 Star！⭐

你的支持是我持续改进的动力！

---

<div align="center">

**XCAGI v5.0 - AI 单据智能处理员工**

🤖 适用于各行业的标签打印、出货管理和收货确认

[🔝 返回顶部](#xcagi-v50---ai-单据智能处理员工)

</div>
