# OpenClaw Gateway 认证配置指南

## 问题说明

OpenClaw Gateway 启动后显示：
```
unauthorized: gateway token missing (open the dashboard URL and paste the token in Control UI settings)
```

这是因为 OpenClaw 需要认证令牌才能连接 Control UI。

## 解决步骤

### 方法 1：通过 Dashboard 获取令牌（推荐）

1. **打开 OpenClaw Dashboard**
   - 在浏览器中访问：`http://127.0.0.1:18789`
   - 或者访问：`http://127.0.0.1:18789/__openclaw__/canvas/`

2. **查看令牌**
   - Dashboard 页面会显示一个认证令牌
   - 令牌格式类似：`oc-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

3. **在 Control UI 中配置令牌**
   - 打开 Control UI 设置
   - 找到 "Gateway Token" 或类似设置项
   - 粘贴获取到的令牌
   - 保存设置

4. **验证连接**
   - 配置完成后，状态应该从"离线"变为"在线"
   - 健康状况显示应为"正常"

### 方法 2：禁用认证（仅限本地开发）

如果只是在本地开发测试，可以临时禁用认证：

1. **停止当前 Gateway**
   ```bash
   # 在终端按 Ctrl+C
   ```

2. **重新启动 Gateway（无认证模式）**
   ```bash
   openclaw gateway --no-auth
   ```
   
   或者设置环境变量：
   ```bash
   set OPENCLAW_NO_AUTH=true
   openclaw gateway
   ```

3. **验证**
   - 重新启动后应该不再需要令牌
   - Control UI 可以直接连接

### 方法 3：查看配置文件

OpenClaw 的配置文件通常位于：
```
C:\Users\97088\.openclaw\config.json
```

编辑配置文件，添加或修改：
```json
{
  "gateway": {
    "token": "your-token-here",
    "url": "ws://127.0.0.1:18789"
  }
}
```

## 当前状态

### ✅ 已运行的服务

1. **OpenClaw Gateway**
   - 状态：运行中
   - WebSocket: `ws://127.0.0.1:18789`
   - Canvas: `http://127.0.0.1:18789/__openclaw__/canvas/`
   - PID: 40232

2. **DeepSeek MCP Server**
   - 状态：运行中 ✅
   - HTTP: `http://127.0.0.1:5001`
   - 健康检查：正常响应

### ⚠️ 需要配置的项目

- **OpenClaw Control UI 认证令牌**
  - 状态：缺少令牌
  - 影响：无法连接 Gateway
  - 解决：按上述步骤配置令牌

## 测试连接

配置令牌后，可以测试连接：

```bash
# 测试 Gateway WebSocket 连接
# 在浏览器控制台或 Node.js 中运行
const ws = new WebSocket('ws://127.0.0.1:18789');
ws.onopen = () => console.log('✅ Connected!');
ws.onerror = (err) => console.log('❌ Error:', err);
```

## DeepSeek 集成测试

配置完成后，测试 DeepSeek 集成：

```bash
# 测试 DeepSeek MCP Server
curl http://127.0.0.1:5001/health

# 测试对话接口
curl -X POST http://127.0.0.1:5001/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"message\": \"你好\", \"use_tools\": false}"
```

## 故障排查

### 问题 1：Dashboard 无法访问

**症状**: 访问 `http://127.0.0.1:18789` 显示无法连接

**解决**:
1. 确认 Gateway 正在运行
2. 检查端口是否被占用：`netstat -ano | findstr :18789`
3. 重启 Gateway

### 问题 2：令牌配置后仍然离线

**症状**: 配置了令牌但状态仍显示"离线"

**解决**:
1. 检查令牌是否正确复制（没有多余空格）
2. 刷新 Control UI 页面
3. 重启 Control UI
4. 检查 Gateway 日志是否有新的错误

### 问题 3：DeepSeek 无法调用

**症状**: OpenClaw 中调用 DeepSeek 失败

**解决**:
1. 确认 DeepSeek MCP Server 正在运行
2. 测试健康检查：`curl http://127.0.0.1:5001/health`
3. 检查 OpenClaw 中的 HTTP 请求配置
4. 确认 CORS 设置（如果需要）

## 下一步

1. ✅ 启动 OpenClaw Gateway
2. ✅ 启动 DeepSeek MCP Server
3. ⏳ 配置认证令牌
4. ⏳ 测试 DeepSeek 集成
5. ⏳ 在 OpenClaw 中使用 DeepSeek 功能

---

**创建时间**: 2026-03-11  
**状态**: 等待令牌配置
