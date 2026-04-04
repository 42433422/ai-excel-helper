@echo off
setlocal EnableExtensions
:: Portable npm shim: common install dirs first, then first npm.cmd on PATH that is not this file.
if exist "%ProgramFiles%\nodejs\npm.cmd" (
  "%ProgramFiles%\nodejs\npm.cmd" %*
  exit /b %ERRORLEVEL%
)
if exist "%ProgramFiles(x86)%\nodejs\npm.cmd" (
  "%ProgramFiles(x86)%\nodejs\npm.cmd" %*
  exit /b %ERRORLEVEL%
)
where npm.cmd >nul 2>&1
if errorlevel 1 (
  echo [ERROR] npm.cmd not found. Install Node.js or add npm to PATH.
  exit /b 9009
)
for /f "delims=" %%i in ('where npm.cmd') do (
  if /i not "%%~fi"=="%~f0" (
    call "%%~fi" %*
    exit /b %ERRORLEVEL%
  )
)
echo [ERROR] npm.cmd not found.
exit /b 9009
