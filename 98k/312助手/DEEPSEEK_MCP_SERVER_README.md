# DeepSeek MCP Server 使用指南

## 概述

DeepSeek MCP Server 是一个为 OpenClaw 提供 DeepSeek AI 能力的包装层服务。它作为 OpenClaw 和 DeepSeek API 之间的桥梁，让 OpenClaw 可以通过 HTTP API 调用 DeepSeek 的强大功能。

## 架构

```
OpenClaw (ws://127.0.0.1:18789)
    ↓
    ↓ HTTP 请求
    ↓
DeepSeek MCP Server (http://127.0.0.1:5001)
    ↓
    ↓ 调用 DeepSeek API
    ↓
DeepSeek API (https://api.deepseek.com/v1)
```

## 快速开始

### 1. 安装依赖

确保已安装以下 Python 包：

```bash
pip install flask requests pandas openpyxl
```

### 2. 配置 API 密钥

编辑 `config/deepseek_config.py` 文件，设置 DeepSeek API 密钥：

```python
# 方法 1：直接在配置文件中设置（不推荐用于生产环境）
DEEPSEEK_API_KEY = 'sk-your-api-key-here'

# 方法 2：使用环境变量（推荐）
# 在系统环境变量中设置 DEEPSEEK_API_KEY
```

### 3. 启动服务器

```bash
cd "e:\FHD\新建文件夹 (4)\AI 助手"
python deepseek_mcp_server.py
```

启动成功后会显示：

```
============================================================
DeepSeek MCP Server 启动中...
============================================================
API 密钥：已配置
API 地址：https://api.deepseek.com/v1
使用模型：deepseek-chat
监听端口：5001
============================================================
OpenClaw 可以通过以下地址调用：
  对话接口：http://127.0.0.1:5001/chat
  标准接口：http://127.0.0.1:5001/completions
  健康检查：http://127.0.0.1:5001/health
============================================================
```

### 4. 测试服务器

```bash
python test_deepseek_server.py
```

## API 接口

### 1. 健康检查接口

**URL:** `GET /health`

**响应示例:**
```json
{
  "status": "ok",
  "service": "DeepSeek MCP Server",
  "version": "1.0.0"
}
```

### 2. 智能对话接口（推荐）

**URL:** `POST /chat`

**请求格式:**
```json
{
  "message": "查询客户 A 的出货单",
  "conversation_id": "会话 ID（可选）",
  "use_tools": true
}
```

**响应格式:**
```json
{
  "reply": "根据查询，客户 A 有以下出货单...",
  "conversation_id": "会话 ID",
  "usage": {
    "prompt_tokens": 100,
    "completion_tokens": 200,
    "total_tokens": 300
  }
}
```

**Python 示例:**
```python
import requests

response = requests.post(
    "http://127.0.0.1:5001/chat",
    json={
        "message": "你好，请介绍一下你自己",
        "use_tools": False
    }
)

result = response.json()
print(result["reply"])
```

### 3. 标准 Completions 接口（OpenAI 兼容）

**URL:** `POST /completions`

**请求格式:**
```json
{
  "model": "deepseek-chat",
  "messages": [
    {"role": "user", "content": "你好"}
  ],
  "temperature": 0.7,
  "max_tokens": 2000
}
```

**响应格式:** 标准的 OpenAI 格式响应

### 4. 工具列表接口

**URL:** `GET /tools`

**响应示例:**
```json
{
  "tools": [
    {
      "name": "read_excel",
      "description": "读取 Excel 文件内容",
      "parameters": {...}
    },
    {
      "name": "search_products",
      "description": "搜索产品信息",
      "parameters": {...}
    }
  ]
}
```

### 5. 直接调用工具

**URL:** `POST /tools/<tool_name>`

**示例 - 读取 Excel:**
```bash
curl -X POST http://127.0.0.1:5001/tools/read_excel \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"file_path": "C:/data/products.xlsx", "sheet_name": "Sheet1"}}'
```

**示例 - 获取客户列表:**
```bash
curl -X POST http://127.0.0.1:5001/tools/get_customers \
  -H "Content-Type: application/json" \
  -d '{"parameters": {}}'
```

## OpenClaw 集成

### 在 OpenClaw Canvas 中配置

1. 打开 OpenClaw Canvas: `http://127.0.0.1:18789/__openclaw__/canvas/`

2. 添加 HTTP 请求节点，配置如下：
   - **URL:** `http://127.0.0.1:5001/chat`
   - **Method:** `POST`
   - **Headers:** `Content-Type: application/json`
   - **Body:** 
     ```json
     {
       "message": "{{user_input}}",
       "use_tools": true
     }
     ```

3. 连接节点，处理返回的 `reply` 字段

### 使用示例技能

#### 出货单查询
```json
{
  "message": "查询客户 A 在 2026 年 3 月的出货单",
  "use_tools": true
}
```

#### 产品搜索
```json
{
  "message": "搜索型号为 A001 的产品",
  "use_tools": true
}
```

#### 读取 Excel
```json
{
  "message": "读取 C:/data/report.xlsx 文件，分析里面的数据",
  "use_tools": true
}
```

## 可用工具

当前支持的工具：

1. **read_excel** - 读取 Excel 文件
   - 参数：`file_path` (必需), `sheet_name` (可选)

2. **search_products** - 搜索产品
   - 参数：`keyword` (必需)

3. **get_customers** - 获取客户列表
   - 参数：无

4. **get_shipments** - 查询出货单
   - 参数：`customer_name` (可选), `date_range` (可选)

## 配置选项

编辑 `config/deepseek_config.py` 可以修改以下配置：

```python
# API 密钥
DEEPSEEK_API_KEY = 'sk-your-key'

# API 基础地址
DEEPSEEK_API_BASE = 'https://api.deepseek.com/v1'

# 模型选择
DEEPSEEK_MODEL = 'deepseek-chat'

# 生成参数
AI_TEMPERATURE = 0.7      # 创意程度（0-1）
MAX_TOKENS = 2000         # 最大 token 数
TIMEOUT = 60              # 超时时间（秒）

# 服务器配置
OPENCLAW_API_PORT = 5001  # 监听端口
```

## 故障排查

### 1. 服务器无法启动

**检查端口是否被占用:**
```bash
netstat -ano | findstr :5001
```

**解决方案:** 修改配置中的 `OPENCLAW_API_PORT` 为其他端口

### 2. API 调用失败

**检查 API 密钥是否正确:**
```python
from config.deepseek_config import DEEPSEEK_API_KEY
print(DEEPSEEK_API_KEY)
```

**检查网络连接:**
```bash
ping api.deepseek.com
```

### 3. 工具调用失败

**检查依赖包:**
```bash
pip install pandas openpyxl
```

**检查文件路径:** 确保 Excel 文件路径正确且可访问

## 高级用法

### 自定义工具

在 `deepseek_mcp_server.py` 中添加新的工具函数：

```python
def my_custom_tool(param1, param2):
    """自定义工具描述"""
    # 实现逻辑
    return {"result": "数据"}

# 注册工具
TOOLS_REGISTRY["my_tool"] = {
    "name": "my_tool",
    "description": "我的自定义工具",
    "parameters": {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "参数 1"},
            "param2": {"type": "number", "description": "参数 2"}
        },
        "required": ["param1"]
    },
    "function": my_custom_tool
}
```

### 连接真实数据库

修改工具函数，连接实际的数据库：

```python
import sqlite3

def get_customers():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM customers")
    customers = cursor.fetchall()
    conn.close()
    
    return {
        "customers": [
            {"name": row[0], "contact": row[1], "phone": row[2]}
            for row in customers
        ]
    }
```

## 性能优化建议

1. **使用连接池** - 数据库查询使用连接池
2. **缓存结果** - 对频繁查询的结果进行缓存
3. **异步处理** - 对耗时操作使用异步处理
4. **限制并发** - 设置合理的并发请求数

## 安全注意事项

1. **不要硬编码 API 密钥** - 使用环境变量
2. **限制访问来源** - 只允许本地访问（127.0.0.1）
3. **添加认证** - 生产环境添加 API 认证
4. **日志记录** - 记录所有请求用于审计

## 技术支持

如有问题，请检查：
1. 服务器日志输出
2. 测试脚本的运行结果
3. DeepSeek API 文档：https://platform.deepseek.com/docs

---

**版本:** 1.0.0  
**更新日期:** 2026-03-11
