@echo off
chcp 65001 >nul

:: ============================================
:: XCAGI 项目手动拉取镜像脚本
:: ============================================

echo.
echo ════════════════════════════════════════
echo  手动拉取 Docker 镜像
echo ════════════════════════════════════════
echo.

cd /d "%~dp0"

echo 正在从国内镜像源拉取所需的 Docker 镜像...
echo.

:: 拉取 Redis 镜像
echo [1/2] 拉取 Redis 镜像...
echo 使用阿里云镜像源...
docker pull registry.cn-hangzhou.aliyuncs.com/library/redis:7-alpine
if errorlevel 1 (
    echo 尝试使用其他镜像源...
    docker pull registry.docker-cn.com/library/redis:7-alpine
)

:: 如果拉取成功，创建标签
if not errorlevel 1 (
    echo [✓] Redis 镜像拉取成功
) else (
    echo [!] Redis 镜像拉取失败，请检查网络连接
    goto :pull_python
)

echo.

:: 拉取 Python 镜像
echo [2/2] 拉取 Python 镜像...
echo 使用阿里云镜像源...
docker pull registry.cn-hangzhou.aliyuncs.com/library/python:3.11-slim
if errorlevel 1 (
    echo 尝试使用其他镜像源...
    docker pull registry.docker-cn.com/library/python:3.11-slim
)

if not errorlevel 1 (
    echo [✓] Python 镜像拉取成功
) else (
    echo [!] Python 镜像拉取失败，请检查网络连接
)

echo.
echo ════════════════════════════════════════
echo  镜像拉取完成!
echo ════════════════════════════════════════
echo.
echo 现在可以运行部署脚本了：
echo   双击 deploy.bat
echo.

pause
