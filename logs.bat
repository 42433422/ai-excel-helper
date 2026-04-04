@echo off
chcp 65001 >nul

:: ============================================
:: XCAGI 项目日志查看脚本
:: ============================================

echo.
echo ════════════════════════════════════════
echo  XCAGI 实时日志查看器
echo ════════════════════════════════════════
echo.

cd /d "%~dp0"

if "%~1"=="" (
    echo 正在连接所有服务日志...
    echo 按 Ctrl+C 停止查看
    echo.
    docker-compose logs -f
) else (
    echo 正在连接 %1 服务日志...
    echo 按 Ctrl+C 停止查看
    echo.
    docker-compose logs -f %1
)
