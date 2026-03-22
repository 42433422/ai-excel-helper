# 快速开始指南

> 5 分钟快速上手 XCAGI v3.0

---

## 📋 前置要求

在开始之前，请确保您的系统满足以下要求：

### 系统要求

- **操作系统**: Windows 10/11
- **Python**: 3.11 或更高版本
- **Node.js**: 18.0 或更高版本（可选，用于前端开发）
- **Redis**: 5.0 或更高版本（用于缓存和任务队列）
- **Git**: 用于克隆仓库

### 验证安装

```bash
# 检查 Python 版本
python --version
# 应该输出：Python 3.11.x 或更高

# 检查 Node.js 版本（可选）
node --version
# 应该输出：v18.x.x 或更高

# 检查 Redis（可选）
redis-cli --version
# 应该输出版本号
```

---

## 🚀 快速安装

### 步骤 1: 克隆仓库

```bash
# 克隆仓库
git clone https://github.com/42433422/xcagi.git

# 进入项目目录
cd xcagi
```

### 步骤 2: 安装后端依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

# 安装 Python 依赖
pip install -r requirements.txt
```

### 步骤 3: 安装前端依赖（可选）

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 返回项目根目录
cd ..
```

### 步骤 4: 配置环境变量

```bash
# 复制环境变量示例文件
cp resources/config/.env.example .env

# 编辑 .env 文件，配置必要的参数
# 使用文本编辑器打开 .env 文件
```

**必要配置项**:

```env
# 数据库配置
DATABASE_URL=sqlite:///products.db

# Redis 配置（可选，用于缓存和任务队列）
REDIS_URL=redis://localhost:6379/0

# DeepSeek AI API 密钥（可选）
DEEPSEEK_API_KEY=your-api-key-here

# Flask 密钥
SECRET_KEY=your-secret-key-here

# 调试模式
DEBUG=True
```

### 步骤 5: 初始化数据库

```bash
# 运行数据库迁移
alembic upgrade head

# 或者使用初始化脚本
python app/db/init_db.py
```

### 步骤 6: 启动服务

#### 方式 1: 快速启动（推荐新手）

```bash
# 启动主服务（包含前端）
python run.py
```

访问：http://localhost:5000

#### 方式 2: 开发模式（前后端分离）

```bash
# 终端 1: 启动后端
python run.py

# 终端 2: 启动前端开发服务器
cd frontend
npm run dev
```

访问：http://localhost:5173（Vite 开发服务器）

#### 方式 3: 完整模式（包含 Celery Worker）

```bash
# 终端 1: 启动后端
python run.py

# 终端 2: 启动 Celery Worker
celery -A celery_app worker --loglevel=info

# 终端 3: 启动 Celery Beat（定时任务，可选）
celery -A celery_app beat --loglevel=info
```

---

## ✅ 验证安装

### 检查服务状态

访问以下地址验证服务是否正常运行：

1. **主界面**: http://localhost:5000
2. **API 文档**: http://localhost:5000/apidocs
3. **健康检查**: http://localhost:5000/api/health

### 运行测试

```bash
# 运行后端测试
pytest

# 运行前端测试
cd frontend
npm test

# 运行端到端测试（可选）
npm run test:e2e
```

### 测试核心功能

1. **Excel 导入**
   - 访问主界面
   - 上传测试 Excel 文件
   - 验证数据解析

2. **AI 对话**
   - 点击 AI 助手
   - 发送消息
   - 验证 AI 响应

3. **标签打印**
   - 进入标签管理
   - 创建标签模板
   - 测试打印功能

---

## 🎯 基本使用

### 1. 创建第一个出货单

1. 访问 http://localhost:5000
2. 点击"出货管理"
3. 点击"新建出货单"
4. 填写信息并保存

### 2. 导入 Excel 数据

1. 点击"Excel 导入"
2. 上传 Excel 文件
3. 系统自动解析数据
4. 确认并保存

### 3. 使用 AI 助手

1. 点击"AI 助手"
2. 输入问题，例如："帮我创建出货单"
3. AI 将引导您完成操作

### 4. 打印标签

1. 进入"标签管理"
2. 选择产品
3. 点击"打印标签"
4. 选择打印机并打印

---

## 🔧 常见问题

### Q: 无法启动服务

**问题**: 启动时提示端口被占用

**解决方案**:
```bash
# 方法 1: 修改端口
# 编辑 run.py，修改端口号
app.run(host='0.0.0.0', port=5001)

# 方法 2: 关闭占用端口的进程
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Linux/macOS
lsof -i :5000
kill -9 <PID>
```

### Q: 数据库初始化失败

**问题**: 运行数据库迁移时报错

**解决方案**:
```bash
# 方法 1: 删除旧数据库文件
rm products.db customers.db

# 方法 2: 重新运行迁移
alembic downgrade base
alembic upgrade head
```

### Q: Redis 连接失败

**问题**: 提示无法连接 Redis

**解决方案**:

1. **安装 Redis**
   - Windows: https://github.com/microsoftarchive/redis/releases
   - Linux: `sudo apt-get install redis-server`
   - macOS: `brew install redis`

2. **启动 Redis**
   ```bash
   # Windows: 运行 redis-server.exe
   # Linux/macOS
   redis-server
   ```

3. **验证 Redis**
   ```bash
   redis-cli ping
   # 应该返回：PONG
   ```

### Q: 前端无法加载

**问题**: 访问前端页面显示空白或错误

**解决方案**:
```bash
# 方法 1: 重新构建前端
cd frontend
npm run build

# 方法 2: 清除缓存
# 浏览器中按 Ctrl+Shift+Delete
# 清除缓存和 Cookie

# 方法 3: 检查控制台错误
# 按 F12 打开开发者工具
# 查看 Console 标签页的错误信息
```

### Q: AI 功能不可用

**问题**: AI 对话或意图识别失败

**解决方案**:

1. **检查 API 密钥**
   ```bash
   # 确保 .env 文件中配置了正确的 API 密钥
   DEEPSEEK_API_KEY=your-api-key-here
   ```

2. **检查网络连接**
   ```bash
   # 测试 API 连接
   curl https://api.deepseek.com
   ```

3. **使用本地模型**
   - 系统支持离线 BERT 模型
   - 确保模型文件在 `distillation/` 目录

---

## 📚 下一步

完成快速开始后，您可以：

1. **阅读完整文档**
   - [架构设计](docs/ARCHITECTURE.md)
   - [部署指南](docs/DEPLOYMENT.md)
   - [API 参考](docs/API_REFERENCE.md)

2. **学习核心功能**
   - [Excel 导入教程](docs/excel_import_api.md)
   - [标签模板指南](LABEL_TEMPLATE_GUIDE.md)
   - [AI 对话使用指南](docs/ai_chat_guide.md)

3. **参与贡献**
   - [贡献指南](.github/CONTRIBUTING.md)
   - [开发规范](.github/CONTRIBUTING.md#代码规范)
   - [Issue 列表](https://github.com/42433422/xcagi/issues)

---

## 🆘 获取帮助

如果您在使用过程中遇到问题：

1. **查看文档**: [完整文档](docs/)
2. **搜索 Issue**: [GitHub Issues](https://github.com/42433422/xcagi/issues)
3. **提交 Issue**: [新建 Issue](https://github.com/42433422/xcagi/issues/new)
4. **查看讨论**: [Discussions](https://github.com/42433422/xcagi/discussions)

---

## 🎉 恭喜！

您已经成功安装并运行了 XCAGI v3.0！

现在可以开始使用智能单据处理系统了。祝您使用愉快！🚀

---

*最后更新：2026-03-23*
