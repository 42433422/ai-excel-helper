@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ============================================
:: XCAGI 项目一键部署脚本 (Windows)
:: ============================================

echo.
echo ╔════════════════════════════════════════╗
echo ║     XCAGI 项目 Docker 一键部署工具      ║
echo ╚════════════════════════════════════════╝
echo.

:: 检查 Docker 是否安装
docker --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Docker，请先安装 Docker Desktop
    echo 下载地址：https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

echo [✓] Docker 已安装

:: 检查 Docker Compose 是否安装
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Docker Compose
    pause
    exit /b 1
)

echo [✓] Docker Compose 已安装

:: 检查 docker-compose.yml 是否存在
if not exist "docker-compose.yml" (
    echo [错误] 未找到 docker-compose.yml 文件
    echo 请确保在正确的项目目录运行此脚本
    pause
    exit /b 1
)

echo [✓] Docker Compose 配置文件已找到
echo.

:: 切换到脚本所在目录
cd /d "%~dp0"

:: 检查 .env 文件是否存在
if not exist ".env" (
    echo [提示] 未找到 .env 文件，正在从 .env.example 创建...
    copy .env.example .env >nul
    if errorlevel 1 (
        echo [错误] 创建 .env 文件失败
        pause
        exit /b 1
    )
    echo [✓] .env 文件已创建，请编辑该文件设置 SECRET_KEY 等环境变量
    echo.
)

:: 显示菜单
echo 请选择部署模式:
echo.
echo 1) 生产环境部署 (推荐)
echo 2) 开发环境部署
echo 3) 仅启动已构建的服务
echo 4) 停止所有服务
echo 5) 清理所有数据 (谨慎使用!)
echo 6) 查看服务状态
echo 7) 查看实时日志
echo 8) 退出
echo.
set /p choice="请输入选项 (1-8): "

if "%choice%"=="1" goto deploy_prod
if "%choice%"=="2" goto deploy_dev
if "%choice%"=="3" goto start_only
if "%choice%"=="4" goto stop_all
if "%choice%"=="5" goto cleanup
if "%choice%"=="6" goto status
if "%choice%"=="7" goto logs
if "%choice%"=="8" goto end
goto menu_error

:deploy_prod
echo.
echo ════════════════════════════════════════
echo 正在部署生产环境...
echo ════════════════════════════════════════
echo.

:: 停止现有服务
echo [1/4] 停止现有服务...
docker-compose down >nul 2>&1

:: 构建镜像
echo [2/4] 构建 Docker 镜像...
docker-compose build --no-cache
if errorlevel 1 (
    echo [错误] 镜像构建失败
    pause
    exit /b 1
)

:: 启动服务
echo [3/4] 启动所有服务...
docker-compose up -d
if errorlevel 1 (
    echo [错误] 服务启动失败
    pause
    exit /b 1
)

:: 等待服务启动
echo [4/4] 等待服务启动...
timeout /t 10 /nobreak >nul

:: 检查服务状态
echo.
docker-compose ps
echo.

:: 健康检查
echo 正在检查后端服务...
for /l %%i in (1,1,5) do (
    curl -s http://localhost:5000/health >nul 2>&1 && (
        echo [✓] 后端服务健康检查通过
        goto health_ok
    )
    echo 等待后端服务启动 (尝试 %%i/5)...
    timeout /t 3 /nobreak >nul
)
echo [警告] 后端服务健康检查未通过，请查看日志
goto health_check_end

:health_ok
echo [✓] 所有服务启动成功!
:health_check_end

echo.
echo ════════════════════════════════════════
echo 部署完成!
echo ════════════════════════════════════════
echo.
echo 访问地址:
echo   前端：http://localhost
echo   后端 API: http://localhost:5000
echo   Redis: localhost:6379
echo.
echo 查看日志：docker-compose logs -f
echo 停止服务：docker-compose down
echo.
pause
goto end

:deploy_dev
echo.
echo ════════════════════════════════════════
echo 正在部署开发环境...
echo ════════════════════════════════════════
echo.

:: 停止现有服务
echo [1/3] 停止现有服务...
docker-compose -f docker-compose.dev.yml down >nul 2>&1

:: 构建并启动
echo [2/3] 构建并启动开发环境...
docker-compose -f docker-compose.dev.yml up -d --build
if errorlevel 1 (
    echo [错误] 开发环境启动失败
    pause
    exit /b 1
)

:: 等待服务启动
echo [3/3] 等待服务启动...
timeout /t 8 /nobreak >nul

:: 检查服务状态
echo.
docker-compose -f docker-compose.dev.yml ps
echo.

echo [✓] 开发环境部署完成!
echo.
echo 访问地址:
echo   后端 API: http://localhost:5000
echo   Redis: localhost:6379
echo.
echo 开发模式特点:
echo   - 代码修改即时生效
echo   - 启用 Flask 调试模式
echo   - 详细日志输出
echo.
pause
goto end

:start_only
echo.
echo ════════════════════════════════════════
echo 正在启动已构建的服务...
echo ════════════════════════════════════════
echo.

docker-compose start
if errorlevel 1 (
    echo [错误] 服务启动失败，可能需要重新构建
    pause
    exit /b 1
)

echo [✓] 服务启动成功!
docker-compose ps
echo.
pause
goto end

:stop_all
echo.
echo ════════════════════════════════════════
echo 正在停止所有服务...
echo ════════════════════════════════════════
echo.

docker-compose down
echo.
echo [✓] 所有服务已停止
echo.
pause
goto end

:cleanup
echo.
echo ════════════════════════════════════════
echo 警告：此操作将删除所有数据!
echo ════════════════════════════════════════
echo.
set /p confirm="确定要删除所有容器、镜像和数据卷吗？(y/N): "
if /i not "%confirm%"=="y" (
    echo 操作已取消
    pause
    goto end
)

echo.
echo 正在清理...
docker-compose down -v
docker system prune -f
echo.
echo [✓] 清理完成
echo.
pause
goto end

:status
echo.
echo ════════════════════════════════════════
echo 服务状态:
echo ════════════════════════════════════════
echo.
docker-compose ps
echo.
echo 磁盘使用情况:
docker system df
echo.
pause
goto end

:logs
echo.
echo ════════════════════════════════════════
echo 正在查看实时日志...
echo ════════════════════════════════════════
echo.
echo 按 Ctrl+C 停止查看
echo.
docker-compose logs -f
goto end

:menu_error
echo.
echo [错误] 无效的选项，请重新运行脚本
echo.
pause

:end
echo.
echo 感谢使用 XCAGI 一键部署工具!
echo.
