#!/usr/bin/env pwsh
# ============================================================================
# 本文件须以 UTF-8 BOM 保存；否则 Windows PowerShell 5.1 会按 ANSI 解析，中文串会触发 ParserError。
# XCAGI v7.0 LAN Launcher
#
# Location (after restructure): scripts/launchers/start-lan.ps1
# Repo root is resolved dynamically from $PSScriptRoot so this script works
# no matter where the checkout lives (no more hard-coded E:\FHD paths).
# ============================================================================

param(
    [switch]$NoFrontend,
    [switch]$NoBackend,
    [switch]$NoReload,
    [switch]$StopOnly,
    [switch]$ConfigureFirewall,
    # 仅添加 TCP 5000/5001 入站规则后退出（须管理员；供 start-lan.bat 菜单 UAC 提权窗口使用）
    [switch]$ConfigureFirewallOnly,
    # 跳过「杀旧 python/node」；WMI 极慢/卡死时可加本开关（可能残留旧进程占端口）
    [switch]$SkipKillExisting,
    [int]$BackendWaitSec,
    [int]$FrontendWaitSec
)

if (-not $PSBoundParameters.ContainsKey('BackendWaitSec')) { $BackendWaitSec = 30 }
if (-not $PSBoundParameters.ContainsKey('FrontendWaitSec')) { $FrontendWaitSec = 45 }

$ErrorActionPreference = "Stop"
try {
    $host.UI.RawUI.WindowTitle = "XCAGI v7.0 LAN Server"
} catch {
    # 非交互宿主（CI/子进程）可能无法设置控制台标题
}

function Test-IsAdmin {
    try {
        $id = [System.Security.Principal.WindowsIdentity]::GetCurrent()
        $pr = New-Object System.Security.Principal.WindowsPrincipal($id)
        return $pr.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
    } catch {
        return $false
    }
}
$IsAdmin = Test-IsAdmin

# --- Path resolution --------------------------------------------------------
function Resolve-RepoRoot {
    $dir = (Resolve-Path -LiteralPath $PSScriptRoot).Path
    for ($i = 0; $i -lt 6 -and $dir; $i++) {
        if (Test-Path (Join-Path $dir "XCAGI\run.py")) { return $dir }
        $parent = Split-Path -Parent $dir
        if (-not $parent -or $parent -eq $dir) { break }
        $dir = $parent
    }
    throw "XCAGI\run.py not found while walking up from $PSScriptRoot"
}

$RepoRoot = Resolve-RepoRoot
$BackendDir = Join-Path $RepoRoot "XCAGI"
$AppDir   = Join-Path $RepoRoot "app"
$FrontDir = Join-Path $RepoRoot "frontend"
$ModsDir  = Join-Path $BackendDir "mods"
$VenvPy   = Join-Path $BackendDir ".venv\Scripts\python.exe"

function Get-DotEnvValue {
    param(
        [string]$Path,
        [string[]]$Names
    )
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    foreach ($line in Get-Content -LiteralPath $Path -ErrorAction SilentlyContinue) {
        if ($line -match '^\s*(#|$)') { continue }
        if ($line -notmatch '^\s*([^=\s]+)\s*=\s*(.*)\s*$') { continue }
        $name = $matches[1]
        if ($Names -notcontains $name) { continue }
        return ($matches[2]).Trim().Trim('"').Trim("'")
    }
    return $null
}

function Resolve-Port {
    param(
        [object[]]$Candidates,
        [int]$Default
    )
    foreach ($candidate in $Candidates) {
        $raw = ([string]$candidate).Trim()
        if (-not $raw) { continue }
        $port = 0
        if ([int]::TryParse($raw, [ref]$port) -and $port -gt 0 -and $port -lt 65536) {
            return $port
        }
    }
    return $Default
}

$RepoEnvPath = Join-Path $RepoRoot ".env"
$BackendPort = Resolve-Port -Default 5000 -Candidates @(
    $env:XCAGI_API_PORT,
    $env:FASTAPI_PORT,
    (Get-DotEnvValue -Path $RepoEnvPath -Names @("XCAGI_API_PORT", "FASTAPI_PORT"))
)
$FrontendPort = Resolve-Port -Default 5001 -Candidates @(
    $env:VITE_DEV_PORT,
    (Get-DotEnvValue -Path (Join-Path $FrontDir ".env.development.local") -Names @("VITE_DEV_PORT")),
    (Get-DotEnvValue -Path (Join-Path $FrontDir ".env.local") -Names @("VITE_DEV_PORT")),
    (Get-DotEnvValue -Path (Join-Path $FrontDir ".env.development") -Names @("VITE_DEV_PORT"))
)

# Sanity
if (-not (Test-Path (Join-Path $BackendDir "run_fastapi.py"))) {
    Write-Host "[ERROR] XCAGI\run.py not found under $RepoRoot" -ForegroundColor Red
    Write-Host "        Expected layout: <repo>/scripts/launchers/start-lan.ps1" -ForegroundColor Red
    exit 1
}

# Pick python: prefer .venv, fallback to whatever is on PATH
function Resolve-Python {
    if (Test-Path $VenvPy) { return $VenvPy }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $cmd = Get-Command py -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    throw "Python not found (no .venv and no 'python' / 'py' on PATH)."
}

# --- Console helpers --------------------------------------------------------
function Write-Info($msg)    { Write-Host $msg -ForegroundColor Cyan }
function Write-Success($msg) { Write-Host $msg -ForegroundColor Green }
function Write-Warn($msg)    { Write-Host $msg -ForegroundColor Yellow }
function Write-Err($msg)     { Write-Host $msg -ForegroundColor Red }

function Invoke-NetshAdvFirewall {
    <#
    通过 netsh 调用高级防火墙，避免 Get-NetFirewallRule / New-NetFirewallRule
    在部分机器上长时间卡住（NetSecurity + WMI / MPS 无响应）。
    #>
    param(
        [string]$ArgumentLine,
        [int]$WaitMs = 45000
    )
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName               = "netsh.exe"
    $psi.Arguments              = $ArgumentLine
    $psi.UseShellExecute        = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError  = $true
    $psi.CreateNoWindow         = $true
    $p = New-Object System.Diagnostics.Process
    $p.StartInfo = $psi
    [void]$p.Start()
    # 必须先 WaitForExit 再 ReadToEnd，否则 stdout 缓冲区满时可能死锁
    if (-not $p.WaitForExit($WaitMs)) {
        try { $p.Kill() } catch {}
        throw "netsh timed out after ${WaitMs}ms: $ArgumentLine"
    }
    $stdout = $p.StandardOutput.ReadToEnd()
    $stderr = $p.StandardError.ReadToEnd()
    return [pscustomobject]@{
        ExitCode = $p.ExitCode
        StdOut   = $stdout
        StdErr   = $stderr
    }
}

function Ensure-FirewallRule {
    param([string]$Name, [int]$Port)
    $safeName = $Name.Replace('"', '')
    try {
        Write-Host ('  firewall: checking "{0}" (tcp/{1}) ...' -f $Name, $Port) -ForegroundColor DarkGray
        try { [Console]::Out.Flush() } catch {}

        $showArgs = 'advfirewall firewall show rule name="{0}"' -f $safeName
        $show = Invoke-NetshAdvFirewall -ArgumentLine $showArgs -WaitMs 30000
        $showText = ($show.StdOut + "`n" + $show.StdErr)
        # netsh 在「无匹配规则」时多为 exit 1；英文/简中/日等提示不同，不能只看 "No rules match"
        $noRuleMsg = $showText -match '(?i)No rules match|没有与指定标准相匹配|指定の条件に一致する規則はありません|Keine Regeln entsprechen'
        $hasRuleBlock = $showText -match '(?i)Rule Name\s*:|规则名称'

        $needAdd = $false
        if ($hasRuleBlock) {
            Write-Host ('  = firewall rule already present: {0} (tcp/{1})' -f $Name, $Port) -ForegroundColor DarkGray
        } elseif ($noRuleMsg -or $show.ExitCode -eq 1) {
            $needAdd = $true
        } else {
            Write-Warn ('  firewall: "show rule" exit {0}; output unclear, will try add: {1}' -f $show.ExitCode, $Name)
            $needAdd = $true
        }

        if ($needAdd) {
            Write-Host ('  firewall: adding "{0}" ...' -f $Name) -ForegroundColor DarkGray
            try { [Console]::Out.Flush() } catch {}

            $addArgs = 'advfirewall firewall add rule name="{0}" dir=in action=allow protocol=TCP localport={1} profile=any' -f $safeName, $Port
            $add = Invoke-NetshAdvFirewall -ArgumentLine $addArgs -WaitMs 45000
            $addText = ($add.StdOut + "`n" + $add.StdErr)
            if ($add.ExitCode -ne 0 -and $addText -notmatch '(?i)already been created|already exists|duplicate|specified name already exists|已存在|已创建|重复') {
                throw ('netsh add failed exit={0}: {1}' -f $add.ExitCode, $addText.Trim())
            }
            Write-Host ('  + firewall rule OK: {0} (tcp/{1})' -f $Name, $Port) -ForegroundColor DarkGray
        }
    } catch {
        Write-Warn ('Failed to configure firewall rule {0} (tcp/{1}): {2}' -f $Name, $Port, $_.Exception.Message)
    }
}

if ($ConfigureFirewallOnly) {
    if (-not $IsAdmin) {
        Write-Err "[ERROR] -ConfigureFirewallOnly 需要管理员权限。请接受 UAC，或使用 start-lan.bat /Firewall。"
        exit 1
    }
    Write-Info ("Adding inbound firewall rules (TCP {0}/{1}) ..." -f $BackendPort, $FrontendPort)
    Ensure-FirewallRule -Name ("XCAGI Backend ({0})" -f $BackendPort)  -Port $BackendPort
    Ensure-FirewallRule -Name ("XCAGI Frontend ({0})" -f $FrontendPort) -Port $FrontendPort
    Write-Success "Firewall rules OK. Close this window; the parent launcher will continue."
    exit 0
}

$Python = Resolve-Python

# --- LAN IP discovery -------------------------------------------------------
function Test-IsLikelyWifiInterface([string]$alias) {
    if (-not $alias) { return $false }
    return [bool]($alias -match '(?i)(WLAN|Wi-?Fi|802\.11|无线|\bWWAN\b)')
}

function Get-LanIpv4Rows {
    param(
        # 跳过 Get-NetIPConfiguration（在部分环境会长时间无响应）；仅用 Get-NetIPAddress 兜底逻辑
        [switch]$NetAddressOnly
    )
    # 虚拟/隧道/环回；避免把 WSL/ Docker/蓝牙 PAN 等当成「给手机连的 WiFi 网段」
    $ifaceSkip = '(?i)(Loopback|WSL|Hyper-V|Docker|VirtualBox|VMware|Teredo|vEthernet|Tailscale|ZeroTier|NPF|TAP|VPN|Pseudo|伪|虚拟|Bluetooth|Npcap|isatap|6to4)'
    # RFC1918 私网（含 172.16–31.*）
    $privateRe = '^(10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|192\.168\.)'

    $hits = @()
    if (-not $NetAddressOnly) {
        try {
            foreach ($cfg in Get-NetIPConfiguration -ErrorAction SilentlyContinue) {
                if (-not $cfg.IPv4Address) { continue }
                if ($cfg.InterfaceAlias -match $ifaceSkip) { continue }
                if ($cfg.NetAdapter -and $cfg.NetAdapter.Status -ne 'Up') { continue }
                foreach ($addr in @($cfg.IPv4Address)) {
                    $ip = $addr.IPAddress
                    if (-not $ip) { continue }
                    if ($ip -match '^(127\.|169\.254\.)') { continue }
                    if ($ip -notmatch $privateRe) { continue }
                    $hasGw = $null -ne $cfg.IPv4DefaultGateway
                    $metric = 99999
                    try {
                        $ifi = Get-NetIPInterface -InterfaceIndex $cfg.InterfaceIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue
                        if ($ifi) { $metric = [int]$ifi.InterfaceMetric }
                    } catch {}
                    $wlanPrio = if (Test-IsLikelyWifiInterface $cfg.InterfaceAlias) { 0 } else { 1 }
                    $hits += [pscustomobject]@{
                        IP               = $ip
                        InterfaceAlias   = [string]$cfg.InterfaceAlias
                        HasGw            = $hasGw
                        Metric           = $metric
                        WlanPrio         = $wlanPrio
                    }
                }
            }
        } catch {}
    }

    if ($NetAddressOnly -or $hits.Count -eq 0) {
        # 回退 / 快速路径：Get-NetIPAddress（无默认网关信息，通常比 NetIPConfiguration 不易卡死）
        $ifaceSkip2 = $ifaceSkip
        $privateRe2 = $privateRe
        foreach ($na in Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue) {
            if ($na.InterfaceAlias -match $ifaceSkip2) { continue }
            $ip = $na.IPAddress
            if (-not $ip -or $ip -match '^(127\.|169\.254\.)') { continue }
            if ($ip -notmatch $privateRe2) { continue }
            $wlanPrio = if (Test-IsLikelyWifiInterface $na.InterfaceAlias) { 0 } else { 1 }
            $hits += [pscustomobject]@{
                IP               = $ip
                InterfaceAlias   = [string]$na.InterfaceAlias
                HasGw            = $false
                Metric           = 99999
                WlanPrio         = $wlanPrio
            }
        }
    }

    # 同一 IP 多网卡记录时保留更优一条
    $dedup = @{}
    foreach ($h in $hits) {
        $key = $h.IP
        if (-not $dedup.ContainsKey($key)) {
            $dedup[$key] = $h
            continue
        }
        $o = $dedup[$key]
        $pickNew =
            ($h.WlanPrio -lt $o.WlanPrio) -or
            ($h.WlanPrio -eq $o.WlanPrio -and $h.HasGw -and -not $o.HasGw) -or
            ($h.WlanPrio -eq $o.WlanPrio -and $h.HasGw -eq $o.HasGw -and $h.Metric -lt $o.Metric)
        if ($pickNew) { $dedup[$key] = $h }
    }

    return @(
        $dedup.Values |
            Sort-Object WlanPrio, @{ Expression = { -not $_.HasGw } }, Metric, InterfaceAlias |
            ForEach-Object { $_ }
    )
}

function Get-LanIP {
    $rows = @(Get-LanIpv4Rows -NetAddressOnly)
    if ($rows.Count -ge 1) { return [string]$rows[0].IP }
    return '127.0.0.1'
}

function Get-QuickPrivateIPv4ForHmr {
    <#
    仅给 Vite HMR 用：不调 Get-NetIPConfiguration（在不少机器上会卡死数分钟）。
    用 ipconfig 文本解析私网 IPv4，进程级 5s 超时。
    #>
    try {
        Write-Host "  detecting LAN IPv4 for Vite HMR via ipconfig (<=5s, avoids slow NetIPConfiguration) ..." -ForegroundColor DarkGray
        try { [Console]::Out.Flush() } catch {}
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName               = 'ipconfig.exe'
        $psi.Arguments               = ''
        $psi.UseShellExecute         = $false
        $psi.RedirectStandardOutput  = $true
        $psi.RedirectStandardError   = $true
        $psi.CreateNoWindow          = $true
        $pr = New-Object System.Diagnostics.Process
        $pr.StartInfo = $psi
        [void]$pr.Start()
        if (-not $pr.WaitForExit(5000)) {
            try { $pr.Kill() } catch {}
            return '127.0.0.1'
        }
        $txt = $pr.StandardOutput.ReadToEnd() + $pr.StandardError.ReadToEnd()
        $priv = [regex]'\b(10\.(\d{1,3}\.){2}\d{1,3}|192\.168\.(\d{1,3}\.){2}\d{1,3}|172\.(1[6-9]|2[0-9]|3[01])\.(\d{1,3}\.){2}\d{1,3})\b'
        foreach ($m in $priv.Matches($txt)) {
            $ip = [string]$m.Value
            if ($ip -and $ip -notmatch '^127\.') { return $ip }
        }
    } catch {}
    return '127.0.0.1'
}

# --- Stop existing backend/frontend processes in THIS repo ------------------
function Stop-Existing {
    if ($SkipKillExisting) {
        Write-Warn "SkipKillExisting: 已跳过清理旧 python/node（若端口被占用请手动结束进程或去掉本参数）。"
        return
    }
    Write-Info "Stopping existing processes under $RepoRoot ..."
    Write-Host '  (先按 exe 路径匹配本仓库；其余才查 WMI。单次 WMI 有超时，避免整段卡死无输出)' -ForegroundColor DarkGray
    try { [Console]::Out.Flush() } catch {}

    $rootNorm = ""
    try {
        $rootNorm = ((Resolve-Path -LiteralPath $RepoRoot).ProviderPath).TrimEnd('\')
    } catch {
        $rootNorm = $RepoRoot.TrimEnd('\')
    }
    $repoPattern = $RepoRoot.Replace('\', '\\')
    $deadline = [datetime]::UtcNow.AddSeconds(25)
    $cimTimeoutSec = 2
    $cimHasTimeout = $false
    try {
        $cimHasTimeout = [bool]((Get-Command Get-CimInstance -ErrorAction Stop).Parameters.ContainsKey('OperationTimeoutSec'))
    } catch {
        $cimHasTimeout = $false
    }
    # 无 OperationTimeoutSec 时用 Start-Job 包一层，单次开销大，故降低 WMI 次数上限
    $maxWmi = if ($cimHasTimeout) { 40 } else { 8 }

    Write-Host '  enumerating python.exe / node.exe ...' -ForegroundColor DarkGray
    try { [Console]::Out.Flush() } catch {}

    $byId = @{}
    foreach ($pat in @('python*', 'node*')) {
        try {
            foreach ($g in @(Get-Process -Name $pat -ErrorAction SilentlyContinue)) {
                $byId[$g.Id] = $g
            }
        } catch {
            # 无匹配进程时 Get-Process 可能抛错，忽略
        }
    }

    Write-Host ('  found {0} candidate process(es); matching repo...' -f $byId.Count) -ForegroundColor DarkGray
    try { [Console]::Out.Flush() } catch {}

    $pathMatch = [System.Collections.Generic.List[object]]::new()
    $needWmi = [System.Collections.Generic.List[object]]::new()
    foreach ($gp in $byId.Values) {
        $hit = $false
        try {
            $fp = $gp.Path
            if ($fp -and $rootNorm -and ($fp.StartsWith($rootNorm, [System.StringComparison]::OrdinalIgnoreCase))) {
                $hit = $true
            }
        } catch {
            # Path 对部分进程不可读
        }
        if ($hit) { $pathMatch.Add($gp) } else { $needWmi.Add($gp) }
    }

    $killed = 0
    function Stop-OneRepoProc([System.Diagnostics.Process]$gp) {
        try {
            Stop-Process -Id $gp.Id -Force -ErrorAction Stop
            Write-Host ('  killed {0} PID={1}' -f $gp.ProcessName, $gp.Id)
            return 1
        } catch {
            Write-Warn ('  skip PID={0}: {1}' -f $gp.Id, $_.Exception.Message)
            return 0
        }
    }

    foreach ($gp in $pathMatch) {
        if ([datetime]::UtcNow -gt $deadline) {
            Write-Warn 'Stop-Existing: 已超过 25s 预算（路径匹配阶段）。可改用 -SkipKillExisting。'
            break
        }
        $killed += Stop-OneRepoProc $gp
    }

    $wmiUsed = 0
    foreach ($gp in $needWmi) {
        if ([datetime]::UtcNow -gt $deadline) {
            Write-Warn 'Stop-Existing: 已超过 25s 总预算，停止 WMI 回退（避免长时间无响应）。可改用 -SkipKillExisting。'
            break
        }
        if ($wmiUsed -ge $maxWmi) {
            $left = [Math]::Max(0, $needWmi.Count - $maxWmi)
            Write-Warn ('Stop-Existing: WMI 回退已达上限 ({0})，另有约 {1} 个候选未再查询（防卡死）。若端口仍被占，请手动结束进程或改用 -SkipKillExisting。' -f $maxWmi, $left)
            break
        }

        $belongs = $false
        try {
            $wmiUsed++
            $wmiCap = [Math]::Min($needWmi.Count, $maxWmi)
            Write-Host "  process PID=$($gp.Id) ($wmiUsed/$wmiCap) ..." -ForegroundColor DarkGray
            try { [Console]::Out.Flush() } catch {}

            $w = $null
            if ($cimHasTimeout) {
                $flt = 'ProcessId = {0}' -f $gp.Id
                $w = Get-CimInstance -ClassName Win32_Process -Filter $flt -ErrorAction SilentlyContinue -OperationTimeoutSec $cimTimeoutSec
            } else {
                $job = Start-Job -ScriptBlock {
                    param($TargetId)
                    $f = 'ProcessId = {0}' -f $TargetId
                    Get-CimInstance -ClassName Win32_Process -Filter $f -ErrorAction SilentlyContinue
                } -ArgumentList @($gp.Id)
                $done = Wait-Job -Job $job -Timeout ([Math]::Max(3, $cimTimeoutSec + 1))
                if ($done) {
                    $w = Receive-Job -Job $job -ErrorAction SilentlyContinue
                } else {
                    Stop-Job -Job $job -Force -ErrorAction SilentlyContinue
                }
                Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
            }
            if ($w) {
                $cmd = [string]$w.CommandLine
                $exePath = [string]$w.ExecutablePath
                if ($cmd -match $repoPattern -or $exePath -match $repoPattern) { $belongs = $true }
            }
        } catch {
            # 单 PID WMI 失败则跳过该进程
        }

        if (-not $belongs) { continue }
        $killed += Stop-OneRepoProc $gp
    }

    if ($killed -eq 0) {
        Write-Host "  (no matching repo processes)" -ForegroundColor DarkGray
    }
    Start-Sleep -Seconds 1
    Write-Success "Process cleanup done"
}

# --- Backend ----------------------------------------------------------------
function Start-Backend {
    $bindHost = "0.0.0.0:$BackendPort"
    Write-Info ("Starting backend ($bindHost) via $Python ...")

    # Runtime env. DATABASE_URL is only set if not already provided so the
    # caller can override (e.g. point at a staging DB without editing this script).
    if (-not $env:DATABASE_URL -and (Test-Path (Join-Path $BackendDir ".env"))) {
        $envLine = Get-Content -LiteralPath (Join-Path $BackendDir ".env") -ErrorAction SilentlyContinue |
            Where-Object { $_ -match '^\s*DATABASE_URL\s*=' } |
            Select-Object -First 1
        if ($envLine) { $env:DATABASE_URL = ($envLine -replace '^\s*DATABASE_URL\s*=', '').Trim().Trim('"').Trim("'") }
    }
    if (-not $env:VECTOR_DB_URL -and (Test-Path (Join-Path $BackendDir ".env"))) {
        $envLine = Get-Content -LiteralPath (Join-Path $BackendDir ".env") -ErrorAction SilentlyContinue |
            Where-Object { $_ -match '^\s*VECTOR_DB_URL\s*=' } |
            Select-Object -First 1
        if ($envLine) { $env:VECTOR_DB_URL = ($envLine -replace '^\s*VECTOR_DB_URL\s*=', '').Trim().Trim('"').Trim("'") }
    }
    if (-not $env:DATABASE_URL) {
        $pgPort = $null
        foreach ($port in @(5433, 5432)) {
            try {
                $client = New-Object Net.Sockets.TcpClient
                $iar = $client.BeginConnect('127.0.0.1', $port, $null, $null)
                if ($iar.AsyncWaitHandle.WaitOne(800, $false) -and $client.Connected) { $pgPort = $port; break }
            } catch {
            } finally {
                if ($client) { $client.Dispose() }
            }
        }
        if ($pgPort) {
            $env:DATABASE_URL = "postgresql+psycopg://xcagi:xcagi@127.0.0.1:$pgPort/xcagi"
            Write-Info "Auto-detected PostgreSQL on 127.0.0.1:$pgPort"
        } else {
            $dataDir = Join-Path $BackendDir "data"
            if (-not (Test-Path $dataDir)) { New-Item -ItemType Directory -Path $dataDir -Force | Out-Null }
            $sqlitePath = (Join-Path $dataDir "products.db").Replace('\', '/')
            $env:DATABASE_URL = "sqlite:///$sqlitePath"
            Write-Warn "No local PostgreSQL detected on 5433/5432; using SQLite: $env:DATABASE_URL"
        }
    }
    if (-not $env:VECTOR_DB_URL)  { $env:VECTOR_DB_URL = $env:DATABASE_URL }
    # 治根注：FHD 仓库根放在前，XCAGI 入口目录放在后。
    # 历史上反过来（XCAGI 在前）会让 XCAGI/resources/、XCAGI/scripts/ 下的
    # 僵尸副本永远赢 FHD 主版本（namespace package 先到先得），导致
    # /api/system/industries 之类接口拿到 4-14 的旧 industry_config，前端下拉
    # 出现"4 项 YAML 硬编码"幽灵。修过该文件后请保持 RepoRoot 在 BackendDir 之前。
    $env:PYTHONPATH = @($RepoRoot, $BackendDir) -join [System.IO.Path]::PathSeparator
    $env:PYTHONUTF8 = '1'
    $env:XCAGI_DEV_ALLOW_LAN_CORS = '1'
    $env:FHD_BUSINESS_DATA_REQUIRES_EXTENSION_MOD = '1'
    $env:XCAGI_MODS_ROOT = $ModsDir
    $env:LAN_ADMIN_HOST_AUTO_BYPASS = '1'

    if ($NoReload) {
        $env:XCAGI_UVICORN_RELOAD = '0'
    } else {
        $env:XCAGI_UVICORN_RELOAD = '1'
    }
    $env:FASTAPI_HOST = '0.0.0.0'
    $env:FASTAPI_PORT = [string]$BackendPort
    $env:XCAGI_API_PORT = [string]$BackendPort

    $arguments = @(
        (Join-Path $BackendDir "run_fastapi.py")
    )

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName         = $Python
    $psi.Arguments        = ($arguments | ForEach-Object { if ($_ -match '\s') { '"{0}"' -f $_ } else { $_ } }) -join " "
    $psi.WorkingDirectory = $BackendDir
    $psi.UseShellExecute  = $false
    $psi.CreateNoWindow   = $false
    [System.Diagnostics.Process]::Start($psi) | Out-Null

    $ok = $false
    for ($i = 1; $i -le $BackendWaitSec; $i++) {
        Start-Sleep -Seconds 1
        try {
            $r = Invoke-WebRequest -Uri ("http://127.0.0.1:{0}/api/lan/host-info" -f $BackendPort) -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($r.StatusCode -eq 200) { $ok = $true; break }
        } catch {}
        if ($i % 5 -eq 0) { Write-Host (' [{0}s]' -f $i) -NoNewline } else { Write-Host "." -NoNewline }
    }
    Write-Host ""

    if ($ok) {
        Write-Success ('Backend started in ~{0}s' -f $i)
    } else {
        Write-Warn ('Backend still not responding after {0}s; it may still be booting (reload subprocess cold-start).' -f $BackendWaitSec)
        Write-Warn ('Probe URL: http://127.0.0.1:{0}/api/lan/host-info' -f $BackendPort)
    }
}

# --- Frontend ---------------------------------------------------------------
function Start-Frontend {
    if (-not (Test-Path (Join-Path $FrontDir 'package.json'))) {
        Write-Warn "Frontend skipped: $FrontDir\package.json missing"
        return
    }
    Write-Info ("Starting frontend (Vite dev on port {0}) in {1} ..." -f $FrontendPort, $FrontDir)
    try { [Console]::Out.Flush() } catch {}

    $viteEntry = Join-Path $FrontDir "node_modules\vite\bin\vite.js"
    if (-not (Test-Path $viteEntry)) {
        Write-Info '未检测到 node_modules（或缺少 vite）；将弹出 cmd 窗口执行 npm install（最多等待 20 分钟）...'
        try { [Console]::Out.Flush() } catch {}
        $fdQ = '"' + ($FrontDir.Replace('"', '')) + '"'
        # cmd 一行：用拼接避免 PS 5.1 对 '...&&...' / -f 的解析差异
        $installLine = 'cd /d ' + $fdQ + ' && npm install || pause'
        $instProc = Start-Process -FilePath $env:ComSpec -ArgumentList @('/c', $installLine) `
            -WorkingDirectory $FrontDir -WindowStyle Normal -PassThru
        if ($null -ne $instProc) {
            $installWaitMs = 1200000
            if (-not $instProc.WaitForExit($installWaitMs)) {
                try { $instProc.Kill() } catch {}
                Write-Warn ('npm install 超过 {0} 分钟仍未结束，已终止等待。请在 frontend 目录手动 npm install 后重试。' -f [int]($installWaitMs / 60000))
            } elseif ($instProc.ExitCode -ne 0) {
                Write-Warn ('npm install 退出码 {0}；若随后 dev 失败，请在 frontend 目录手动执行 npm install。' -f $instProc.ExitCode)
            }
        }
    }

    # 勿在此调用 Get-LanIP：其内部 Get-NetIPConfiguration 会卡死，表现为一直停在上一行 Write-Info
    $lip = Get-QuickPrivateIPv4ForHmr
    $npmPrefix = ""
    if ($lip -and $lip -ne "127.0.0.1") {
        $npmPrefix = 'set VITE_DEV_HMR_HOST=' + $lip + '&& '
        Write-Info ('VITE_DEV_HMR_HOST={0} (手机/平板 HMR WebSocket 指向本机私网 IP)' -f $lip)
    }
    $npmPrefix += 'set VITE_API_BASE=http://127.0.0.1:' + $BackendPort + '&& '
    Write-Info ('VITE_API_BASE=http://127.0.0.1:{0} (Vite 代理目标)' -f $BackendPort)

    # 必须用 Start-Process 新开控制台：Process.Start(..., UseShellExecute=$false) 的子进程会挂到当前 PowerShell 上，
    # 往往看不到独立 cmd 窗口，npm/vite 日志也「像没启动」。
    $fdQ = '"' + ($FrontDir.Replace('"', '')) + '"'
    $devSep = [string]::new([char[]]@(0x20, 0x26, 0x26, 0x20))  # ' && ' 避免无 BOM 时编码错位导致引号未闭合
    $devLine = 'cd /d ' + $fdQ + $devSep + $npmPrefix + 'npm run dev -- --host 0.0.0.0 --port ' + $FrontendPort
    Start-Process -FilePath $env:ComSpec -ArgumentList @('/k', $devLine) -WorkingDirectory $FrontDir -WindowStyle Normal
    Write-Info '已单独弹出 cmd 窗口跑 Vite（标题为命令提示符）；npm/vite 日志在该窗口，可最小化但不要关。'

    $ok = $false
    for ($i = 1; $i -le $FrontendWaitSec; $i++) {
        Start-Sleep -Seconds 1
        try {
            $r = Invoke-WebRequest -Uri ("http://127.0.0.1:{0}" -f $FrontendPort) -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
            if ($r.StatusCode -eq 200) { $ok = $true; break }
        } catch {}
        if ($i % 5 -eq 0) { Write-Host (' [{0}s]' -f $i) -NoNewline } else { Write-Host "." -NoNewline }
    }
    Write-Host ""

    if ($ok) {
        Write-Success ('Frontend started in ~{0}s' -f $i)
    } else {
        Write-Warn ('Frontend still not responding after {0}s. Vite cold start (after vite cache wipe) can take up to 60s.' -f $FrontendWaitSec)
        Write-Warn '请看已弹出的 cmd 窗口里的 npm/vite 报错；或传 -FrontendWaitSec 90 再试。'
    }
}

# --- Info banner ------------------------------------------------------------
function Show-Info {
    $rows = @(Get-LanIpv4Rows -NetAddressOnly)
    $lanIp = if ($rows.Count -ge 1) { [string]$rows[0].IP } else { "127.0.0.1" }
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "    XCAGI v7.0 Server Running!"          -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Repo Root  : $RepoRoot" -ForegroundColor DarkGray
    Write-Host "  Python     : $Python"   -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  LAN 前端 (手机请用与电脑同一网段的地址) :" -ForegroundColor Cyan
    if ($rows.Count -eq 0) {
        Write-Host "     (未检测到私网 IPv4，请检查 WiFi/网线是否已连接)" -ForegroundColor Yellow
    } else {
        foreach ($r in $rows) {
            $tag = if ($r.IP -eq $lanIp) { "  ← 默认优先" } else { "" }
            Write-Host ('     http://{0}:{1}   [{2}]{3}' -f $r.IP, $FrontendPort, $r.InterfaceAlias, $tag) -ForegroundColor Cyan
        }
        if ($rows.Count -gt 1) {
            Write-Host ""
            Write-Host "  若手机打不开第一行，多半是连到了另一块网卡；请依次试上面其它 IP。" -ForegroundColor DarkGray
        }
    }
    Write-Host ""
    # 双引号内勿写 ::1（PS 5.1 会把 :: 当类型/作用域解析，导致整文件级联语法错）
    Write-Host '  本机浏览器 (建议用 IPv4，避免 localhost 解析到 ::1 时连不上):' -ForegroundColor Cyan
    Write-Host ('     http://127.0.0.1:{0}' -f $FrontendPort)
    Write-Host ""
    Write-Host "  API 后端 :" -ForegroundColor Cyan
    if ($rows.Count -ge 1) {
        foreach ($r in $rows) {
            Write-Host ('     http://{0}:{1}   [{2}]' -f $r.IP, $BackendPort, $r.InterfaceAlias) -ForegroundColor Cyan
        }
        Write-Host ('     http://{0}:{1}/docs' -f $lanIp, $BackendPort) -ForegroundColor Cyan
    } else {
        Write-Host ('     http://{0}:{1}' -f $lanIp, $BackendPort)
        Write-Host ('     http://{0}:{1}/docs' -f $lanIp, $BackendPort)
    }
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green

    if ($lanIp -eq "127.0.0.1") {
        Write-Warn "未解析到可用的局域网 IPv4；请连接 WiFi/以太网后重启本脚本。"
    }

    Write-Host ""
    Write-Host '  端口自检 (本机探测，手机仍进不来多半是防火墙或路由器 AP 隔离):' -ForegroundColor DarkGray
    foreach ($r in $rows) {
        $ip = [string]$r.IP
        if (-not $ip -or $ip -eq "127.0.0.1") { continue }
        try {
            $t1 = Test-NetConnection -ComputerName $ip -Port $FrontendPort -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
            $t0 = Test-NetConnection -ComputerName $ip -Port $BackendPort -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
            $s1 = if ($t1.TcpTestSucceeded) { "OK" } else { "FAIL" }
            $s0 = if ($t0.TcpTestSucceeded) { "OK" } else { "FAIL" }
            Write-Host ('     {0}  TCP {1}={2}  TCP {3}={4}' -f $ip, $FrontendPort, $s1, $BackendPort, $s0) -ForegroundColor DarkGray
        } catch {
            Write-Host ('     {0}  (自检跳过)' -f $ip) -ForegroundColor DarkGray
        }
    }
}

# --- Main -------------------------------------------------------------------
if ($StopOnly) {
    Stop-Existing
    Write-Success "StopOnly requested; not starting anything."
    exit 0
}

Clear-Host
Write-Host ""
Write-Host '              XCAGI  v7.0' -ForegroundColor Green
Write-Host ""
# ASCII：stock figlet 默认字体「XCAGI」（无旧版右侧 -6.0 尾巴）
Write-Host ' __  ______    _    ____ ___ ' -ForegroundColor Cyan
Write-Host ' \ \/ / ___|  / \  / ___|_ _|' -ForegroundColor Cyan
Write-Host '  \  / |     / _ \| |  _ | | ' -ForegroundColor Cyan
Write-Host '  /  \ |___ / ___ \ |_| || | ' -ForegroundColor Cyan
Write-Host ' /_/\_\____/_/   \_\____|___|' -ForegroundColor Cyan
Write-Host ""
Write-Host '            -----  v7.0  -----' -ForegroundColor Yellow
Write-Host ('       LAN Dev Launcher · FastAPI :{0} + Vite :{1}' -f $BackendPort, $FrontendPort) -ForegroundColor DarkGray
Write-Host ""

Stop-Existing

# --- Firewall rules (only when running as admin) ---------------------------
if ($ConfigureFirewall) {
    if (-not $IsAdmin) {
        Write-Warn "-ConfigureFirewall requires Administrator; firewall rules skipped. Run start-lan.bat /Firewall and accept UAC, then try again."
    } else {
        Write-Info ("Adding inbound firewall rules (TCP {0}/{1}) because -ConfigureFirewall / start-lan.bat /Firewall was used." -f $BackendPort, $FrontendPort)
        Ensure-FirewallRule -Name ("XCAGI Backend ({0})" -f $BackendPort)  -Port $BackendPort
        Ensure-FirewallRule -Name ("XCAGI Frontend ({0})" -f $FrontendPort) -Port $FrontendPort
    }
}

Write-Host ('  Launch: Backend={0}  Frontend(Vite)={1}' -f (-not $NoBackend), (-not $NoFrontend)) -ForegroundColor DarkGray
if (-not $NoBackend)  { Start-Backend }
if (-not $NoFrontend) { Start-Frontend }

Show-Info

Write-Info ""
Write-Info "Press Ctrl+C to stop, or close this window..."
Write-Info "Server is running..."
Write-Host ""

# Keep running
while ($true) {
    Start-Sleep -Seconds 5
}
