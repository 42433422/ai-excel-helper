# 验证一级只读锁：默认开启（未设 FHD_DISABLE_DB_READ_LOCK=1 时），无 X-FHD-Db-Read-Token 的 list 请求应返回 403。
# 用法: .\scripts\verify-db-read-lock.ps1
#       .\scripts\verify-db-read-lock.ps1 http://127.0.0.1:8000

param(
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$base = $BaseUrl.TrimEnd("/")
$u = "$base/api/products/list?page=1&per_page=1"
$code = 0
try {
    $r = Invoke-WebRequest -Uri $u -Method GET -UseBasicParsing
    $code = [int]$r.StatusCode
} catch {
    $resp = $_.Exception.Response
    if ($null -ne $resp) {
        $code = [int]$resp.StatusCode
    } else {
        Write-Host "[FAIL] Request error: $($_.Exception.Message)"
        exit 2
    }
}

if ($code -eq 403) {
    Write-Host "[OK] Read lock active: GET list without X-FHD-Db-Read-Token returned 403"
    exit 0
}
Write-Host "[FAIL] Expected HTTP 403 without read token, got $code. If you disabled lock, unset FHD_DISABLE_DB_READ_LOCK; else restart backend."
exit 1
