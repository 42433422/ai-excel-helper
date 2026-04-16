# OpenClaw Canvas 使用 DeepSeek（最终方案）

## 问题说明

OpenClaw Gateway 的认证配置复杂，403 错误难以解决。

**推荐方案：在 Canvas 中直接使用 HTTP 请求调用 DeepSeek MCP Server**

## 配置步骤

### 1. 确认服务运行

```bash
# DeepSeek MCP Server 应该在运行
curl http://127.0.0.1:5001/health
```

### 2. 打开 Canvas

访问：`http://127.0.0.1:18789/__openclaw__/canvas/`

### 3. 创建 Flow

#### 步骤 1：添加 Trigger 节点

- 从节点面板拖拽 "Trigger" 节点
- 配置触发条件（如 Webhook 或 Manual）

#### 步骤 2：添加 HTTP Request 节点

- 拖拽 "HTTP Request" 节点到画布
- **配置如下：**

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
  "use_tools": true
}
```

#### 步骤 3：添加 JSON Parse 节点

- 连接 HTTP Request 的输出到 JSON Parse
- **配置提取字段：**
  - Field Name: `reply`
  - JSON Path: `$.reply`

#### 步骤 4：添加 Response 节点

- 连接 JSON Parse 到 Response
- **配置回复内容：** `{{reply}}`

### 4. 完整 Flow 示例

```
┌─────────────┐
│   Trigger   │  (用户输入：user_input)
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ HTTP Request│  → POST /chat
│  (DeepSeek) │     {"message": "{{user_input}}"}
└──────┬──────┘
       │
       ↓
┌─────────────┐
│ JSON Parse  │  → 提取 reply
└──────┬──────┘
       │
       ↓
┌─────────────┐
│  Response   │  → {{reply}}
└─────────────┘
```

## 测试 Flow

1. 点击 "Run" 或 "Test" 按钮
2. 输入测试消息："你好"
3. 查看响应

**预期结果：**
```
你好！我是 DeepSeek，很高兴为你服务...
```

## 高级用法

### 1. 使用工具调用

```json
{
  "message": "帮我查询客户列表",
  "use_tools": true
}
```

### 2. 禁用工具（纯对话）

```json
{
  "message": "你好，请介绍一下你自己",
  "use_tools": false
}
```

### 3. 带上下文的对话

```json
{
  "message": "{{user_input}}",
  "conversation_id": "{{flow_id}}",
  "use_tools": true
}
```

### 4. 错误处理

添加错误处理分支：

```
HTTP Request → [成功 200] → JSON Parse → Response
             → [失败] → Error Handler → Error Response
```

## API 参考

### POST /chat

**请求体：**
```json
{
  "message": "用户消息",
  "use_tools": true/false,
  "conversation_id": "会话 ID（可选）"
}
```

**响应：**
```json
{
  "reply": "AI 回复",
  "conversation_id": "会话 ID",
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 50,
    "total_tokens": 60
  }
}
```

### POST /tools/{tool_name}

**请求体：**
```json
{
  "parameters": {
    "file_path": "C:/data.xlsx"
  }
}
```

**响应：**
```json
{
  "tool": "read_excel",
  "result": {...}
}
```

## 可用工具

1. **read_excel** - 读取 Excel 文件
2. **search_products** - 搜索产品
3. **get_customers** - 获取客户列表
4. **get_shipments** - 查询出货单

## 故障排查

### 问题 1: HTTP Request 失败

**检查：**
```bash
curl http://127.0.0.1:5001/health
```

如果失败，重启 MCP Server：
```bash
python deepseek_mcp_server.py
```

### 问题 2: 响应解析失败

- 检查 JSON Parse 配置
- 使用 `{{response}}` 查看原始响应
- 确认字段名称正确

### 问题 3: 工具调用失败

- 检查工具是否启用
- 查看 MCP Server 日志
- 确认工具参数正确

## 优势

- ✅ **无需认证配置** - 直接调用
- ✅ **简单快速** - 几分钟内完成
- ✅ **功能完整** - 支持所有工具
- ✅ **易于调试** - 可以看到完整请求/响应

## 总结

与其解决 Gateway 的 403 问题，不如直接使用 Canvas HTTP 请求：

1. ✅ 配置简单
2. ✅ 无需认证
3. ✅ 功能完整
4. ✅ 已经测试成功

现在就开始在 Canvas 中创建你的第一个 AI Flow 吧！

---

**创建时间:** 2026-03-11 23:00  
**状态:** ✅ 推荐方案
