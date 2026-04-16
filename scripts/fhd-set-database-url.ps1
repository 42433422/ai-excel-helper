# PowerShell：设置与 fhd-set-database-url.cmd 相同的环境变量（当前窗口有效）
# 用法（必须「点源」执行，变量才会留在当前终端）：
#   . E:\FHD\scripts\fhd-set-database-url.ps1
# 或先 cd 到仓库：
#   Set-Location E:\FHD
#   . .\scripts\fhd-set-database-url.ps1

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
$env:FHD_ROOT = (Get-Location).Path
$env:DATABASE_URL = "postgresql+psycopg://xcagi:xcagi@127.0.0.1:5433/xcagi"
$env:FHD_DB_WRITE_TOKEN = "61408693"
# 一级只读锁：与写入令牌可相同或不同；无此头时 GET 产品/客户等返回 403
$env:FHD_DB_READ_TOKEN = "61408693"
$env:PYTHONPATH = (Get-Location).Path

Write-Host "[INFO] FHD_ROOT=$($env:FHD_ROOT)"
Write-Host "[INFO] DATABASE_URL=$($env:DATABASE_URL)"
Write-Host "[INFO] FHD_DB_WRITE_TOKEN set (bulk-import / admin)"
Write-Host "[INFO] FHD_DB_READ_TOKEN set (product/customer GET gate; restart backend to apply)"
Write-Host "[INFO] Start backend from this shell so it inherits these variables."
