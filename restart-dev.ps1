# 释放 XCAGI 开发常用端口（仅 LISTEN 进程）
$ports = 5000, 5001
foreach ($p in $ports) {
    Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | ForEach-Object {
        $procId = $_.OwningProcess
        if ($procId) {
            Write-Host "  Stopping PID $procId (port $p)"
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        }
    }
}
