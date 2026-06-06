@echo off
REM 兼容旧入口：转发到桌面 SQLite 统一启动脚本（所有 SKU 共用本地库策略）
cd /d "%~dp0XCAGI"
call "%~dp0XCAGI\start-desktop-sqlite.bat"
