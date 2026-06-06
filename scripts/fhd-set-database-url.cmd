@echo off
REM Configure DATABASE_URL / VECTOR_DB_URL / PYTHONPATH for local CMD sessions.
REM ASCII-only; CRLF line endings; UTF-8 without BOM. Safe: call "%~dp0fhd-set-database-url.cmd"

pushd "%~dp0.."
set "FHD_ROOT=%CD%"
if "%FHD_ROOT:~-1%"=="\" set "FHD_ROOT=%FHD_ROOT:~0,-1%"
popd

set "XCAGI_ROOT=%FHD_ROOT%\XCAGI"
if not exist "%XCAGI_ROOT%\app\" set "XCAGI_ROOT="

if not defined DATABASE_URL if defined XCAGI_ROOT if exist "%XCAGI_ROOT%\.env" (
  for /f "usebackq tokens=1* delims==" %%A in (`findstr /R /C:"^[ ]*DATABASE_URL[ ]*=" "%XCAGI_ROOT%\.env"`) do set "DATABASE_URL=%%B"
)
if not defined VECTOR_DB_URL if defined XCAGI_ROOT if exist "%XCAGI_ROOT%\.env" (
  for /f "usebackq tokens=1* delims==" %%A in (`findstr /R /C:"^[ ]*VECTOR_DB_URL[ ]*=" "%XCAGI_ROOT%\.env"`) do set "VECTOR_DB_URL=%%B"
)

set "PG5433_UP=0"
set "PG5432_UP=0"
powershell -NoProfile -Command "$c=New-Object Net.Sockets.TcpClient; try{$c.Connect('127.0.0.1',5433); exit 0} catch {exit 1} finally{$c.Dispose()}" >nul 2>&1
if not errorlevel 1 set "PG5433_UP=1"
powershell -NoProfile -Command "$c=New-Object Net.Sockets.TcpClient; try{$c.Connect('127.0.0.1',5432); exit 0} catch {exit 1} finally{$c.Dispose()}" >nul 2>&1
if not errorlevel 1 set "PG5432_UP=1"

if not defined DATABASE_URL (
  set "PG_PORT="
  if "%PG5433_UP%"=="1" set "PG_PORT=5433"
  if not defined PG_PORT if "%PG5432_UP%"=="1" set "PG_PORT=5432"
  if not defined PG_PORT set "PG_PORT=5433"
  set "DATABASE_URL=postgresql+psycopg://xcagi:xcagi@127.0.0.1:%PG_PORT%/xcagi"
)

REM 治根注：FHD_ROOT 必须放在 PYTHONPATH 第一位，XCAGI 在后（或不放）。
REM 历史上反过来会让 XCAGI/resources/、XCAGI/scripts/ 下的僵尸副本永远赢
REM FHD 主版本（namespace package 先到先得），典型症状是 /api/system/industries
REM 拿到 4-14 旧 industry_config，前端下拉出现 4 项 YAML 硬编码幽灵。
if exist "%FHD_ROOT%\XCAGI\app\" (
  if not defined PYTHONPATH (
    set "PYTHONPATH=%FHD_ROOT%;%FHD_ROOT%\XCAGI"
  ) else (
    echo ";%PYTHONPATH%;" | findstr /i /c:";%FHD_ROOT%;" >nul
    if errorlevel 1 set "PYTHONPATH=%FHD_ROOT%;%FHD_ROOT%\XCAGI;%PYTHONPATH%"
  )
) else (
  if not defined PYTHONPATH set "PYTHONPATH=%FHD_ROOT%"
)

set "FHD_REPO_ROOT=%FHD_ROOT%"
set "PG5433_UP="
set "PG5432_UP="
set "PG_PORT="
exit /b 0
