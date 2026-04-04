# XCAGI 项目部署指南

本文档提供详细的部署说明，涵盖 Docker 部署、本地部署以及各种实用脚本的使用方法。

## 📋 目录

- [快速开始](#快速开始)
- [Docker 部署](#docker-部署)
- [本地部署](#本地部署)
- [部署脚本说明](#部署脚本说明)
- [常见问题](#常见问题)

---

## 🚀 快速开始

### Windows 用户

1. **最简单方式**：双击 `quick-start.bat`
2. **交互式部署**：运行 `deploy.bat`
3. 访问 http://localhost

### Linux/Mac 用户

```bash
# 赋予执行权限
chmod +x deploy.sh

# 运行部署脚本
./deploy.sh
```

---

## 🐳 Docker 部署

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ 可用内存
- 10GB+ 磁盘空间

### 部署步骤

#### 1. 准备环境变量

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

编辑 `.env` 文件，设置 `SECRET_KEY`：

```bash
SECRET_KEY=your-secret-key-here
LOG_LEVEL=INFO
```

#### 2. 生产环境部署

```bash
# 构建并启动
docker-compose up -d --build

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

#### 2.1 源码保护部署（推荐给交付客户机器）

如果希望目标机器**不持有项目源码**，使用发布包流程：

```bash
# 在构建机（有源码）执行，打包镜像
# Windows
package-release.bat v1

# Linux/Mac
./package-release.sh v1
```

打包后会生成 `release-bundle/`，其中包含：
- `docker-compose.yml`（发布版，仅拉起镜像）
- `xcagi-images-<tag>.tar`（离线镜像包）
- `.env.example`、`.release.env`
- `deploy-release.bat` / `deploy-release.sh`

在目标机器（无源码）执行：

```bash
# Windows
deploy-release.bat

# Linux/Mac
./deploy-release.sh
```

> 注意：目标机首次部署前请先编辑 `.env`，至少修改 `SECRET_KEY`。

#### 3. 开发环境部署

```bash
# 使用开发配置
docker-compose -f docker-compose.dev.yml up -d --build
```

**开发环境特点**：
- 代码热重载
- Flask 调试模式
- 详细日志输出

### 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| 前端 | 80 | Nginx 静态服务器 |
| 后端 | 5000 | Flask API |
| Redis | 6379 | 缓存/消息队列 |

### 常用命令

```bash
# 查看服务状态
docker-compose ps

# 停止所有服务
docker-compose down

# 重启服务
docker-compose restart

# 进入后端容器
docker exec -it xcagi-backend bash

# 查看实时日志
docker-compose logs -f backend

# 重新构建镜像
docker-compose build --no-cache

# 清理所有数据（谨慎！）
docker-compose down -v
```

---

## 💻 本地部署（无 Docker）

### Windows

#### 1. 安装 Python 3.11

下载：https://www.python.org/downloads/

#### 2. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

#### 3. 安装 Node.js（前端）

下载：https://nodejs.org/

```bash
cd frontend
npm install
npm run build
```

#### 4. 安装 Redis

下载：https://github.com/microsoftarchive/redis/releases

#### 5. 启动服务

```bash
# 启动后端
python run.py

# 启动 Celery Worker
celery -A celery_app worker --loglevel=info

# 启动前端（开发模式）
cd frontend
npm run dev
```

### Linux/Mac

```bash
# 安装依赖
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 安装 Redis
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# 启动 Redis
redis-server

# 启动后端
python run.py

# 启动 Celery
celery -A celery_app worker --loglevel=info
```

---

## 📜 部署脚本说明

### Windows 脚本

| 脚本文件 | 功能 | 说明 |
|----------|------|------|
| `quick-start.bat` | 一键启动 | 最简单的启动方式 |
| `deploy.bat` | 交互式部署 | 提供多种部署选项 |
| `stop.bat` | 停止服务 | 安全停止所有容器 |
| `restart.bat` | 重启服务 | 快速重启 |
| `logs.bat` | 查看日志 | 实时日志查看器 |

### Linux 脚本

| 脚本文件 | 功能 |
|----------|------|
| `deploy.sh` | 交互式部署脚本 |

### 使用示例

#### Windows - 交互式部署

```cmd
deploy.bat
```

选择 `1` 进行生产环境部署。

#### Linux - 交互式部署

```bash
chmod +x deploy.sh
./deploy.sh
```

---

## ❓ 常见问题

### 1. Docker 启动失败

**问题**：`Cannot start service`

**解决**：
```bash
# 检查 Docker 是否运行
docker ps

# 重启 Docker 服务
# Windows: 重启 Docker Desktop
# Linux: sudo systemctl restart docker
```

### 2. 端口被占用

**问题**：`Bind for 0.0.0.0:5000 failed: port is already allocated`

**解决**：
```bash
# 查找占用端口的进程
# Windows
netstat -ano | findstr :5000

# Linux/Mac
lsof -i :5000

# 停止占用进程或修改 docker-compose.yml 端口映射
```

### 3. 数据库文件丢失

**问题**：重启后数据丢失

**解决**：
确保 Docker 卷正确挂载：
```bash
docker volume ls
docker volume inspect xcagi-data
```

### 4. Redis 连接失败

**问题**：`Connection refused to redis:6379`

**解决**：
```bash
# 检查 Redis 容器状态
docker-compose ps redis

# 重启 Redis
docker-compose restart redis
```

### 5. 前端页面空白

**问题**：访问 http://localhost 显示空白

**解决**：
```bash
# 检查前端容器日志
docker-compose logs frontend

# 重新构建前端
docker-compose build frontend
docker-compose up -d frontend
```

### 6. 内存不足

**问题**：容器频繁重启

**解决**：
在 `docker-compose.yml` 中添加资源限制：
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

---

## 🔧 高级配置

### 修改服务端口

编辑 `docker-compose.yml`：

```yaml
services:
  backend:
    ports:
      - "8080:5000"  # 改为 8080
  frontend:
    ports:
      - "8081:80"    # 改为 8081
```

### 启用 HTTPS

1. 获取 SSL 证书
2. 配置 Nginx（参考 `frontend/nginx.conf`）
3. 在 Docker Compose 中挂载证书

### 日志轮转

编辑 `docker-compose.yml`：

```yaml
services:
  backend:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## 📞 技术支持

如遇到其他问题，请：

1. 查看日志：`docker-compose logs -f`
2. 检查容器状态：`docker-compose ps`
3. 验证健康状态：`curl http://localhost:5000/health`

---

**最后更新**: 2026-03-25
**版本**: 1.0
