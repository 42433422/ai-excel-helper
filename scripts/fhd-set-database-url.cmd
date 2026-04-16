@echo off
REM PowerShell users: dot-source  . "%~dp0fhd-set-database-url.ps1"  (do not paste this .cmd into pwsh line by line).
cd /d "%~dp0.."
set "FHD_ROOT=%CD%"
set "DATABASE_URL=postgresql+psycopg://xcagi:xcagi@127.0.0.1:5433/xcagi"
set "FHD_DB_WRITE_TOKEN=61408693"
set "FHD_DB_READ_TOKEN=61408693"
set "PYTHONPATH=%CD%"
echo [INFO] FHD_ROOT=%FHD_ROOT%
echo [INFO] DATABASE_URL=%DATABASE_URL%
echo [INFO] FHD_DB_WRITE_TOKEN is set for products_bulk_import and admin bulk-import.
echo [INFO] FHD_DB_READ_TOKEN is set for product/customer GET gate - restart backend to apply.
echo [INFO] Use: call "%~f0"   so these vars stay in this CMD window.
