@echo off
chcp 65001
cls
echo ==========================================
echo   科密CM500高拍仪服务启动器
echo ==========================================
echo.
echo 正在检查Python环境...

python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.7+
    pause
    exit /b 1
)

echo [OK] Python已安装
echo.
echo 正在启动科密CM500桥接服务...
echo 服务地址: http://127.0.0.1:5001
echo.
echo 按Ctrl+C停止服务
echo ==========================================

python comet_scanner_service.py

pause
