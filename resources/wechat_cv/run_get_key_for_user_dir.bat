@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 从微信进程内存扫描 64 位 hex 并验证（需管理员权限才能读进程内存）
echo 数据目录已配置为: E:\缓存\WeChat Files\wxid_bommxleja9kq22
echo.
set WECHAT_DATA_DIR=E:\缓存\WeChat Files\wxid_bommxleja9kq22
python wechat_db_key_from_memory.py "E:\缓存\WeChat Files\wxid_bommxleja9kq22\Msg\ChatMsg.db"
if errorlevel 1 (
    echo.
    echo 若提示「0 个候选」或无法验证，请右键本 bat 选择「以管理员身份运行」。
)
pause
