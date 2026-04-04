@echo off
chcp 65001 >nul
echo =============================================
echo   XCAGI 打包构建脚本
echo =============================================
echo.

cd /d "%~dp0"

if not exist "node_modules" (
    echo [步骤 1/4] 安装前端依赖...
    cd frontend
    call npm install
    cd ..
) else (
    echo [跳过] 前端依赖已安装
)

echo.
echo [步骤 2/4] 构建前端...
cd frontend
call npm run build
if errorlevel 1 (
    echo 前端构建失败！
    pause
    exit /b 1
)
cd ..

echo.
echo [步骤 3/4] 安装 PyInstaller...
pip install pyinstaller -q

echo.
echo [步骤 4/4] 打包 Python 应用...
pyinstaller xcagi.spec --clean

echo.
echo =============================================
echo   打包完成！
echo =============================================
echo.
echo 输出目录: dist\XCAGI
echo.
echo 启动应用: dist\XCAGI\XCAGI.exe
echo.
pause
