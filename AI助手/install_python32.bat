@echo off
echo ==========================================
echo   安装32位Python 3.11.9
echo ==========================================
echo.
echo 正在安装32位Python到当前目录...
echo.

REM 安装到当前目录的python32文件夹
mkdir python32 2>nul

REM 运行安装程序
python-3.11.9-32bit.exe /quiet InstallAllUsers=0 PrependPath=0 Include_test=0 TargetDir="%~dp0python32"

echo.
echo 安装完成！
echo.
echo 请检查 %~dp0python32 目录
echo.
pause
