@echo off
chcp 65001 >nul

:: ============================================
:: XCAGI 项目重启脚本
:: ============================================

echo.
echo ════════════════════════════════════════
echo  正在重启所有服务...
echo ════════════════════════════════════════
echo.

cd /d "%~dp0"

docker-compose restart

if errorlevel 1 (
    echo [错误] 重启失败，尝试重新启动...
    docker-compose down
    docker-compose up -d
)

echo.
echo 等待服务启动...
timeout /t 5 /nobreak >nul

echo.
docker-compose ps
echo.
echo [✓] 服务重启完成
echo.
pause
