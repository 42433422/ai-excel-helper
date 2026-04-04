#!/bin/bash

# ============================================
# XCAGI 项目一键部署脚本 (Linux/Mac)
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

# 显示标题
echo ""
echo "╔════════════════════════════════════════╗"
echo "║     XCAGI 项目 Docker 一键部署工具      ║"
echo "╚════════════════════════════════════════╝"
echo ""

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    print_error "未检测到 Docker，请先安装 Docker"
    echo "下载地址：https://docs.docker.com/get-docker/"
    exit 1
fi
print_success "Docker 已安装：$(docker --version)"

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null; then
    print_error "未检测到 Docker Compose"
    exit 1
fi
print_success "Docker Compose 已安装：$(docker-compose --version)"

# 切换到脚本所在目录
cd "$(dirname "$0")"

# 检查 .env 文件是否存在
if [ ! -f ".env" ]; then
    print_info "未找到 .env 文件，正在从 .env.example 创建..."
    cp .env.example .env
    if [ $? -ne 0 ]; then
        print_error "创建 .env 文件失败"
        exit 1
    fi
    print_success ".env 文件已创建"
    print_warning "请编辑 .env 文件设置 SECRET_KEY 等环境变量"
    echo ""
fi

# 显示菜单
echo "请选择部署模式:"
echo ""
echo "1) 生产环境部署 (推荐)"
echo "2) 开发环境部署"
echo "3) 仅启动已构建的服务"
echo "4) 停止所有服务"
echo "5) 清理所有数据 (谨慎使用!)"
echo "6) 查看服务状态"
echo "7) 查看实时日志"
echo "8) 重新构建镜像"
echo "9) 退出"
echo ""
read -p "请输入选项 (1-9): " choice

case $choice in
    1)
        echo ""
        echo "════════════════════════════════════════"
        echo "正在部署生产环境..."
        echo "════════════════════════════════════════"
        echo ""
        
        # 停止现有服务
        print_info "停止现有服务..."
        docker-compose down > /dev/null 2>&1 || true
        
        # 构建镜像
        print_info "构建 Docker 镜像..."
        docker-compose build --no-cache
        if [ $? -ne 0 ]; then
            print_error "镜像构建失败"
            exit 1
        fi
        
        # 启动服务
        print_info "启动所有服务..."
        docker-compose up -d
        if [ $? -ne 0 ]; then
            print_error "服务启动失败"
            exit 1
        fi
        
        # 等待服务启动
        print_info "等待服务启动..."
        sleep 10
        
        # 检查服务状态
        echo ""
        docker-compose ps
        echo ""
        
        # 健康检查
        print_info "正在检查后端服务..."
        for i in {1..5}; do
            if curl -s http://localhost:5000/health > /dev/null 2>&1; then
                print_success "后端服务健康检查通过"
                health_ok=true
                break
            fi
            print_info "等待后端服务启动 (尝试 $i/5)..."
            sleep 3
        done
        
        if [ "$health_ok" = true ]; then
            print_success "所有服务启动成功!"
        else
            print_warning "后端服务健康检查未通过，请查看日志"
        fi
        
        echo ""
        echo "════════════════════════════════════════"
        print_success "部署完成!"
        echo "════════════════════════════════════════"
        echo ""
        echo "访问地址:"
        echo "  前端：http://localhost"
        echo "  后端 API: http://localhost:5000"
        echo "  Redis: localhost:6379"
        echo ""
        echo "查看日志：docker-compose logs -f"
        echo "停止服务：docker-compose down"
        echo ""
        ;;
        
    2)
        echo ""
        echo "════════════════════════════════════════"
        echo "正在部署开发环境..."
        echo "════════════════════════════════════════"
        echo ""
        
        # 停止现有服务
        print_info "停止现有服务..."
        docker-compose -f docker-compose.dev.yml down > /dev/null 2>&1 || true
        
        # 构建并启动
        print_info "构建并启动开发环境..."
        docker-compose -f docker-compose.dev.yml up -d --build
        if [ $? -ne 0 ]; then
            print_error "开发环境启动失败"
            exit 1
        fi
        
        # 等待服务启动
        print_info "等待服务启动..."
        sleep 8
        
        # 检查服务状态
        echo ""
        docker-compose -f docker-compose.dev.yml ps
        echo ""
        
        print_success "开发环境部署完成!"
        echo ""
        echo "访问地址:"
        echo "  后端 API: http://localhost:5000"
        echo "  Redis: localhost:6379"
        echo ""
        echo "开发模式特点:"
        echo "  - 代码修改即时生效"
        echo "  - 启用 Flask 调试模式"
        echo "  - 详细日志输出"
        echo ""
        ;;
        
    3)
        echo ""
        echo "════════════════════════════════════════"
        echo "正在启动已构建的服务..."
        echo "════════════════════════════════════════"
        echo ""
        
        docker-compose start
        if [ $? -ne 0 ]; then
            print_error "服务启动失败，可能需要重新构建"
            exit 1
        fi
        
        print_success "服务启动成功!"
        docker-compose ps
        echo ""
        ;;
        
    4)
        echo ""
        echo "════════════════════════════════════════"
        echo "正在停止所有服务..."
        echo "════════════════════════════════════════"
        echo ""
        
        docker-compose down
        echo ""
        print_success "所有服务已停止"
        echo ""
        ;;
        
    5)
        echo ""
        echo "════════════════════════════════════════"
        print_warning "警告：此操作将删除所有数据!"
        echo "════════════════════════════════════════"
        echo ""
        read -p "确定要删除所有容器、镜像和数据卷吗？(y/N): " confirm
        if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
            print_info "操作已取消"
            exit 0
        fi
        
        echo ""
        print_info "正在清理..."
        docker-compose down -v
        docker system prune -f
        echo ""
        print_success "清理完成"
        echo ""
        ;;
        
    6)
        echo ""
        echo "════════════════════════════════════════"
        echo "服务状态:"
        echo "════════════════════════════════════════"
        echo ""
        docker-compose ps
        echo ""
        echo "磁盘使用情况:"
        docker system df
        echo ""
        ;;
        
    7)
        echo ""
        echo "════════════════════════════════════════"
        echo "正在查看实时日志..."
        echo "════════════════════════════════════════"
        echo ""
        print_info "按 Ctrl+C 停止查看"
        echo ""
        docker-compose logs -f
        ;;
        
    8)
        echo ""
        echo "════════════════════════════════════════"
        echo "正在重新构建镜像..."
        echo "════════════════════════════════════════"
        echo ""
        
        docker-compose build --no-cache
        if [ $? -ne 0 ]; then
            print_error "镜像构建失败"
            exit 1
        fi
        
        print_success "镜像构建完成!"
        echo ""
        ;;
        
    9)
        print_info "退出部署工具"
        exit 0
        ;;
        
    *)
        echo ""
        print_error "无效的选项，请重新运行脚本"
        echo ""
        exit 1
        ;;
esac

echo "感谢使用 XCAGI 一键部署工具!"
echo ""
