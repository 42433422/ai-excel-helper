@echo off
chcp 65001 >nul

:: ============================================
:: XCAGI 项目国内镜像加速脚本
:: ============================================

echo.
echo ════════════════════════════════════════
echo  Docker 镜像加速配置
echo ════════════════════════════════════════
echo.

echo 正在配置 Docker 镜像加速器...
echo.

:: 创建或更新 Docker daemon.json
set DOCKER_CONFIG=%APPDATA%\Docker\settings.json

echo [1/3] 检查 Docker 配置...
if not exist "%APPDATA%\Docker" (
    mkdir "%APPDATA%\Docker"
)

:: 使用国内镜像源
echo [2/3] 配置镜像加速器...
echo.
echo 将使用以下镜像加速器：
echo   - registry.docker-cn.com
echo   - mirror.ccs.tencentyun.com (腾讯云)
echo   - hub-mirror.c.163.com (网易云)
echo.

:: 创建 daemon.json 配置文件
set DAEMON_JSON=%PROGRAMDATA%\docker\config\daemon.json
if not exist "%PROGRAMDATA%\docker\config" (
    mkdir "%PROGRAMDATA%\docker\config"
)

:: 备份现有配置
if exist "%DAEMON_JSON%" (
    copy "%DAEMON_JSON%" "%DAEMON_JSON%.bak" >nul
    echo [✓] 已备份现有配置
)

:: 写入新的镜像加速配置
echo {
  "registry-mirrors": [
    "https://registry.docker-cn.com",
    "https://mirror.ccs.tencentyun.com",
    "https://hub-mirror.c.163.com",
    "https://docker.mirrors.ustc.edu.cn"
  ],
  "debug": false
} > "%DAEMON_JSON%"

echo [✓] 配置文件已写入：%DAEMON_JSON%
echo.

echo [3/3] 重启 Docker 服务...
echo.
echo 请手动重启 Docker Desktop：
echo   1. 右键点击系统托盘中的 Docker 图标
echo   2. 选择 "Restart Docker Desktop"
echo   3. 或者退出后重新打开 Docker Desktop
echo.
echo 重启 Docker 后，再次运行部署脚本即可。
echo.

:: 提供手动拉取选项
echo 或者，你也可以选择手动拉取镜像：
echo.
echo 手动拉取命令：
echo   docker pull registry.docker-cn.com/library/redis:7-alpine
echo   docker tag registry.docker-cn.com/library/redis:7-alpine redis:7-alpine
echo.

pause
