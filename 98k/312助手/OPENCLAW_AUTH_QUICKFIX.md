# OpenClaw 认证配置指南

## 问题说明

OpenClaw 报告错误：
```
未找到"anthropic"提供者的 API 密钥
```

这是因为 OpenClaw 默认使用 Anthropic Claude 模型，但没有配置认证。

## 解决方案

### 方案 1：使用 DeepSeek（推荐 - 已配置）

我们已经创建了 DeepSeek 的认证配置，可以直接使用。

**复制认证文件：**

```bash
# 复制 auth-profiles.json 到 OpenClaw 配置目录
copy "e:\FHD\新建文件夹 (4)\AI 助手\auth-profiles.json" "C:\Users\97088\.openclaw\agents\main\agent\auth-profiles.json"
```

**然后重启 Gateway：**
```bash
# 在 Gateway 终端按 Ctrl+C 停止
# 重新启动
openclaw gateway
```

### 方案 2：配置 Anthropic API 密钥

如果你有 Anthropic API 密钥：

1. **编辑认证文件：**
   ```
   C:\Users\97088\.openclaw\agents\main\agent\auth-profiles.json
   ```

2. **添加 Anthropic 配置：**
   ```json
   {
     "version": 1,
     "profiles": {
       "anthropic:manual": {
         "type": "token",
         "provider": "anthropic",
         "token": "sk-ant-api03-你的密钥"
       }
     }
   }
   ```

3. **重启 Gateway**

### 方案 3：使用命令行工具配置

```bash
# 为 DeepSeek 添加认证
openclaw agents add main --provider deepseek --token sk-5670fc1d73c74f21b4948d7496b7bf16

# 或者为 Anthropic 添加认证
openclaw agents add main --provider anthropic --token sk-ant-你的密钥
```

### 方案 4：使用环境变量（推荐用于生产）

**设置环境变量：**

```bash
# DeepSeek
set DEEPSEEK_API_KEY=sk-5670fc1d73c74f21b4948d7496b7bf16

# Anthropic
set ANTHROPIC_API_KEY=sk-ant-api03-你的密钥
```

然后重启 Gateway，OpenClaw 会自动从环境变量读取密钥。

## 快速解决（推荐）

**最简单的方法 - 直接复制文件：**

```bash
# 1. 停止 Gateway (Ctrl+C)

# 2. 复制认证文件
copy "e:\FHD\新建文件夹 (4)\AI 助手\auth-profiles.json" "C:\Users\97088\.openclaw\agents\main\agent\auth-profiles.json"

# 3. 重启 Gateway
openclaw gateway
```

## 验证配置

重启后，检查日志：
```
[gateway] agent model: deepseek/deepseek-chat
```

如果显示 DeepSeek 模型，说明配置成功！

## 使用 DeepSeek MCP Server

即使不配置 OpenClaw 的认证，你仍然可以通过 HTTP API 使用 DeepSeek：

### 在 Canvas 中使用 HTTP 请求

```json
{
  "url": "http://127.0.0.1:5001/chat",
  "method": "POST",
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "message": "{{user_input}}",
    "use_tools": true
  }
}
```

这种方式**不需要**配置 OpenClaw 的认证！

## 当前状态

### ✅ 已运行的服务

1. **OpenClaw Gateway**
   - WebSocket: `ws://127.0.0.1:18789`
   - Canvas: `http://127.0.0.1:18789/__openclaw__/canvas/`

2. **DeepSeek MCP Server**
   - HTTP: `http://127.0.0.1:5001`
   - 状态：✅ 正常运行

### ⚠️ 需要配置的项目

- **OpenClaw Agent 认证**
  - 状态：缺少 Anthropic 密钥
  - 解决：复制 auth-profiles.json 或配置环境变量

## 推荐方案

**最佳实践：使用 DeepSeek MCP Server + Canvas HTTP 请求**

优点：
- ✅ 不需要配置 OpenClaw 认证
- ✅ 直接使用 DeepSeek
- ✅ 支持工具调用
- ✅ 配置简单

步骤：
1. 在 Canvas 中添加 HTTP Request 节点
2. 配置 URL: `http://127.0.0.1:5001/chat`
3. 发送 POST 请求
4. 解析响应

详细说明见：`OPENCLAW_CANVAS_DIRECT_USE.md`

---

**创建时间:** 2026-03-11  
**状态:** 等待配置
