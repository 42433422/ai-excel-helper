@echo off
chcp 65001 >nul
title XCAGI v7.0 局域网启动器
setlocal EnableExtensions EnableDelayedExpansion

REM cd to script dir first (relative paths and UAC cwd)
cd /d "%~dp0"

echo.
echo ========================================
echo        XCAGI v7.0 LAN Launcher
echo ========================================
echo.

set "WANT_ADMIN="
set "CONFIGURE_FW="
set "SKIP_MENU="
set "NO_ADMIN="

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="all" set "SKIP_MENU=1" & shift & goto parse_args
if /I "%~1"=="/all" set "SKIP_MENU=1" & shift & goto parse_args
if /I "%~1"=="0" set "MENU_EXIT=1" & shift & goto parse_args
if /I "%~1"=="/NoAdmin" set "NO_ADMIN=1" & shift & goto parse_args
if /I "%~1"=="--no-admin" set "NO_ADMIN=1" & shift & goto parse_args
if /I "%~1"=="/Admin" set "WANT_ADMIN=1" & shift & goto parse_args
if /I "%~1"=="/Firewall" set "WANT_ADMIN=1" & set "CONFIGURE_FW=1" & shift & goto parse_args
shift
goto parse_args
:args_done

REM Default to admin so LAN firewall/port checks behave consistently. Use /NoAdmin to skip UAC.
if not defined NO_ADMIN set "WANT_ADMIN=1"

REM UAC re-launch: preserve the shortcut all mode plus admin/firewall intent.
REM 关键：UAC 被取消 / Start-Process 抛异常时必须 pause，否则原窗口直接关闭 = 用户看到的"闪退"。
if defined WANT_ADMIN (
    net session >nul 2>&1
    if errorlevel 1 (
        echo [提示] 已请求管理员权限 UAC ...
        if defined CONFIGURE_FW (
            echo        原因: 已指定 /Firewall，需管理员才能添加入站规则。
            if defined SKIP_MENU (
                set "ELEV_ARGS=/Firewall all"
            ) else (
                set "ELEV_ARGS=/Firewall"
            )
        ) else (
            echo        原因: 默认以管理员权限启动；不会主动修改防火墙。
            if defined SKIP_MENU (
                set "ELEV_ARGS=/Admin all"
            ) else (
                set "ELEV_ARGS=/Admin"
            )
        )
        echo        若不需要高权限，请使用 start-lan.bat /NoAdmin
        powershell -NoProfile -Command "try { Start-Process -FilePath '%~f0' -Verb RunAs -ArgumentList '!ELEV_ARGS!' -ErrorAction Stop } catch { Write-Host ''; Write-Host ('[ERROR] Elevation failed: ' + $_.Exception.Message) -ForegroundColor Yellow; exit 2 }"
        if errorlevel 2 goto UAC_FAILED
        REM UAC ok; new elevated window started; safely exit this one.
        exit /b 0
    )
)
goto AFTER_UAC

:UAC_FAILED
echo.
echo [提示] 未获得管理员权限 ^(可能点击了 UAC 的"否"，或被策略阻止^)
echo        如需以普通用户运行，请使用参数  /NoAdmin
echo        例如:  start-lan.bat /NoAdmin
echo.
echo 按任意键退出...
pause >nul
exit /b 1

:AFTER_UAC

set "FWOPT="
if defined CONFIGURE_FW set "FWOPT=-ConfigureFirewall"

set "SCRIPT_DIR=%~dp0"
set "REPO_ROOT="

REM ---- Repo root resolution -------------------------------------------------
REM 1) XCAGI_ROOT   2) Phase A: ancestors only \<ancestor>\XCAGI\run.py
REM 3) Phase B: named subfolders; FHD-个人 before FHD when both under same parent
REM 4) %CD%   5) drive/profile candidates ^(FHD-个人 first^)

for %%I in (
    "%SCRIPT_DIR%."
    "%SCRIPT_DIR%.."
    "%SCRIPT_DIR%..\.."
    "%SCRIPT_DIR%..\..\.."
    "%SCRIPT_DIR%..\..\..\.."
    "%SCRIPT_DIR%..\..\..\..\.."
    "%SCRIPT_DIR%..\..\..\..\..\.."
    "%SCRIPT_DIR%..\..\..\..\..\..\.."
) do (
    if not defined REPO_ROOT if exist "%%~fI\XCAGI\run.py" set "REPO_ROOT=%%~fI"
)

REM XCAGI_ROOT is only a fallback. The launcher should prefer the repo that contains it.
if not defined REPO_ROOT if defined XCAGI_ROOT if exist "%XCAGI_ROOT%\XCAGI\run.py" set "REPO_ROOT=%XCAGI_ROOT%"

if not defined REPO_ROOT for %%I in (
    "%SCRIPT_DIR%."
    "%SCRIPT_DIR%.."
    "%SCRIPT_DIR%..\.."
    "%SCRIPT_DIR%..\..\.."
    "%SCRIPT_DIR%..\..\..\.."
    "%SCRIPT_DIR%..\..\..\..\.."
    "%SCRIPT_DIR%..\..\..\..\..\.."
    "%SCRIPT_DIR%..\..\..\..\..\..\.."
) do (
    if not defined REPO_ROOT if exist "%%~fI\FHD-个人\XCAGI\run.py" set "REPO_ROOT=%%~fI\FHD-个人"
    if not defined REPO_ROOT if exist "%%~fI\FHD\XCAGI\run.py" set "REPO_ROOT=%%~fI\FHD"
    if not defined REPO_ROOT if exist "%%~fI\XCMAX\FHD-个人\XCAGI\run.py" set "REPO_ROOT=%%~fI\XCMAX\FHD-个人"
    if not defined REPO_ROOT if exist "%%~fI\XCMAX\FHD\XCAGI\run.py" set "REPO_ROOT=%%~fI\XCMAX\FHD"
)

if not defined REPO_ROOT (
    if exist "%CD%\XCAGI\run.py" set "REPO_ROOT=%CD%"
    if not defined REPO_ROOT if exist "%CD%\FHD-个人\XCAGI\run.py" set "REPO_ROOT=%CD%\FHD-个人"
    if not defined REPO_ROOT if exist "%CD%\FHD\XCAGI\run.py" set "REPO_ROOT=%CD%\FHD"
    if not defined REPO_ROOT if exist "%CD%\XCMAX\FHD-个人\XCAGI\run.py" set "REPO_ROOT=%CD%\XCMAX\FHD-个人"
    if not defined REPO_ROOT if exist "%CD%\XCMAX\FHD\XCAGI\run.py" set "REPO_ROOT=%CD%\XCMAX\FHD"
)

if not defined REPO_ROOT (
    for %%D in (
        "%~d0\XCMAX\FHD-个人"
        "%~d0\XCMAX\FHD"
        "%~d0\FHD-个人"
        "%~d0\FHD"
        "%SystemDrive%\XCMAX\FHD-个人"
        "%SystemDrive%\XCMAX\FHD"
        "%SystemDrive%\FHD-个人"
        "%SystemDrive%\FHD"
        "%USERPROFILE%\XCMAX\FHD-个人"
        "%USERPROFILE%\XCMAX\FHD"
        "%USERPROFILE%\Desktop\XCMAX\FHD-个人"
        "%USERPROFILE%\Desktop\XCMAX\FHD"
        "%USERPROFILE%\Documents\XCMAX\FHD-个人"
        "%USERPROFILE%\Documents\XCMAX\FHD"
    ) do (
        if not defined REPO_ROOT if exist "%%~fD\XCAGI\run.py" set "REPO_ROOT=%%~fD"
    )
)

if not defined REPO_ROOT (
    echo [错误] 无法定位 XCAGI\run.py
    echo        脚本位置: %SCRIPT_DIR%
    echo        当前目录: %CD%
    echo.
    echo 解决方法 ^(任选其一^):
    echo   A^) 把 start-lan.bat 放回 仓库\scripts\launchers\ 下双击
    echo   B^) 设置环境变量 XCAGI_ROOT 指向包含 XCAGI\run.py 的目录, 例如:
    echo        setx XCAGI_ROOT "E:\XCMAX\FHD-个人"  或  "E:\XCMAX\FHD"
    echo      然后重新打开本脚本
    echo   C^) 在命令行里 cd 到对应仓库根后再运行 start-lan.bat
    echo.
    pause
    exit /b 1
)

REM If this resolves to FHD and sibling FHD-personal exists, force personal repo.
REM This also handles old shortcuts and old XCAGI_ROOT values.
set "REPO_ROOT_FIX=!REPO_ROOT!"
for /f "usebackq delims=" %%G in (`powershell -NoProfile -ExecutionPolicy Bypass -Command "$r = $env:REPO_ROOT_FIX; if (-not $r) { exit }; $r = $r -replace '[\\/]+$',''; $leaf = [System.IO.Path]::GetFileName($r); if ($leaf -cne 'FHD') { exit }; $parent = [System.IO.Path]::GetDirectoryName($r); $p = [System.IO.Path]::Combine($parent, ('FHD-' + [char]0x4E2A + [char]0x4EBA)); if (Test-Path -LiteralPath ([System.IO.Path]::Combine($p, 'XCAGI', 'run.py'))) { Write-Output $p }"`) do set "REPO_ROOT=%%G"
set "REPO_ROOT_FIX="

echo [INFO] 已定位仓库根: %REPO_ROOT%
cd /d "%REPO_ROOT%"

REM ---- start-lan.ps1：优先 REPO_ROOT，保证与 ps1 内 Resolve-RepoRoot 一致 ----
set "PS1_PATH="
if exist "%REPO_ROOT%\scripts\launchers\start-lan.ps1" set "PS1_PATH=%REPO_ROOT%\scripts\launchers\start-lan.ps1"
if not defined PS1_PATH if exist "%SCRIPT_DIR%start-lan.ps1" set "PS1_PATH=%SCRIPT_DIR%start-lan.ps1"
if not defined PS1_PATH if exist "%REPO_ROOT%\start-lan.ps1" set "PS1_PATH=%REPO_ROOT%\start-lan.ps1"
if not defined PS1_PATH (
    echo [错误] 找不到 start-lan.ps1
    echo        已尝试: "%REPO_ROOT%\scripts\launchers\start-lan.ps1"
    echo        已尝试: "%SCRIPT_DIR%start-lan.ps1"
    echo        请确认 仓库\scripts\launchers\start-lan.ps1 存在。
    echo.
    pause
    exit /b 1
)
echo [INFO] 使用 PS 脚本: %PS1_PATH%

if defined SKIP_MENU (
    echo.
    echo [INFO] 命令行已指定 all：直接启动后端 + 前端 ^(Vite dev^)，不再询问菜单。
    goto START_ALL
)
if defined MENU_EXIT goto END

REM 显示选项
echo 当前仓库根: %REPO_ROOT%
net session >nul 2>&1
if errorlevel 1 (
    echo 权限       : 当前用户 ^(未提权^)
) else (
    echo 权限       : 管理员
)
if defined CONFIGURE_FW (
    echo 防火墙     : 将尝试放行配置的后端/前端 TCP 端口 ^(由 start-lan.ps1 执行^)
) else (
    echo 防火墙     : 不修改 ^(局域网连不上时再运行: start-lan.bat /Firewall^)
)
echo.
echo [1] All dev       - backend + frontend, hot reload
echo [2] Backend only  - configured API port
echo [3] Frontend only - configured Vite port
echo [4] Stop          - kill repo python/node
echo [5] All + firewall - configured TCP inbound ^(admin UAC^)
echo [6] Backend + firewall ^(admin UAC^)
echo [7] Frontend + firewall ^(admin UAC^)
echo [0] Exit
echo.
echo CLI: start-lan.bat /Firewall   same as menu 5-7
echo Args: /NoAdmin   /Firewall   ^(append in shortcut Target^)
echo.
echo Tip: PowerShell window lists LAN URLs for phones on same WiFi.
echo      （菜单为英文：避免 cmd 将括号、加号、逗号等误解析为命令）
echo.
echo [快捷] start-lan.bat all   跳过本菜单，直接前后端一起启动。
echo.
REM choice 的 /M 必须用纯 ASCII：中文、加号、括号在 cmd 下会破坏解析，出现「xxx 不是内部或外部命令」。
echo Press a number key. Timeout 25s defaults to 1.
choice /C 12345670 /T 25 /D 1 /N /M "Press 1-7 or 0. See menu above. Timeout 25s default 1: "

if errorlevel 8 goto END
if errorlevel 7 goto START_FRONTEND_FW
if errorlevel 6 goto START_BACKEND_FW
if errorlevel 5 goto START_ALL_FW
if errorlevel 4 goto STOP_ALL
if errorlevel 3 goto START_FRONTEND
if errorlevel 2 goto START_BACKEND
if errorlevel 1 goto START_ALL
goto END

:MaybeElevateFirewall
net session >nul 2>&1
if not errorlevel 1 exit /b 0
echo.
echo [提示] 放行配置的后端/前端 TCP 端口需要管理员权限。将弹出 UAC；请在新窗口中确认完成。
echo        该窗口内应出现 Firewall rules OK 后自动返回此处。
echo.
REM 注意：不得把本段包在圆括号块里，否则 SCRIPT_DIR 会在块解析阶段被提前展开为空，导致提权窗口找不到 ps1 而卡在 pause。
REM powershell.exe 启动器只认 -File / -Command，不认 -LiteralPath；之前用 -LiteralPath 会让提权窗口直接报错闪退。
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Start-Process -FilePath powershell.exe -Verb RunAs -Wait -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-File',('%PS1_PATH%'),'-ConfigureFirewallOnly') -ErrorAction Stop } catch { Write-Host ('[ERROR] Firewall elevation failed: ' + $_.Exception.Message) -ForegroundColor Yellow; exit 2 }"
if errorlevel 2 (
    echo.
    echo [提示] 防火墙规则未添加 ^(UAC 被取消或被策略阻止^)。
    echo        可改用命令行: start-lan.bat /Firewall
)
echo.
echo 放行步骤已结束。若取消 UAC，请右键本脚本以管理员身份运行后重试，或命令行 start-lan.bat /Firewall
pause
exit /b 0

:START_ALL_FW
call :MaybeElevateFirewall
set "FWOPT="
net session >nul 2>&1
if not errorlevel 1 set "FWOPT=-ConfigureFirewall"
goto START_ALL

:START_BACKEND_FW
call :MaybeElevateFirewall
set "FWOPT="
net session >nul 2>&1
if not errorlevel 1 set "FWOPT=-ConfigureFirewall"
goto START_BACKEND

:START_FRONTEND_FW
call :MaybeElevateFirewall
set "FWOPT="
net session >nul 2>&1
if not errorlevel 1 set "FWOPT=-ConfigureFirewall"
goto START_FRONTEND

:START_ALL
echo.
echo [INFO] 正在启动前后端服务 ^(不附加 -NoFrontend / -NoBackend，由 start-lan.ps1 同时起 Vite^)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1_PATH%" %FWOPT%
if errorlevel 1 echo [警告] start-lan.ps1 退出码 %errorlevel%，请查看上方报错。
goto END

:START_BACKEND
echo.
echo [INFO] 正在启动后端服务...
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1_PATH%" -NoFrontend %FWOPT%
if errorlevel 1 echo [警告] start-lan.ps1 退出码 %errorlevel%，请查看上方报错。
goto END

:START_FRONTEND
echo.
echo [INFO] 正在启动前端服务...
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1_PATH%" -NoBackend %FWOPT%
if errorlevel 1 echo [警告] start-lan.ps1 退出码 %errorlevel%，请查看上方报错。
goto END

:STOP_ALL
echo.
echo [INFO] 正在停止本仓库相关的 python.exe / node.exe ...
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1_PATH%" -StopOnly
echo [√] 服务已停止
timeout /t 2 >nul
goto END

:END
echo.
echo 按任意键退出...
pause >nul
endlocal
