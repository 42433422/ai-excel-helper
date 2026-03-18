@echo off
echo 临时更改Windows默认打印机
rundll32 printui.dll,PrintUIEntry /y /n "TSC TTP-244 Plus"
echo 默认打印机已更改为TSC TTP-244 Plus
pause
