# XCAGI - AI Excel Helper 2.0

智能发货单处理系统，基于 AI 的 Excel 出货单据智能处理工具，专为家具制造行业的发货管理设计。

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

### 1. 克隆仓库
```bash
git clone https://github.com/42433422/ai-excel-helper.git
cd ai-excel-helper
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

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
```

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

## 技术支持

如有问题，请提交 Issue 或联系维护者。

## 作者

GitHub: @42433422

⭐ 如果这个项目对你有帮助，请给我一个 Star！