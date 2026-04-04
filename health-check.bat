@echo off
chcp 65001 >nul

:: ============================================
:: XCAGI 项目健康检查脚本
:: ============================================

echo.
echo ════════════════════════════════════════
echo  XCAGI 健康检查
echo ════════════════════════════════════════
echo.

cd /d "%~dp0"

:: 检查 Docker 服务
echo [1/5] 检查 Docker 服务...
docker-compose ps
if errorlevel 1 (
    echo [错误] Docker 服务未运行
    pause
    exit /b 1
)
echo.

:: 检查后端健康
echo [2/5] 检查后端服务...
curl -s http://localhost:5000/health >nul 2>&1
if errorlevel 1 (
    echo [警告] 后端服务未响应
) else (
    echo [✓] 后端服务正常
)
echo.

:: 检查前端
echo [3/5] 检查前端服务...
curl -s -o nul http://localhost/
if errorlevel 1 (
    echo [警告] 前端服务未响应
) else (
    echo [✓] 前端服务正常
)
echo.

:: 检查 Redis
echo [4/5] 检查 Redis 服务...
docker exec xcagi-redis redis-cli ping >nul 2>&1
if errorlevel 1 (
    echo [警告] Redis 服务未响应
) else (
    echo [✓] Redis 服务正常
)
echo.

:: 检查磁盘空间
echo [5/5] 检查磁盘使用情况...
docker system df
echo.

echo ════════════════════════════════════════
echo  健康检查完成!
echo ════════════════════════════════════════
echo.
pause
