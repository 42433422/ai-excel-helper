# XCAGI 部署指南

> 开发环境和生产环境完整部署教程  
> 版本：3.0.0

---

## 📋 目录

1. [环境要求](#环境要求)
2. [开发环境部署](#开发环境部署)
3. [生产环境部署](#生产环境部署)
4. [Docker 部署](#docker-部署)
5. [Kubernetes 部署](#kubernetes-部署)
6. [云部署](#云部署)
7. [配置优化](#配置优化)
8. [性能调优](#性能调优)
9. [监控和日志](#监控和日志)
10. [故障排查](#故障排查)

---

## 环境要求

### 基础要求

| 组件 | 版本 | 必需 | 说明 |
|------|------|------|------|
| **操作系统** | Windows 10/11 | ✅ | 主要支持平台 |
| **Python** | 3.11+ | ✅ | 后端运行环境 |
| **Node.js** | 18.0+ | ⚠️ | 前端开发（可选） |
| **Redis** | 5.0+ | ⚠️ | 缓存和任务队列（推荐） |
| **Git** | 最新 | ✅ | 版本控制 |

### 可选组件

| 组件 | 用途 | 说明 |
|------|------|------|
| **TSC 打印机** | 标签打印 | 支持 TSC 系列打印机 |
| **Microsoft Excel** | Excel 自动化 | 高级 Excel 处理功能 |
| **Tesseract OCR** | 文字识别 | 离线 OCR 功能 |

### 硬件要求

| 配置 | 最低要求 | 推荐配置 |
|------|----------|----------|
| **CPU** | 双核 2.0GHz | 四核 3.0GHz+ |
| **内存** | 4GB | 8GB+ |
| **硬盘** | 10GB | 50GB+ SSD |
| **网络** | 1Mbps | 10Mbps+ |

---

## 开发环境部署

### 步骤 1: 克隆仓库

```bash
# 克隆仓库
git clone https://github.com/42433422/xcagi.git

# 进入项目目录
cd xcagi
```

### 步骤 2: 创建虚拟环境

```bash
# 创建 Python 虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

### 步骤 3: 安装后端依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 验证安装
pip list
```

### 步骤 4: 安装前端依赖（可选）

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 返回根目录
cd ..
```

### 步骤 5: 配置环境变量

```bash
# 复制环境变量示例文件
cp resources/config/.env.example .env

# 编辑 .env 文件
# Windows: 使用记事本或 VS Code
# Linux/macOS: 使用 vim 或 nano
```

**开发环境配置示例**:

```env
# 基础配置
FLASK_ENV=development
DEBUG=True
SECRET_KEY=your-dev-secret-key-here

# 数据库配置
DATABASE_URL=sqlite:///products.db
CUSTOMERS_DB_URL=sqlite:///customers.db
USERS_DB_URL=sqlite:///users.db

# Redis 配置（可选）
REDIS_URL=redis://localhost:6379/0

# AI 服务配置
DEEPSEEK_API_KEY=your-api-key-here
USE_LOCAL_BERT=True

# TTS 配置
TTS_VOICE=zh-CN-XiaoxiaoNeural
TTS_RATE=1.0
TTS_PITCH=1.0

# 文件上传配置
MAX_CONTENT_LENGTH=16777216
UPLOAD_FOLDER=temp_excel

# 日志配置
LOG_LEVEL=DEBUG
LOG_FILE=app.log
```

### 步骤 6: 初始化数据库

```bash
# 运行数据库迁移
alembic upgrade head

# 或者使用初始化脚本
python app/db/init_db.py

# 验证数据库
python check_app_db.py
```

### 步骤 7: 启动 Redis（可选但推荐）

```bash
# Windows: 下载并运行 redis-server.exe
# Linux/macOS
redis-server

# 验证 Redis
redis-cli ping
# 应该返回：PONG
```

### 步骤 8: 启动开发服务器

#### 方式 1: 快速启动（单体模式）

```bash
# 启动 Flask 服务
python run.py

# 访问：http://localhost:5000
```

#### 方式 2: 前后端分离模式

```bash
# 终端 1: 启动后端
python run.py

# 终端 2: 启动前端开发服务器
cd frontend
npm run dev

# 访问：http://localhost:5173（Vite 开发服务器）
```

#### 方式 3: 完整模式（包含 Celery）

```bash
# 终端 1: 启动后端
python run.py

# 终端 2: 启动 Celery Worker
celery -A celery_app worker --loglevel=debug

# 终端 3: 启动 Celery Beat（定时任务）
celery -A celery_app beat --loglevel=info
```

### 步骤 9: 验证安装

访问以下地址验证：

- **主界面**: http://localhost:5000
- **API 文档**: http://localhost:5000/apidocs
- **健康检查**: http://localhost:5000/api/health

### 步骤 10: 运行测试

```bash
# 后端测试
pytest -v

# 前端测试
cd frontend
npm test

# 端到端测试（可选）
npm run test:e2e
```

---

## 生产环境部署

### 前置准备

1. **域名和 SSL 证书**
   - 购买域名
   - 申请 SSL 证书（Let's Encrypt 免费）

2. **服务器**
   - Windows Server 2019/2022 或 Linux
   - 建议 4 核 CPU，8GB 内存，50GB SSD

3. **反向代理**
   - Nginx（推荐）或 Apache

### 步骤 1: 安装系统依赖

```bash
# Linux (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv redis-server nginx

# Windows Server
# 下载并安装 Python 3.11
# 下载并安装 Redis for Windows
```

### 步骤 2: 部署代码

```bash
# 克隆仓库
git clone https://github.com/42433422/xcagi.git /opt/xcagi
cd /opt/xcagi

# 创建虚拟环境
python3.11 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 步骤 3: 配置环境变量

```bash
# 创建生产环境配置
cat > .env << EOF
FLASK_ENV=production
DEBUG=False
SECRET_KEY=your-production-secret-key-here

DATABASE_URL=sqlite:///products.db
REDIS_URL=redis://localhost:6379/0

DEEPSEEK_API_KEY=your-api-key-here
USE_LOCAL_BERT=True

LOG_LEVEL=INFO
LOG_FILE=/var/log/xcagi/app.log
EOF
```

### 步骤 4: 初始化数据库

```bash
# 运行数据库迁移
alembic upgrade head

# 创建日志目录
sudo mkdir -p /var/log/xcagi
sudo chown -R $USER:$USER /var/log/xcagi
```

### 步骤 5: 配置 Gunicorn（Linux）或 Gevent（Windows）

**Gunicorn 配置** (`gunicorn_config.py`):

```python
import multiprocessing

bind = "127.0.0.1:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gevent"
worker_connections = 1000
timeout = 120
keepalive = 5
accesslog = "/var/log/xcagi/access.log"
errorlog = "/var/log/xcagi/error.log"
loglevel = "info"
```

### 步骤 6: 配置 Nginx

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 重定向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 静态文件
    location /static {
        alias /opt/xcagi/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 前端构建文件
    location / {
        root /opt/xcagi/templates/vue-dist;
        try_files $uri $uri/ /index.html;
    }

    # 反向代理到 Flask
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 120;
        proxy_read_timeout 120;
    }

    # 日志
    access_log /var/log/xcagi/nginx_access.log;
    error_log /var/log/xcagi/nginx_error.log;
}
```

### 步骤 7: 配置 Systemd 服务（Linux）

```ini
# /etc/systemd/system/xcagi.service
[Unit]
Description=XCAGI AI Excel Helper
After=network.target redis.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/xcagi
Environment="PATH=/opt/xcagi/venv/bin"
ExecStart=/opt/xcagi/venv/bin/gunicorn --config gunicorn_config.py run:app

Restart=on-failure
RestartSec=10s

# 安全设置
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

```bash
# 启用并启动服务
sudo systemctl daemon-reload
sudo systemctl enable xcagi
sudo systemctl start xcagi

# 查看状态
sudo systemctl status xcagi
```

### 步骤 8: 配置 Celery Worker

```ini
# /etc/systemd/system/xcagi-worker.service
[Unit]
Description=XCAGI Celery Worker
After=network.target redis.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/xcagi
Environment="PATH=/opt/xcagi/venv/bin"
ExecStart=/opt/xcagi/venv/bin/celery -A celery_app worker --loglevel=info

Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

```bash
# 启用并启动 Worker
sudo systemctl enable xcagi-worker
sudo systemctl start xcagi-worker
```

### 步骤 9: 配置防火墙

```bash
# 允许 HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 启用防火墙
sudo ufw enable

# 查看状态
sudo ufw status
```

### 步骤 10: 验证部署

```bash
# 检查服务状态
sudo systemctl status xcagi
sudo systemctl status xcagi-worker

# 检查 Nginx
sudo systemctl status nginx

# 测试访问
curl -I https://your-domain.com
curl -I https://your-domain.com/api/health
```

---

## Docker 部署

### 步骤 1: 创建 Dockerfile

**后端 Dockerfile**:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    redis-tools \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 5000

# 环境变量
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# 启动命令
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "run:app"]
```

**前端 Dockerfile**:

```dockerfile
FROM node:18-alpine as builder

WORKDIR /app

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# 生产镜像
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### 步骤 2: 创建 docker-compose.yml

```yaml
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: always

  backend:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "5000:5000"
    environment:
      - DATABASE_URL=sqlite:///app/products.db
      - REDIS_URL=redis://redis:6379/0
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
    volumes:
      - ./data:/app/data
      - ./temp_excel:/app/temp_excel
    depends_on:
      - redis
    restart: always

  worker:
    build:
      context: .
      dockerfile: Dockerfile
    command: celery -A celery_app worker --loglevel=info
    environment:
      - DATABASE_URL=sqlite:///app/products.db
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./data:/app/data
      - ./temp_excel:/app/temp_excel
    depends_on:
      - redis
    restart: always

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: always

volumes:
  redis_data:
```

### 步骤 3: 构建和运行

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

---

## Kubernetes 部署

### 步骤 1: 创建 Kubernetes 配置

参考项目中的 `k8s/` 目录：

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: xcagi-backend
  labels:
    app: xcagi
spec:
  replicas: 3
  selector:
    matchLabels:
      app: xcagi
  template:
    metadata:
      labels:
        app: xcagi
    spec:
      containers:
      - name: backend
        image: your-registry/xcagi:3.0.0
        ports:
        - containerPort: 5000
        env:
        - name: DATABASE_URL
          value: "sqlite:///app/products.db"
        - name: REDIS_URL
          value: "redis://redis:6379/0"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /api/health
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 5
```

### 步骤 2: 部署到 Kubernetes

```bash
# 创建命名空间
kubectl create namespace xcagi

# 部署应用
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/ingress.yaml

# 查看状态
kubectl get pods -n xcagi
kubectl get services -n xcagi
kubectl get ingress -n xcagi
```

---

## 配置优化

### 数据库优化

```python
# SQLite 优化配置
engine = create_engine(
    "sqlite:///products.db",
    connect_args={
        "pragma": [
            ("journal_mode", "WAL"),
            ("synchronous", "NORMAL"),
            ("cache_size", "-64000"),
            ("foreign_keys", "ON"),
        ]
    }
)
```

### 缓存配置

```python
from flask_caching import Cache

cache = Cache(config={
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': 'redis://localhost:6379/0',
    'CACHE_DEFAULT_TIMEOUT': 300
})
```

### 日志配置

```python
import logging
from logging.handlers import RotatingFileHandler

# 配置日志轮转
handler = RotatingFileHandler(
    'app.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=10
)
handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s'
))
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)
```

---

## 性能调优

### 1. Gunicorn 优化

```python
# 根据服务器配置调整
workers = 4  # CPU 核心数 * 2 + 1
worker_class = "gevent"
worker_connections = 1000
threads = 2
```

### 2. 数据库查询优化

```python
# 使用 joinedload 避免 N+1 查询
from sqlalchemy.orm import joinedload

products = db.query(Product).options(
    joinedload(Product.category)
).all()
```

### 3. 前端构建优化

```javascript
// vite.config.js
export default {
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vue-vendor': ['vue', 'vue-router', 'pinia'],
        },
      },
    },
    chunkSizeWarningLimit: 1000,
  },
}
```

---

## 监控和日志

### 1. 应用监控

使用 Prometheus + Grafana:

```yaml
# docker-compose.monitoring.yml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./k8s/monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana

  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"

  promtail:
    image: grafana/promtail:latest
    volumes:
      - /var/log:/var/log
    command: -config.file=/etc/promtail/config.yml
```

### 2. 日志收集

```python
# 结构化日志
import json
from pythonjsonlogger import jsonlogger

logger = logging.getLogger()
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)
```

---

## 故障排查

### 常见问题

#### 1. 服务无法启动

```bash
# 检查端口占用
netstat -ano | findstr :5000

# 查看日志
tail -f /var/log/xcagi/error.log

# 检查权限
ls -la /var/log/xcagi
```

#### 2. 数据库连接失败

```bash
# 检查数据库文件
ls -la *.db

# 检查 WAL 文件
ls -la *.db-wal *.db-shm

# 运行 WAL 检查点
sqlite3 products.db "PRAGMA wal_checkpoint(TRUNCATE);"
```

#### 3. Redis 连接失败

```bash
# 检查 Redis 状态
sudo systemctl status redis

# 测试连接
redis-cli ping

# 查看 Redis 日志
tail -f /var/log/redis/redis.log
```

#### 4. Celery Worker 不工作

```bash
# 检查 Worker 状态
sudo systemctl status xcagi-worker

# 查看 Worker 日志
journalctl -u xcagi-worker -f

# 测试任务
celery -A celery_app inspect ping
```

---

## 备份和恢复

### 数据库备份

```bash
# 备份脚本
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/xcagi"

# 备份数据库
cp products.db "$BACKUP_DIR/products.db.$DATE"
cp customers.db "$BACKUP_DIR/customers.db.$DATE"
cp users.db "$BACKUP_DIR/users.db.$DATE"

# 压缩备份
tar -czf "$BACKUP_DIR/xcagi_backup_$DATE.tar.gz" \
    products.db.$DATE customers.db.$DATE users.db.$DATE

# 清理旧备份（保留 7 天）
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

### 恢复数据库

```bash
# 停止服务
sudo systemctl stop xcagi

# 恢复数据库
tar -xzf xcagi_backup_20260323_120000.tar.gz
cp products.db.20260323_120000 products.db

# 启动服务
sudo systemctl start xcagi
```

---

## 安全加固

### 1. 防火墙配置

```bash
# 只开放必要端口
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### 2. SSL/TLS 配置

```bash
# 使用 Let's Encrypt
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo crontab -e
# 添加：0 3 * * * certbot renew --quiet
```

### 3. 数据库加密

```python
# 使用 SQLCipher 加密 SQLite
from sqlalchemy import create_engine

engine = create_engine(
    "sqlite:///products.db",
    connect_args={
        "pragma": [
            ("key", "your-encryption-key"),
            ("cipher", "aes-256-cbc"),
        ]
    }
)
```

---

## 总结

本部署指南涵盖了从开发环境到生产环境的完整部署流程。根据您的具体需求选择合适的部署方式：

- **开发环境**: 快速启动，前后端分离
- **生产环境**: Gunicorn + Nginx + Systemd
- **容器化**: Docker Compose（推荐中小型项目）
- **云原生**: Kubernetes（推荐大型项目）

如有问题，请查阅：
- [快速开始指南](QUICK_START.md)
- [架构设计文档](ARCHITECTURE.md)
- [GitHub Issues](https://github.com/42433422/xcagi/issues)

---

*最后更新：2026-03-23*
