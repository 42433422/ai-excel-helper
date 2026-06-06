# XCAGI 启动器更新总结

> **更新日期**: 2026-04-17  
> **目标**: 更新所有启动脚本以使用统一的 FastAPI 入口（端口 5000）

---

## 📋 更新的文件清单

### 1. 主要启动脚本

| 文件 | 变更内容 | 状态 |
|------|----------|------|
| `start-xcagi.bat` | 端口 8000 → 5000，更新提示信息 | ✅ 已更新 |
| `xcagi-backend-8000.cmd` | 端口 8000 → 5000，删除 compact 栈 | ✅ 已更新 |
| `xcagi-backend-with-db.cmd` | 更新注释说明 | ✅ 已更新 |
| `start-basic.bat` | 端口 8000 → 5000，删除 compact 栈引用 | ✅ 已更新 |
| `start-dev.bat` | 端口 8000 → 5000，更新输出信息 | ✅ 已更新 |

### 2. 前端配置

| 文件 | 变更内容 | 状态 |
|------|----------|------|
| `frontend/vite.config.ts` | 代理目标 8000 → 5000 | ✅ 已更新（之前已完成） |

---

## 🔧 详细变更内容

### 1. `start-xcagi.bat`

**变更**:
- 更新标题: 历史记录曾使用 `XCAGI v6.0`；**当前主线文档与安装标题为 v8.0**（FastAPI 唯一入口 + 可选 Electron 桌面壳 + 跨行业适配）。
- 添加 CHANGELOG 信息到启动画面
- 端口 8000 → 5000（健康检查、启动等待、摘要输出）
- 删除 `XCAGI_API_STACK=compact` 环境变量说明
- 更新摘要信息，添加迁移说明

**关键端口变更**:
```batch
# 旧
set "BACKEND_READY=0"
powershell ... 'http://127.0.0.1:8000/api/health' ...
echo [INFO] Backend is ready on http://127.0.0.1:8000

# 新
set "BACKEND_READY=0"
powershell ... 'http://127.0.0.1:5000/api/health' ...
echo [INFO] Backend is ready on http://127.0.0.1:5000
echo [INFO] API docs: http://127.0.0.1:5000/docs
```

---

### 2. `xcagi-backend-8000.cmd`

**变更**:
- 添加统一的 FastAPI 入口标题
- 删除 `stack_compact` 分支（backend.http_app 已删除）
- 端口 8000 → 5000
- 使用 `app.fastapi_main:app` 替代 `run_fastapi:app`
- 添加 `--reload` 参数便于开发
- 更新帮助信息

**关键变更**:
```batch
# 旧
echo [INFO] Starting FastAPI at http://127.0.0.1:8000
"%PY_EXE%" -m uvicorn run_fastapi:app --host 127.0.0.1 --port 8000

# 新
echo [INFO] Starting FastAPI at http://127.0.0.1:5000
echo [INFO] API docs: http://127.0.0.1:5000/docs
echo [INFO] Health: http://127.0.0.1:5000/api/health
"%PY_EXE%" -m uvicorn app.fastapi_main:app --host 127.0.0.1 --port 5000 --reload
```

---

### 3. `start-basic.bat`

**变更**:
- 端口 8000 → 5000
- 删除 `XCAGI_API_STACK=compact` 环境变量设置
- 添加迁移说明

---

### 4. `start-dev.bat`

**变更**:
- 端口 8000 → 5000
- 更新输出信息，添加 API 文档链接

---

### 5. `xcagi-backend-with-db.cmd`

**变更**:
- 更新注释说明，反映端口变更

---

## 🎯 现在的启动配置

### 后端
- **端口**: 5000
- **入口**: `XCAGI/app.fastapi_main:app`
- **健康检查**: `http://127.0.0.1:5000/api/health`
- **API 文档**: `http://127.0.0.1:5000/docs`

### 前端
- **开发服务器**: 5173 (Vite) / 5001 (npm run dev)
- **代理**: `/api` → `http://127.0.0.1:5000`
- **浏览器**: `http://127.0.0.1:5001`

---

## 🚀 使用方式

### 方式 1: 使用 start-xcagi.bat（推荐）

```batch
cd E:\FHD\XCAGI
start-xcagi.bat
```

### 方式 2: 使用根目录 run.py

```batch
cd E:\FHD
python run.py
```

### 方式 3: 直接启动

```batch
cd E:\FHD\XCAGI
python -m uvicorn app.fastapi_main:app --host 127.0.0.1 --port 5000
```

---

## 📊 端口变更对照

| 服务 | 旧端口 | 新端口 | 说明 |
|------|--------|--------|------|
| FastAPI 后端 | 8000 | **5000** | 统一入口 |
| Vite 前端 | 5173 | 5173 | 不变 |
| npm 前端 | 5001 | 5001 | 不变 |

---

## ⚠️ 注意事项

1. **端口 8000 已废弃**: backend.http_app 已删除，不要再使用 8000 端口
2. **Vite 代理已更新**: frontend/vite.config.ts 已指向 5000 端口
3. **Flask 已迁移**: 所有 Flask 路由已迁移到 FastAPI
4. **启动器已更新**: 所有 .bat 文件已更新为使用 5000 端口

---

## ✅ 验证启动器正常工作

启动后应该看到：

```
=============================================
  XCAGI Startup Script v5.0
  UPDATED: 2026-04-17 - Unified FastAPI Entry
=============================================
...
[Backend] Starting FastAPI on port 5000 (Unified Entry)...
...
[1] Backend:  http://127.0.0.1:5000  API docs: http://127.0.0.1:5000/docs
[2] Frontend: http://127.0.0.1:5001
```

---

**更新时间**: 2026-04-17  
**状态**: ✅ 所有启动器已更新完成
