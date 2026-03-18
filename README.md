<<<<<<< HEAD
# XCAGI - AI Excel Helper 2.0

智能发货单处理系统，基于 AI 的 Excel 出货单据智能处理工具，专为家具制造行业的发货管理设计。
=======
# AI-Excel Helper 出货单智能处理系统

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0.html)
[![Python](https://img.shields.io/badge/Python-3.11+-green.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-blue.svg)](https://www.microsoft.com/windows/)

## 项目简介

AI-Excel Helper 是一款基于 AI 的出货单智能处理系统，专门用于家具制造行业的发货管理。通过深度学习 OCR 技术和智能解析算法，自动识别和处理 Excel 出货单据。
>>>>>>> 1a45efbdddedb6e19ae25a882297f4071946d6ee

## 主要功能

### 📊 出货单处理
- 自动识别 Excel 出货单格式
- 智能提取产品型号、数量、价格信息
- 支持多客户数据结构
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
- 多客户数据隔离
- 出货记录追踪
- 价格体系管理

<<<<<<< HEAD
### 🌐 Web 界面
- 现代化 Vue 前端
- 响应式设计
- 实时数据更新
- 智能对话界面

=======
>>>>>>> 1a45efbdddedb6e19ae25a882297f4071946d6ee
## 系统要求

- Windows 10/11
- Python 3.11+
- Microsoft Excel (可选，用于自动化)
- TSC 打印机 (可选，用于标签打印)
<<<<<<< HEAD
- Redis (用于缓存和任务队列)

## 安装步骤

### 1. 克隆仓库
=======

## 安装步骤

1. 克隆仓库
>>>>>>> 1a45efbdddedb6e19ae25a882297f4071946d6ee
```bash
git clone https://github.com/42433422/ai-excel-helper.git
cd ai-excel-helper
```

<<<<<<< HEAD
### 2. 安装依赖
=======
2. 安装依赖
>>>>>>> 1a45efbdddedb6e19ae25a882297f4071946d6ee
```bash
pip install -r requirements.txt
```

<<<<<<< HEAD
### 3. 配置环境变量
```bash
# 设置 DeepSeek API 密钥
set DEEPSEEK_API_KEY=your-api-key-here

# 设置 Flask 密钥（生产环境必需）
set SECRET_KEY=your-secret-key-here
```

### 4. 启动服务
```bash
# 启动主服务
python run.py

# 访问地址: http://localhost:5000
=======
3. 配置 API 密钥（可选）
```bash
# 设置 DeepSeek API 密钥
set DEEPSEEK_API_KEY=your-api-key-here
```

## 使用方法

### 启动主程序
```bash
python AI助手/app_api.py
```

### 启动 Web 界面
```bash
python AI助手/simple_web_app.py
```

### 启动语音助手
```bash
python AI助手/voice_frontend_app.py
>>>>>>> 1a45efbdddedb6e19ae25a882297f4071946d6ee
```

## 项目结构

```
ai-excel-helper/
<<<<<<< HEAD
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

### 1. Excel 解析器
- 智能识别 Excel 表格结构
- 支持多种模板格式
- 自动提取关键信息

### 2. AI 对话系统
- 基于 DeepSeek 模型
- 自然语言处理
- 智能意图识别

### 3. 标签打印系统
- TSC 打印机集成
- 自定义标签模板
- 批量打印功能

### 4. 数据管理系统
- 客户信息管理
- 产品信息管理
- 出货记录追踪

## API 接口

### 主要 API 端点
- `/api/excel/extract` - 提取 Excel 数据
- `/api/shipment/create` - 创建出货单
- `/api/products` - 产品管理
- `/api/customers` - 客户管理
- `/api/ai/chat` - AI 对话接口

### Swagger 文档
访问 `http://localhost:5000/apidocs` 查看完整 API 文档

## 技术栈

### 后端
- Python 3.11+
- Flask 2.0+
- SQLite (本地数据库)
- Redis (缓存/队列)
- Celery (任务队列)

### 前端
- Vue 3
- Vite
- JavaScript
- CSS3

### AI 技术
- DeepSeek API
- OCR 文字识别
- 自然语言处理

## 安全注意事项

- API 密钥通过环境变量配置，不要硬编码在代码中
- 数据库文件已在 .gitignore 中排除，不会上传到仓库
- 生产环境请设置强密码和 HTTPS

## 版本更新

### v2.0 新特性
- 全新 Vue 3 前端界面
- 增强的 AI 对话功能
- 优化的 Excel 解析算法
- 支持更多打印机型号
- 完善的 API 文档
- 增强的错误处理

## 许可证

本项目采用 GNU Affero General Public License v3.0 (AGPL-3.0) 开源许可证。
=======
├── AI助手/                 # 主程序目录
│   ├── app_api.py         # 主 API
│   ├── config.py          # 配置文件
│   ├── shipment_parser.py  # 出货单解析
│   └── ...
├── 产品文件夹/             # 产品数据处理
├── 标签模板/              # 打印标签模板
├── LICENSE               # AGPL-3.0 许可证
└── README.md             # 说明文档
```

## 配置说明

在 `AI助手/config.py` 中配置：

```python
AI_CONFIG = {
    "model_name": "deepseek",
    "api_key": os.environ.get("DEEPSEEK_API_KEY", "your-api-key-here"),
    "base_url": "https://api.deepseek.com/v1",
}
```

## 许可证

本项目采用 **GNU Affero General Public License v3.0 (AGPL-3.0)** 开源许可证。

这意味着：
- ✅ 你可以自由使用本软件
- ✅ 你可以查看和修改源代码
- ✅ 你必须开源任何基于本项目的修改
- ⚠️ 如果你通过网络提供服务，必须开源你的服务代码

详情请参阅 [LICENSE](LICENSE) 文件。

## 注意事项

⚠️ **隐私保护**
- 数据库文件（*.db）已列入 .gitignore，不会上传到仓库
- 出货记录文件夹已排除
- 请勿在代码中硬编码敏感信息
>>>>>>> 1a45efbdddedb6e19ae25a882297f4071946d6ee

## 技术支持

如有问题，请提交 Issue 或联系维护者。

## 作者

<<<<<<< HEAD
GitHub: @42433422

⭐ 如果这个项目对你有帮助，请给我一个 Star！
=======
- GitHub: [@42433422](https://github.com/42433422)

---

⭐ 如果这个项目对你有帮助，请给我一个 Star！
>>>>>>> 1a45efbdddedb6e19ae25a882297f4071946d6ee
