# OpenClaw Canvas 直接使用 DeepSeek（无需认证）

## 问题说明

OpenClaw Gateway 的 Control UI 需要加密的认证令牌，但我们可以通过更简单的方式直接使用 DeepSeek：

**解决方案：在 OpenClaw Canvas 中直接配置 HTTP 请求节点**

## 快速开始

### 步骤 1：确认 DeepSeek MCP Server 运行中

```bash
# 测试 DeepSeek 服务
curl http://127.0.0.1:5001/health
```

应该返回：
```json
{"status":"ok","service":"DeepSeek MCP Server","version":"1.0.0"}
```

### 步骤 2：在 OpenClaw Canvas 中配置

1. **打开 Canvas**
   ```
   http://127.0.0.1:18789/__openclaw__/canvas/
   ```

2. **创建新的 Flow**
   - 点击 "New Flow" 或 "+" 创建新流程

3. **添加 HTTP Request 节点**
   - 从节点面板拖拽 "HTTP Request" 节点到画布
   - 配置如下：

   **Basic Settings:**
   - **Name:** `DeepSeek Chat`
   - **URL:** `http://127.0.0.1:5001/chat`
   - **Method:** `POST`

   **Headers:**
   ```
   Content-Type: application/json
   ```

   **Body (JSON):**
   ```json
   {
     "message": "{{user_input}}",
     "use_tools": true,
     "conversation_id": "{{flow_id}}"
   }
   ```

4. **添加 JSON Parse 节点**
   - 连接 HTTP Request 节点的输出到 JSON Parse 节点
   - 配置提取字段：
     - `reply` → AI 回复内容
     - `conversation_id` → 会话 ID
     - `usage` → Token 使用情况

5. **添加 Response 节点**
   - 连接 JSON Parse 节点到 Response 节点
   - 配置回复内容：`{{reply}}`

### 步骤 3：测试 Flow

1. **添加 Trigger 节点**
   - 添加一个 "Webhook" 或 "Manual Trigger" 节点

2. **测试运行**
   - 点击 "Run" 或 "Test" 按钮
   - 输入测试消息，如："你好"
   - 查看 AI 回复

## 完整的 Flow 示例

```
┌─────────────┐
│   Trigger   │  (用户输入)
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ HTTP Request│  → http://127.0.0.1:5001/chat
│  (POST)     │
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ JSON Parse  │  → 提取 reply 字段
└──────┬──────┘
       │
       ↓
┌─────────────┐
│  Response   │  → 返回 AI 回复
└─────────────┘
```

## 高级配置

### 1. 使用工具调用

如果要使用工具（查询数据库、读取 Excel 等）：

```json
{
  "message": "{{user_input}}",
  "use_tools": true
}
```

### 2. 禁用工具（纯对话）

```json
{
  "message": "{{user_input}}",
  "use_tools": false
}
```

### 3. 指定对话上下文

```json
{
  "message": "{{user_input}}",
  "conversation_id": "{{session_id}}",
  "use_tools": true
}
```

### 4. 错误处理

添加错误处理节点：

```
HTTP Request → [成功] → JSON Parse → Response
             → [失败] → Error Handler → Error Response
```

## API 接口参考

### /chat (推荐)

**请求:**
```json
{
  "message": "你好",
  "use_tools": true,
  "conversation_id": "会话 ID"
}
```

**响应:**
```json
{
  "reply": "你好！我是你的智能助手...",
  "conversation_id": "会话 ID",
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 50,
    "total_tokens": 60
  }
}
```

### /completions (标准 OpenAI 格式)

**请求:**
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

**响应:**
```json
{
  "id": "chatcmpl-xxx",
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "你好！我是..."
      }
    }
  ],
  "usage": {...}
}
```

### /tools/<tool_name>

**请求:**
```json
{
  "parameters": {
    "file_path": "C:/data.xlsx",
    "sheet_name": "Sheet1"
  }
}
```

**响应:**
```json
{
  "tool": "read_excel",
  "result": {...}
}
```

## 可用的工具

1. **read_excel** - 读取 Excel 文件
   - 参数：`file_path`, `sheet_name`(可选)

2. **search_products** - 搜索产品
   - 参数：`keyword`

3. **get_customers** - 获取客户列表
   - 参数：无

4. **get_shipments** - 查询出货单
   - 参数：`customer_name`(可选), `date_range`(可选)

## 示例场景

### 场景 1：客户查询助手

```
用户输入 → HTTP Request (/chat) → 
JSON Parse → Response

Body: {
  "message": "查询客户：{{customer_name}}",
  "use_tools": true
}
```

### 场景 2：产品搜索

```
用户输入 → HTTP Request (/chat) → 
JSON Parse → Response

Body: {
  "message": "搜索产品：{{product_keyword}}",
  "use_tools": true
}
```

### 场景 3：Excel 数据分析

```
用户上传文件 → HTTP Request (/tools/read_excel) → 
JSON Parse → HTTP Request (/chat) → 
JSON Parse → Response

Body 1: {
  "parameters": {
    "file_path": "{{uploaded_file}}"
  }
}

Body 2: {
  "message": "分析这个 Excel 文件的数据",
  "use_tools": false
}
```

## 故障排查

### 问题 1: HTTP Request 失败

**症状:** 节点显示红色错误

**检查:**
1. DeepSeek MCP Server 是否运行
2. URL 是否正确：`http://127.0.0.1:5001/chat`
3. 端口 5001 是否被占用
4. 防火墙设置

**解决:**
```bash
# 测试连接
curl http://127.0.0.1:5001/health

# 如果失败，重启服务器
python deepseek_mcp_server.py
```

### 问题 2: 响应解析失败

**症状:** JSON Parse 节点报错

**检查:**
1. HTTP 响应是否是有效 JSON
2. JSON Parse 配置是否正确
3. 字段名称是否匹配

**解决:**
- 使用 `{{response}}` 查看原始响应
- 检查 JSON Parse 的字段映射

### 问题 3: AI 回复为空

**症状:** Response 节点返回空内容

**检查:**
1. DeepSeek API 密钥是否正确
2. 请求消息格式是否正确
3. 查看服务器日志

**解决:**
```bash
# 查看服务器日志
# 在运行 deepseek_mcp_server.py 的终端查看
```

## 性能优化

### 1. 使用连接池

在 HTTP Request 节点中启用 Keep-Alive

### 2. 设置超时

```json
{
  "timeout": 60
}
```

### 3. 缓存结果

对于频繁查询，添加缓存节点

### 4. 异步处理

对于耗时操作，使用异步节点

## 安全建议

1. **本地部署** - 仅监听 127.0.0.1
2. **API 密钥** - 使用环境变量存储
3. **输入验证** - 添加输入验证节点
4. **错误处理** - 完善的错误处理流程
5. **日志记录** - 记录所有请求和响应

## 下一步

1. ✅ 启动 DeepSeek MCP Server
2. ✅ 在 Canvas 中配置 HTTP Request 节点
3. ⏳ 创建你的第一个 AI Flow
4. ⏳ 测试和优化
5. ⏳ 部署到生产环境

## 更多资源

- DeepSeek 文档：`DEEPSEEK_MCP_SERVER_README.md`
- 流程图：`DEEPSEEK_FLOWCHART.md`
- 集成示例：`openclaw_direct_integration.py`

---

**创建时间:** 2026-03-11  
**版本:** 1.0.0  
**状态:** ✅ 可用
