@echo off
chcp 65001 >nul

:: ============================================
:: XCAGI 项目网络问题解决方案
:: ============================================

echo.
echo ════════════════════════════════════════
echo  Docker 网络问题解决方案
echo ════════════════════════════════════════
echo.

echo 检测到网络连接问题，无法从 Docker Hub 拉取镜像。
echo.
echo 请按以下步骤解决：
echo.
echo ┌────────────────────────────────────────┐
echo │ 方案 1: 配置 Docker 镜像加速器          │
echo ├────────────────────────────────────────┤
echo │ 1. 打开 Docker Desktop                 │
echo │ 2. 点击 Settings (齿轮图标)            │
echo │ 3. 选择 Docker Engine                  │
echo │ 4. 在配置文件中添加：                  │
echo │                                        │
echo │ {                                      │
echo │   "registry-mirrors": [                │
echo │     "https://hub-mirror.c.163.com",    │
echo │     "https://docker.m.daocloud.io"     │
echo │   ]                                    │
echo │ }                                      │
echo │                                        │
echo │ 5. 点击 Apply & restart                │
echo └────────────────────────────────────────┘
echo.
echo ┌────────────────────────────────────────┐
echo │ 方案 2: 使用手机热点（临时方案）        │
echo ├────────────────────────────────────────┤
echo │ 1. 用手机开启热点                      │
echo │ 2. 电脑连接手机热点                    │
echo │ 3. 运行以下命令拉取镜像：              │
echo │                                        │
echo │    docker pull redis:7-alpine          │
echo │    docker pull python:3.11-slim        │
echo │                                        │
echo │ 4. 拉取完成后切回原网络                │
echo │ 5. 运行部署脚本                        │
echo └────────────────────────────────────────┘
echo.
echo ┌────────────────────────────────────────┐
echo │ 方案 3: 离线导入镜像                    │
echo ├────────────────────────────────────────┤
echo │ 1. 在有网络的电脑上下载镜像：          │
echo │    docker save -o redis.tar redis:7-alpine           │
echo │    docker save -o python.tar python:3.11-slim        │
echo │                                        │
echo │ 2. 拷贝 tar 文件到本机                   │
echo │ 3. 导入镜像：                          │
echo │    docker load -i redis.tar            │
echo │    docker load -i python.tar           │
echo │                                        │
echo │ 4. 运行部署脚本                        │
echo └────────────────────────────────────────┘
echo.
echo ┌────────────────────────────────────────┐
echo │ 方案 4: 修改 docker-compose.yml         │
echo ├────────────────────────────────────────┤
echo │ 使用本地已有的镜像或替代镜像           │
echo └────────────────────────────────────────┘
echo.

echo.
echo ════════════════════════════════════════
echo  当前建议
echo ════════════════════════════════════════
echo.
echo 由于所有镜像源都连接失败，建议：
echo.
echo 1. 优先尝试方案 1（配置镜像加速器）
echo 2. 或使用方案 2（手机热点）快速解决
echo 3. 如果都不行，使用方案 3（离线导入）
echo.

echo 是否要查看详细的配置指南？
set /p view_guide="输入 Y 查看指南，输入 N 退出： "

if /i "%view_guide%"=="Y" (
    start "" "国内镜像配置指南.md"
)

echo.
pause
