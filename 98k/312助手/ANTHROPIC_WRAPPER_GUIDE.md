# DeepSeek to Anthropic 包装器使用指南

## 🎯 功能说明

这个包装器将 **DeepSeek API** 伪装成 **Anthropic API** 格式，让 OpenClaw 可以直接使用 DeepSeek 而无需配置 Anthropic 认证。

## ✅ 已启动的服务

### 1. DeepSeek MCP Server (端口 5001)
- HTTP: `http://127.0.0.1:5001`
- 用于 Canvas HTTP 请求

### 2. DeepSeek to Anthropic Wrapper (端口 5002) ⭐ 新增
- HTTP: `http://127.0.0.1:5002`
- 完全兼容 Anthropic API 格式
- OpenClaw 可以直接使用

## 🚀 OpenClaw 配置方法

### 方法 1：配置 OpenClaw 使用包装器（推荐）

**步骤：**

1. **停止 Gateway**
   ```bash
   # 在 Gateway 终端按 Ctrl+C
   ```

2. **设置环境变量**
   ```bash
   # 告诉 OpenClaw 使用本地的 Anthropic 兼容 API
   set ANTHROPIC_BASE_URL=http://127.0.0.1:5002/v1
   set ANTHROPIC_API_KEY=sk-fake-key-not-needed
   ```

3. **重启 Gateway**
   ```bash
   openclaw gateway
   ```

4. **验证**
   - 查看日志，应该显示使用 Anthropic provider
   - 尝试使用 Agent，应该可以正常工作

### 方法 2：修改 OpenClaw 配置

**编辑配置文件：**
```
C:\Users\97088\.openclaw\config.json
```

**添加或修改：**
```json
{
  "api": {
    "anthropic": {
      "baseUrl": "http://127.0.0.1:5002/v1",
      "apiKey": "sk-fake-key"
    }
  }
}
```

**重启 Gateway**

## 📝 API 兼容性

### 支持的 Anthropic API 接口

#### 1. POST /v1/messages (Messages API)

**Anthropic 格式请求：**
```json
{
  "model": "claude-3-opus-20240229",
  "max_tokens": 1024,
  "messages": [
    {
      "role": "user",
      "content": "你好"
    }
  ]
}
```

**内部转换为 DeepSeek 格式：**
```json
{
  "model": "deepseek-chat",
  "messages": [
    {
      "role": "user",
      "content": "你好"
    }
  ]
}
```

**返回 Anthropic 格式响应：**
```json
{
  "id": "msg_xxx",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "你好！我是 DeepSeek..."
    }
  ],
  "model": "claude-3-opus-20240229",
  "usage": {
    "input_tokens": 5,
    "output_tokens": 99
  }
}
```

#### 2. GET /v1/models (Models API)

返回 Anthropic 格式的模型列表。

#### 3. GET /v1/models/{model_id}

返回单个模型信息。

## 🧪 测试方法

### 测试 1：健康检查
```bash
curl http://127.0.0.1:5002/health
```

### 测试 2：Messages API
```powershell
$body = @{
    model = "claude-3-opus-20240229"
    max_tokens = 100
    messages = @(@{role = "user"; content = "你好"})
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://127.0.0.1:5002/v1/messages" `
    -Method Post `
    -Body $body `
    -ContentType "application/json"
```

### 测试 3：Models API
```bash
curl http://127.0.0.1:5002/v1/models
```

## 📊 模型映射

| Anthropic 模型 | DeepSeek 模型 |
|---------------|--------------|
| claude-3-opus-20240229 | deepseek-chat |
| claude-3-sonnet-20240229 | deepseek-chat |
| claude-3-haiku-20240307 | deepseek-chat |
| claude-3-5-sonnet-20240620 | deepseek-chat |
| claude-opus-4-6 | deepseek-chat |

## 🔧 高级配置

### 自定义模型映射

编辑 `deepseek_anthropic_wrapper.py`，修改映射表：

```python
ANTHROPIC_TO_DEEPSEEK_MODELS = {
    "claude-3-opus-20240229": "deepseek-chat",
    "claude-3-sonnet-20240229": "deepseek-chat",
    "claude-3-haiku-20240307": "deepseek-chat",
    "claude-3-5-sonnet-20240620": "deepseek-chat",
    "claude-opus-4-6": "deepseek-chat",
    "default": "deepseek-chat"
}
```

### 修改生成参数

```python
AI_TEMPERATURE = 0.7      # 创意程度
MAX_TOKENS = 2000         # 最大 token 数
TIMEOUT = 60              # 超时时间
```

## 🎯 完整使用流程

### 1. 启动服务

```bash
# 终端 1: DeepSeek MCP Server
python deepseek_mcp_server.py

# 终端 2: Anthropic Wrapper
python deepseek_anthropic_wrapper.py

# 终端 3: OpenClaw Gateway
set ANTHROPIC_BASE_URL=http://127.0.0.1:5002/v1
set ANTHROPIC_API_KEY=sk-fake-key
openclaw gateway
```

### 2. 在 OpenClaw 中使用

现在可以直接在 OpenClaw 中使用，就像使用真正的 Anthropic API 一样：

```
用户 → OpenClaw → Anthropic Wrapper → DeepSeek API → 返回响应
```

### 3. 验证

检查 OpenClaw 日志，应该看到：
```
[gateway] agent model: anthropic/claude-opus-4-6
```

## ⚠️ 注意事项

1. **端口占用**
   - 5001: DeepSeek MCP Server
   - 5002: Anthropic Wrapper
   - 18789: OpenClaw Gateway

2. **环境变量**
   - 必须在启动 Gateway 之前设置
   - 使用 `set` 命令（Windows）或 `export`（Linux/Mac）

3. **API 密钥**
   - 可以是任意值（包装器不使用）
   - 但必须设置（OpenClaw 要求）

## 🐛 故障排查

### 问题 1: OpenClaw 仍然报告缺少密钥

**解决：**
```bash
# 确认环境变量已设置
echo %ANTHROPIC_BASE_URL%
echo %ANTHROPIC_API_KEY%

# 重启 Gateway
openclaw gateway
```

### 问题 2: 包装器无法连接

**检查：**
```bash
# 测试包装器
curl http://127.0.0.1:5002/health

# 检查端口
netstat -ano | findstr :5002
```

### 问题 3: API 调用失败

**查看日志：**
- 包装器日志：运行 `deepseek_anthropic_wrapper.py` 的终端
- OpenClaw 日志：`C:\Users\97088\AppData\Local\Temp\openclaw\openclaw-2026-03-11.log`

## 📈 性能优化

1. **连接池** - 复用 HTTP 连接
2. **缓存** - 缓存常用响应
3. **异步** - 使用异步请求
4. **超时** - 设置合理的超时时间

## 🎉 优势

- ✅ **无需认证** - 不需要 Anthropic API 密钥
- ✅ **完全兼容** - OpenClaw 认为在使用 Anthropic
- ✅ **使用 DeepSeek** - 实际调用的是 DeepSeek API
- ✅ **透明转换** - 自动处理格式转换
- ✅ **即插即用** - 启动即可使用

---

**创建时间:** 2026-03-11  
**版本:** 1.0.0  
**状态:** ✅ 运行中
