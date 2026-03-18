@echo off
echo =========================================
echo     创建AI助手启动快捷方式
echo =========================================
echo.

REM 检查bat文件是否存在
if not exist "启动AI助手.bat" (
    echo ❌ 未找到启动文件
    pause
    exit /b 1
)

REM 创建快捷方式
echo 📁 创建快捷方式...
echo.

REM 使用PowerShell创建快捷方式
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('$PWD\AI助手-发货单标签生成系统.lnk'); $Shortcut.TargetPath = '$PWD\启动AI助手.bat'; $Shortcut.WorkingDirectory = '$PWD'; $Shortcut.Description = 'AI助手 - 发货单标签生成系统'; $Shortcut.Save(); Write-Host '✅ 快捷方式创建成功' -ForegroundColor Green"

if errorlevel 1 (
    echo.
    echo ⚠️  快捷方式创建失败，您可以：
    echo    1. 手动右键点击"启动AI助手.bat"创建桌面快捷方式
    echo    2. 或者将"启动AI助手.bat"拖拽到桌面
)

echo.
echo 📋 使用说明：
echo    1. 双击"AI助手-发货单标签生成系统.lnk"即可启动
echo    2. 或直接双击"启动AI助手.bat"
echo.
pause
