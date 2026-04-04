#!/bin/bash

# ============================================
# XCAGI 项目打包脚本 (Linux/Mac)
# 用途：在构建机（有源码）打包镜像和配置
# ============================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[信息]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[警告]${NC} $1"
}

print_error() {
    echo -e "${RED}[错误]${NC} $1"
}

echo ""
echo "╔════════════════════════════════════════╗"
echo "║     XCAGI 项目打包工具                  ║"
echo "║     生成离线部署包                       ║"
echo "╚════════════════════════════════════════╝"
echo ""

# 检查参数
if [ -z "$1" ]; then
    VERSION="latest"
else
    VERSION="$1"
fi

print_info "打包版本: $VERSION"
echo ""

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 创建 release-bundle 目录
RELEASE_DIR="release-bundle"
if [ -d "$RELEASE_DIR" ]; then
    print_warning "release-bundle 目录已存在，正在删除..."
    rm -rf "$RELEASE_DIR"
fi
mkdir -p "$RELEASE_DIR"
print_success "创建 release-bundle 目录"

# 1. 构建并导出镜像
echo ""
echo "════════════════════════════════════════"
print_info "第 1/5 步：构建并导出 Docker 镜像..."
echo "════════════════════════════════════════"
echo ""

# 构建所有镜像
print_info "构建 Docker 镜像..."
docker-compose build --no-cache
if [ $? -ne 0 ]; then
    print_error "镜像构建失败"
    exit 1
fi

# 导出镜像为 tar 文件
print_info "导出镜像为 tar 文件..."
docker save -o "$RELEASE_DIR/xcagi-redis.tar" redis:7-alpine
docker save -o "$RELEASE_DIR/xcagi-backend.tar" xcagi-backend:latest
docker save -o "$RELEASE_DIR/xcagi-frontend.tar" xcagi-frontend:latest
docker save -o "$RELEASE_DIR/xcagi-celery-worker.tar" xcagi-celery-worker:latest
if [ $? -ne 0 ]; then
    print_error "镜像导出失败"
    exit 1
fi
print_success "镜像导出完成"

# 2. 复制配置文件
echo ""
echo "════════════════════════════════════════"
print_info "第 2/5 步：复制配置文件..."
echo "════════════════════════════════════════"
echo ""

# 复制 docker-compose 配置
cp docker-compose.yml "$RELEASE_DIR/docker-compose.yml"
cp docker-compose.dev.yml "$RELEASE_DIR/docker-compose.dev.yml"

# 复制环境变量配置
cp .env.example "$RELEASE_DIR/.env.example"

# 创建发布版环境变量文件
print_info "创建 .release.env 配置..."
cat > "$RELEASE_DIR/.release.env" << EOF
# XCAGI 发布版本环境变量配置
# 请在部署前修改以下配置

SECRET_KEY=change-me-before-deployment-$VERSION
FLASK_ENV=production
LOG_LEVEL=INFO
EOF

# 复制前端 nginx 配置
if [ -f "frontend/nginx.conf" ]; then
    mkdir -p "$RELEASE_DIR/frontend"
    cp "frontend/nginx.conf" "$RELEASE_DIR/frontend/nginx.conf"
fi

# 复制后端配置
if [ -f "gunicorn_config.py" ]; then
    cp "gunicorn_config.py" "$RELEASE_DIR/gunicorn_config.py"
fi

print_success "配置文件复制完成"

# 3. 创建部署脚本
echo ""
echo "════════════════════════════════════════"
print_info "第 3/5 步：创建部署脚本..."
echo "════════════════════════════════════════"
echo ""

# 创建 Windows 部署脚本
cat > "$RELEASE_DIR/deploy-release.bat" << 'EOFBAT'
@echo off
chcp 65001 >nul

:: ============================================
:: XCAGI 项目离线部署脚本 (Windows)
:: ============================================

echo.
echo ╔════════════════════════════════════════╗
echo ║     XCAGI 项目离线部署工具              ║
echo ╚════════════════════════════════════════╝
echo.

:: 检查 Docker
docker --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 请先安装 Docker Desktop
    pause
    exit /b 1
)

:: 切换到脚本目录
cd /d "%~dp0"

:: 检查镜像文件
if not exist "xcagi-redis.tar" (
    echo [错误] 未找到 xcagi-redis.tar
    pause
    exit /b 1
)

:: 创建 .env 文件
if not exist ".env" (
    echo [提示] 创建 .env 文件...
    copy .release.env .env >nul
    echo [警告] 请编辑 .env 文件修改 SECRET_KEY
)

:: 导入镜像
echo 正在导入 Docker 镜像...
docker load -i xcagi-redis.tar
docker load -i xcagi-backend.tar
docker load -i xcagi-frontend.tar
docker load -i xcagi-celery-worker.tar

:: 启动服务
echo 正在启动服务...
docker-compose up -d

:: 等待服务启动
echo 等待服务启动...
timeout /t 15 /nobreak >nul

:: 检查状态
docker-compose ps

echo.
echo ════════════════════════════════════════
echo 部署完成!
echo ════════════════════════════════════════
echo.
echo 访问地址:
echo   前端：http://localhost
echo   后端：http://localhost:5000
echo.
echo 查看日志：docker-compose logs -f
echo 停止服务：docker-compose down
echo.
pause
EOFBAT

# 创建 Linux 部署脚本
cat > "$RELEASE_DIR/deploy-release.sh" << 'EOFSH'
#!/bin/bash

# ============================================
# XCAGI 项目离线部署脚本 (Linux/Mac)
# ============================================

set -e

echo ""
echo "╔════════════════════════════════════════╗"
echo "║     XCAGI 项目离线部署工具              ║"
echo "╚════════════════════════════════════════╝"
echo ""

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "[错误] 请先安装 Docker"
    exit 1
fi

# 切换到脚本目录
cd "$(dirname "$0")"

# 创建 .env 文件
if [ ! -f ".env" ]; then
    echo "[提示] 创建 .env 文件..."
    cp .release.env .env
    echo "[警告] 请编辑 .env 文件修改 SECRET_KEY"
fi

# 导入镜像
echo "正在导入 Docker 镜像..."
docker load -i xcagi-redis.tar
docker load -i xcagi-backend.tar
docker load -i xcagi-frontend.tar
docker load -i xcagi-celery-worker.tar

# 启动服务
echo "正在启动服务..."
docker-compose up -d

# 等待服务启动
echo "等待服务启动..."
sleep 15

# 检查状态
docker-compose ps

echo ""
echo "════════════════════════════════════════"
echo "部署完成!"
echo "════════════════════════════════════════"
echo ""
echo "访问地址:"
echo "  前端：http://localhost"
echo "  后端：http://localhost:5000"
echo ""
echo "查看日志：docker-compose logs -f"
echo "停止服务：docker-compose down"
echo ""
EOFSH

chmod +x "$RELEASE_DIR/deploy-release.sh"
print_success "部署脚本创建完成"

# 4. 创建使用说明
echo ""
echo "════════════════════════════════════════"
print_info "第 4/5 步：创建使用说明..."
echo "════════════════════════════════════════"
echo ""

cat > "$RELEASE_DIR/README.md" << 'EOFMD'
# XCAGI 离线部署包

## 打包信息
- 版本：VERSION_PLACEHOLDER
- 打包时间：DATE_PLACEHOLDER

## 文件清单

### 镜像文件
- xcagi-redis.tar - Redis 缓存服务
- xcagi-backend.tar - 后端 API 服务
- xcagi-frontend.tar - 前端 Web 服务
- xcagi-celery-worker.tar - Celery 异步任务

### 配置文件
- docker-compose.yml - Docker Compose 配置
- docker-compose.dev.yml - 开发环境配置
- .env.example - 环境变量示例
- .release.env - 发布版环境变量

### 脚本文件
- deploy-release.bat - Windows 部署脚本
- deploy-release.sh - Linux/Mac 部署脚本

## 部署步骤

### Windows
1. 解压本包到目标机器
2. 双击运行 deploy-release.bat
3. 等待部署完成
4. 访问 http://localhost

### Linux/Mac
1. 解压本包到目标机器
2. 赋予执行权限：chmod +x deploy-release.sh
3. 运行：./deploy-release.sh
4. 等待部署完成
5. 访问 http://localhost

## 首次部署

部署前请编辑 .env 文件：
- SECRET_KEY：修改为随机字符串
- LOG_LEVEL：根据需要修改（INFO/WARNING/DEBUG）

## 常用命令

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重启服务
docker-compose restart
```

## 访问地址

- 前端界面：http://localhost
- 后端 API：http://localhost:5000
- 健康检查：http://localhost:5000/health
- Redis：localhost:6379

## 注意事项

1. 目标机器需要安装 Docker Desktop (Windows) 或 Docker (Linux/Mac)
2. 确保 Docker 服务正在运行
3. 端口 80、5000、6379 不能被其他程序占用
4. 首次部署需要导入镜像，请耐心等待
5. 数据存储在 Docker 卷中，删除容器不会丢失数据
EOFMD

# 替换占位符
sed -i "s/VERSION_PLACEHOLDER/$VERSION/g" "$RELEASE_DIR/README.md"
sed -i "s/DATE_PLACEHOLDER/$(date '+%Y-%m-%d %H:%M:%S')/g" "$RELEASE_DIR/README.md"

print_success "使用说明创建完成"

# 5. 生成清单
echo ""
echo "════════════════════════════════════════"
print_info "第 5/5 步：生成打包清单..."
echo "════════════════════════════════════════"
echo ""

print_info "打包清单："
echo ""
ls -lh "$RELEASE_DIR"
echo ""
echo "总计："
echo "- 镜像文件：4 个"
echo "- 配置文件：5 个"
echo "- 部署脚本：2 个"
echo "- 文档：1 个"
echo ""

echo "════════════════════════════════════════"
print_success "打包完成!"
echo "════════════════════════════════════════"
echo ""
echo "release-bundle 目录已生成，包含所有部署所需文件。"
echo ""
echo "下一步："
echo "1. 将 release-bundle 目录拷贝到目标机器"
echo "2. 在目标机器运行 deploy-release.bat (Windows)"
echo "   或 ./deploy-release.sh (Linux/Mac)"
echo ""
echo "详细说明请查看：release-bundle/README.md"
echo ""
