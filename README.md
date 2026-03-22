# XCAGI - AI Excel Helper 3.0

智能单据处理系统，基于 AI 的 Excel 单据智能处理工具，适用于标签打印、出货管理、收货确认等各行业的单据处理场景。

[![Release](https://img.shields.io/github/v/release/42433422/xcagi?color=blue&label=Release)](https://github.com/42433422/xcagi/releases)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0.html)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0-red.svg)](https://flask.palletsprojects.com/)
[![Vue](https://img.shields.io/badge/Vue-3.3-brightgreen.svg)](https://vuejs.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-blue.svg)](https://www.microsoft.com/windows/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](https://github.com/42433422/xcagi/blob/main/.github/CONTRIBUTING.md)

## 🌟 项目简介

AI-Excel Helper 是一款基于 AI 的单据智能处理系统，适用于各行业的标签打印、出货管理和收货确认。通过深度学习 OCR 技术和智能解析算法，自动识别和处理 Excel 单据数据。

> 🚀 **v3.0 重大更新**: 混合意图识别引擎 + TTS 语音合成 + 任务自动化 Agent + DDD 领域驱动设计

**快速链接**:
- 📖 [快速开始指南](docs/QUICK_START.md)
- 🏗️ [架构设计文档](docs/ARCHITECTURE.md)
- 📚 [完整文档](docs/)
- 📝 [更新日志](CHANGELOG.md)
- 🤝 [贡献指南](.github/CONTRIBUTING.md)

## 主要功能

### 📊 单据处理
- 自动识别 Excel 出货单/收货单格式
- 智能提取产品型号、数量、价格信息
- 支持多客户/多供应商数据结构
- 自动同步数据到数据库

### 🖨️ 标签打印
- 自动生成产品标签
- 支持 TSC 打印机
- 批量打印功能
- 个性化标签模板

### 🤖 AI 智能识别
- DeepSeek AI 模型集成
- OCR 文字识别
- 智能解析模糊信息
- 自动纠错功能

### 📁 数据管理
- SQLite 数据库存储
- 多客户/多供应商数据隔离
- 出货/收货记录追踪
- 价格体系管理

### 🌐 Web 界面
- 现代化 Vue 前端
- 响应式设计
- 实时数据更新
- 智能对话界面

## 系统要求

- Windows 10/11
- Python 3.11+
- Microsoft Excel (可选，用于自动化)
- TSC 打印机 (可选，用于标签打印)
- Redis (用于缓存和任务队列)

## 安装步骤

1. 克隆仓库

```bash
git clone https://github.com/42433422/ai-excel-helper.git
cd ai-excel-helper
```

2. 安装依赖

```bash
pip install -r requirements.txt
```

3. 配置 API 密钥（可选）

```bash
# 设置 DeepSeek API 密钥
set DEEPSEEK_API_KEY=your-api-key-here
```

也可以参考并复制一份示例环境变量文件：

- `XCAGI/resources/config/.env.example`

4. 启动服务

```bash
# 启动主服务
python run.py

# 访问地址: http://localhost:5000
```

## 目录结构（迁移后：两大文件夹）

- **代码**：`XCAGI/app/`（后端）+ `XCAGI/frontend/`（前端）
- **资源**：`XCAGI/resources/`（运行期需要的模板/配置/可选工具数据，保证不依赖项目外路径）

`resources/` 推荐子目录：

- `resources/config/`：配置与 `.env.example`
- `resources/db_seed/`：初始 sqlite（可选，用于首次运行/打包复制）
- `resources/templates/`：模板资源（发货单/标签模板等）
- `resources/ai_assistant/`：旧 AI 助手迁移过来的 uploads/outputs 等资源
- `resources/wechat-decrypt/`、`resources/wechat_cv/`：微信相关可选资源
- `resources/tools_legacy/`、`resources/docs/`：历史脚本/资料归档

## 项目结构

```
ai-excel-helper/
├── app/                 # 主应用目录
│   ├── routes/          # API 路由
│   ├── services/        # 业务逻辑服务
│   ├── utils/           # 工具函数
│   ├── db/              # 数据库模型
│   ├── config.py        # 配置文件
│   └── __init__.py      # 应用初始化
├── frontend/            # 前端代码
│   ├── src/             # Vue 源码
│   └── public/          # 静态资源
├── templates/           # HTML 模板
├── temp_excel/          # 临时 Excel 文件
├── tests/               # 测试代码
├── requirements.txt     # 依赖文件
└── run.py               # 启动脚本
```

## 核心功能模块

### 1. 智能单据处理系统
- 支持出货单、收货单、标签打印等多场景
- 自动识别 Excel 表格结构
- 支持多种模板格式
- 自动提取关键信息
- 多客户/多供应商数据隔离

### 2. AI 对话系统
- 基于 DeepSeek 大模型
- 自然语言处理
- 智能意图识别
- 上下文管理
- 工具调用协调

### 3. 混合意图识别引擎
- 规则系统：快速、确定性高
- RASA NLU：处理变体表达、口语化
- BERT 模型：深度语义理解
- 三重保障，准确率 98%+

### 4. 标签打印系统
- TSC 打印机集成
- 自定义标签模板
- 批量打印功能
- 模板自动生成

### 5. 数据管理系统
- 客户信息管理
- 产品信息管理
- 出货/收货记录追踪
- 价格体系管理
- 物料管理

### 6. TTS 语音合成
- Edge TTS 集成
- 多种语音音色
- 语速音调调节
- 实时语音播报

### 7. 微信生态集成
- 微信消息自动处理
- 联系人同步
- 消息解密
- 任务自动创建

### 8. 任务自动化 Agent
- 智能任务代理
- 自动执行复杂流程
- 异步任务队列
- 任务状态追踪

## API 接口

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

## 🏗️ 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                      前端 (Vue 3 + Vite)                      │
│   Vue 3.3 + Pinia 3.0 + Vue Router 4.6                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     API 网关 (Flask 3.0)                     │
│   Flask + Flasgger (Swagger) + CORS + Celery                │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   AI 引擎      │    │   业务服务     │    │   任务队列     │
│               │    │               │    │               │
│ DeepSeek AI   │    │ 出货单处理     │    │ Celery 5.3    │
│ RASA NLU      │    │ 产品管理       │    │ Redis 5.0     │
│ BERT 模型     │    │ 标签打印       │    │               │
│ OCR/TTS       │    │ 微信集成       │    │               │
└───────────────┘    └───────────────┘    └───────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  数据层 (SQLAlchemy 2.0 + DDD)                │
│   SQLite + Alembic 迁移 + Repository Pattern                 │
└─────────────────────────────────────────────────────────────┘
```

## 💻 技术栈详情

### 后端技术

| 技术 | 版本 | 用途 |
|------|------|------|
| **Python** | 3.11+ | 核心编程语言 |
| **Flask** | 3.0+ | Web 框架 |
| **SQLAlchemy** | 2.0+ | ORM |
| **Alembic** | 1.13+ | 数据库迁移 |
| **Celery** | 5.3+ | 分布式任务队列 |
| **Redis** | 5.0+ | 缓存 & 消息中间件 |
| **SQLite** | - | 本地数据库 |

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

## 安全注意事项

- API 密钥通过环境变量配置，不要硬编码在代码中
- 数据库文件已在 .gitignore 中排除，不会上传到仓库
- 生产环境请设置强密码和 HTTPS

## 📊 性能对比

### v2.0 vs v3.0

| 指标 | v2.0 | v3.0 | 提升 |
|------|------|------|------|
| 前端加载时间 | ~3s | ~1.5s | ⬆️ **50%** |
| 意图识别准确率 | ~85% | ~98% | ⬆️ **13%** |
| 响应速度 | 基础 | 优化 | ⬆️ **显著提升** |
| 离线可用性 | ❌ | ✅ | ⬆️ **完全支持** |
| 架构模式 | MVC | DDD | ⬆️ **可维护性** |

### 技术栈升级对比

| 组件 | v2.0 | v3.0 | 改进 |
|------|------|------|------|
| Flask | 2.0+ | 3.0+ | 性能提升、新特性 |
| SQLAlchemy | 基础 | 2.0+ | 更好的类型支持 |
| 数据库迁移 | 手动 | Alembic | 自动化版本管理 |
| 前端状态管理 | - | Pinia 3.0+ | 现代化、TypeScript |
| 构建工具 | 基础 | Vite 4.4+ | 热更新、更快构建 |
| 意图识别 | 云端 API | 混合离线 | 成本可控、离线可用 |
| 架构模式 | 简单分层 | DDD | 清晰的职责划分 |

## 🔄 版本更新

### v3.0 新特性（当前最新）

- 🎯 **混合意图识别引擎** - 规则系统 + RASA NLU + BERT 深度学习模型，意图识别准确率提升至 98%
- 🔊 **TTS 语音合成** - 集成 Edge TTS，支持多种语音音色，实现智能语音播报
- 🧠 **AI 大模型集成** - DeepSeek AI 深度集成，支持自然语言理解和智能对话
- 📊 **智能单据解析** - 支持出货单、收货单、标签打印等多场景单据自动识别
- 🤖 **任务自动化 Agent** - 智能任务代理，自动执行复杂业务流程
- 📱 **微信生态集成** - 微信消息自动处理、联系人同步、消息解密
- 🏷️ **标签打印增强** - 支持 TSC 打印机、批量打印、模板自定义
- 🗄️ **数据库优化** - SQLAlchemy ORM + Alembic 迁移、多客户数据隔离
- ⚡ **异步任务队列** - Celery + Redis 分布式任务队列，支持高并发
- 🎨 **Vue 3 前端** - 全新 Vue 3 + Vite 前端，响应式设计，性能提升 50%
- 🏛️ **DDD 领域驱动设计** - 领域层、应用层、基础设施层，清晰的职责划分

### v2.0 新特性

- 全新 Vue 3 前端界面
- 增强的 AI 对话功能
- 优化的 Excel 解析算法
- 支持更多打印机型号
- 完善的 API 文档
- 增强的错误处理

## 许可证

本项目采用 **GNU Affero General Public License v3.0 (AGPL-3.0)** 开源许可证。

这意味着：
- ✅ 你可以自由使用本软件
- ✅ 你可以查看和修改源代码
- ✅ 你必须开源任何基于本项目的修改
- ⚠️ 如果你通过网络提供服务，必须开源你的服务代码

详情请参阅 [LICENSE](LICENSE) 文件。

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
- 📝 [更新日志](CHANGELOG.md) - 版本更新历史
- 🔒 [安全策略](SECURITY.md) - 安全报告指南
- 📟 [API 文档](http://localhost:5000/apidocs) - Swagger 文档
- 🛠️ [部署指南](docs/DEPLOYMENT.md) - 生产和开发部署

## 🗺️ 路线图

### v3.x 计划

- [ ] 移动端 App 支持
- [ ] 多语言支持（国际化）
- [ ] 云端部署方案
- [ ] 更多打印机型号支持
- [ ] 高级数据分析功能

### v4.0 展望

- [ ] 支持更多 AI 模型本地部署
- [ ] 微服务架构改造
- [ ] 实时协作功能
- [ ] AI 模型自主训练

## 🙏 致谢

感谢以下开源项目：

- [Vue.js](https://vuejs.org/) - 渐进式 JavaScript 框架
- [Flask](https://flask.palletsprojects.com/) - Python Web 框架
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL 工具包
- [DeepSeek](https://www.deepseek.com/) - AI 大模型
- [RASA](https://rasa.com/) - 开源对话 AI
- [Hugging Face](https://huggingface.co/) - 预训练模型

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

如果这个项目对你有帮助，请给我一个 Star！⭐

你的支持是我持续改进的动力！

---

<div align="center">

**XCAGI - AI Excel Helper 3.0**

[🔝 返回顶部](#xcagi---ai-excel-helper-30)

</div>
