# HTTP 403 错误修复指南

## 问题说明

OpenClaw 调用包装器时返回 **HTTP 403 Forbidden** 错误：
```
HTTP 403 forbidden: Request not allowed
```

## 原因分析

403 错误通常由以下原因引起：

1. **CORS 限制** - 跨域请求被阻止
2. **请求头验证** - 缺少必要的请求头
3. **OPTIONS 预检请求** - 浏览器/客户端的预检请求未处理
4. **认证问题** - API 密钥验证失败

## 已实施的修复

### 1. 启用 CORS 支持

在包装器中添加了 CORS 支持：

```python
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 启用 CORS
```

### 2. 处理 OPTIONS 预检请求

添加了对 OPTIONS 请求的处理：

```python
@app.route('/v1/messages', methods=['POST', 'OPTIONS'])
def messages():
    # 处理 OPTIONS 预检请求
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Api-Key')
        response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
        return response
```

### 3. 记录请求头

添加了请求头日志，方便调试：

```python
@app.before_request
def before_request():
    print(f"[{request.remote_addr}] {request.method} {request.path}")
    print(f"Headers: {dict(request.headers)}")
```

## 验证修复

### 测试 1：直接调用

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

**预期结果：** 返回 Anthropic 格式的响应

### 测试 2：检查日志

查看包装器运行日志，应该看到：

```
[127.0.0.1] POST /v1/messages
Headers: {...}
```

### 测试 3：OpenClaw 调用

在 OpenClaw Canvas 中使用 Agent 节点，应该不再出现 403 错误。

## 如果仍然出现 403

### 检查点 1：包装器是否运行

```bash
curl http://127.0.0.1:5002/health
```

如果返回 404，说明 `/health` 路由不存在，但 API 应该正常工作。

### 检查点 2：查看包装器日志

在运行包装器的终端查看日志，应该看到请求记录。

### 检查点 3：检查 OpenClaw 配置

确认环境变量已正确设置：

```powershell
echo $env:ANTHROPIC_BASE_URL
echo $env:ANTHROPIC_API_KEY
```

应该输出：
```
http://127.0.0.1:5002/v1
sk-fake-key-not-needed
```

### 检查点 4：重启 Gateway

如果修改了配置，需要重启 Gateway：

```bash
# 停止 Gateway (Ctrl+C)

# 重启
$env:ANTHROPIC_BASE_URL="http://127.0.0.1:5002/v1"
$env:ANTHROPIC_API_KEY="sk-fake-key-not-needed"
openclaw gateway
```

## 调试技巧

### 1. 启用详细日志

在包装器代码中添加：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 2. 测试不同端点

```bash
# 测试模型列表
curl http://127.0.0.1:5002/v1/models

# 测试单个模型
curl http://127.0.0.1:5002/v1/models/claude-3-opus-20240229
```

### 3. 检查网络连接

```bash
# 检查端口监听
netstat -ano | findstr :5002

# 测试连接
telnet 127.0.0.1 5002
```

## 常见错误

### 错误 1：Connection refused

**原因：** 包装器未运行

**解决：** 启动包装器
```bash
python deepseek_anthropic_wrapper.py
```

### 错误 2：404 Not Found

**原因：** 路由错误

**解决：** 检查 URL 是否正确
- 正确：`http://127.0.0.1:5002/v1/messages`
- 错误：`http://127.0.0.1:5002/messages`

### 错误 3：500 Internal Server Error

**原因：** DeepSeek API 调用失败

**解决：** 检查 DeepSeek API 密钥和网络连接

### 错误 4：504 Gateway Timeout

**原因：** 请求超时

**解决：** 增加超时时间或检查网络

## 完整重启流程

```bash
# 1. 停止所有服务
# 在各个终端按 Ctrl+C

# 2. 重启包装器
python deepseek_anthropic_wrapper.py

# 3. 重启 Gateway
$env:ANTHROPIC_BASE_URL="http://127.0.0.1:5002/v1"
$env:ANTHROPIC_API_KEY="sk-fake-key-not-needed"
openclaw gateway
```

## 联系支持

如果问题仍未解决，请提供：

1. 包装器日志
2. OpenClaw 日志
3. 错误截图
4. 测试命令和输出

---

**更新时间:** 2026-03-11 22:55  
**状态:** 已修复 CORS 和 OPTIONS 请求
